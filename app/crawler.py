from playwright.async_api import async_playwright
from typing import List, Dict, Any
from .models import UIElement, AuthConfig, ScanStrategy
import logging
import json
import asyncio
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebsiteCrawler:
    def __init__(self):
        self.playwright = None
        self.browser = None
        
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _apply_auth(self, page, auth: AuthConfig):
        if not auth:
            return
            
        if auth.type == "basic" and auth.username and auth.password:
            await page.set_http_credentials({"username": auth.username, "password": auth.password})
        elif auth.type == "session" and auth.token:
            if auth.token_type == "cookie":
                await page.context.add_cookies([{
                    "name": "session",
                    "value": auth.token,
                    "url": page.url
                }])
            elif auth.token_type == "bearer":
                await page.set_extra_http_headers({
                    "Authorization": f"Bearer {auth.token}"
                })

    async def _wait_for_dynamic_content(self, page):
        """Enhanced waiting strategy for dynamic content to load completely"""
        try:
            # 1. Wait for network activity to cease - more robust than fixed timeout
            logger.info("Waiting for network activity to cease...")
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            # 2. Wait for common navigation elements to be present (helps with SPAs)
            common_nav_selectors = ['nav', 'header', '[role="navigation"]', '.navbar', '.navigation']
            for selector in common_nav_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    logger.info(f"Found navigation element: {selector}")
                    break
                except:
                    continue
            
            # 3. Scroll to trigger lazy-loaded content, then wait again
            logger.info("Scrolling to trigger lazy-loaded content...")
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)  # Brief wait for scroll-triggered content
            
            # 4. Scroll back to top for consistent starting position
            await page.evaluate('window.scrollTo(0, 0)')
            await page.wait_for_timeout(1000)
            
            # 5. Final networkidle wait to catch any scroll-triggered requests
            await page.wait_for_load_state('networkidle', timeout=10000)
            logger.info("Dynamic content loading completed")
            
        except Exception as e:
            logger.warning(f"Dynamic content waiting completed with some timeouts: {e}")

    async def _extract_structured_content(self, page) -> Dict[str, Any]:
        """Extract structured content (buttons, links, etc.) for better LLM input"""
        try:
            logger.info("Extracting structured content for LLM...")
            
            # Extract visible interactive elements with their semantic information
            structured_content = await page.evaluate("""() => {
                const elements = [];
                
                // Get all visible buttons
                const buttons = Array.from(document.querySelectorAll('button:not([style*="display: none"]):not([style*="visibility: hidden"])'));
                buttons.forEach(btn => {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        const text = btn.textContent?.trim() || '';
                        const ariaLabel = btn.getAttribute('aria-label') || '';
                        const title = btn.getAttribute('title') || '';
                        if (text || ariaLabel || title) {
                            elements.push({
                                type: 'button',
                                text: text,
                                aria_label: ariaLabel,
                                title: title,
                                id: btn.id || '',
                                classes: btn.className || '',
                                name: btn.name || ''
                            });
                        }
                    }
                });
                
                // Get all visible links
                const links = Array.from(document.querySelectorAll('a:not([style*="display: none"]):not([style*="visibility: hidden"])'));
                links.forEach(link => {
                    const rect = link.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        const text = link.textContent?.trim() || '';
                        const ariaLabel = link.getAttribute('aria-label') || '';
                        const href = link.getAttribute('href') || '';
                        const title = link.getAttribute('title') || '';
                        if ((text || ariaLabel || title) && href && !href.startsWith('javascript:') && href !== '#') {
                            elements.push({
                                type: 'link',
                                text: text,
                                href: href,
                                aria_label: ariaLabel,
                                title: title,
                                id: link.id || '',
                                classes: link.className || ''
                            });
                        }
                    }
                });
                
                // Get all visible input fields
                const inputs = Array.from(document.querySelectorAll('input:not([style*="display: none"]):not([style*="visibility: hidden"]), textarea:not([style*="display: none"]):not([style*="visibility: hidden"]), select:not([style*="display: none"]):not([style*="visibility: hidden"])'));
                inputs.forEach(input => {
                    const rect = input.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        const placeholder = input.getAttribute('placeholder') || '';
                        const ariaLabel = input.getAttribute('aria-label') || '';
                        const label = input.labels?.[0]?.textContent?.trim() || '';
                        const name = input.getAttribute('name') || '';
                        const type = input.getAttribute('type') || input.tagName.toLowerCase();
                        
                        elements.push({
                            type: 'input',
                            input_type: type,
                            placeholder: placeholder,
                            aria_label: ariaLabel,
                            label: label,
                            name: name,
                            id: input.id || '',
                            classes: input.className || ''
                        });
                    }
                });
                
                // Get navigation-specific elements
                const navElements = Array.from(document.querySelectorAll('nav *, [role="navigation"] *, .navbar *, .navigation *, header *'));
                const navItems = [];
                navElements.forEach(el => {
                    if ((el.tagName === 'A' || el.tagName === 'BUTTON') && el.textContent?.trim()) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            navItems.push({
                                type: 'navigation_item',
                                text: el.textContent.trim(),
                                tag: el.tagName.toLowerCase(),
                                href: el.getAttribute('href') || '',
                                classes: el.className || ''
                            });
                        }
                    }
                });
                
                return {
                    interactive_elements: elements,
                    navigation_elements: navItems,
                    total_elements: elements.length + navItems.length
                };
            }""")
            
            logger.info(f"Extracted {structured_content['total_elements']} structured elements")
            return structured_content
            
        except Exception as e:
            logger.error(f"Error extracting structured content: {e}")
            return {"interactive_elements": [], "navigation_elements": [], "total_elements": 0}

    async def _extract_html_snapshot(self, page) -> str:
        """Extract complete HTML snapshot after dynamic content has loaded"""
        try:
            logger.info("Extracting complete HTML snapshot...")
            html_content = await page.content()
            logger.info(f"Extracted HTML content ({len(html_content)} characters)")
            return html_content
        except Exception as e:
            logger.error(f"Error extracting HTML snapshot: {e}")
            return ""

    async def _extract_element_info(self, element) -> Dict[str, Any]:
        try:
            box = await element.bounding_box()
            position = {
                "x": box["x"],
                "y": box["y"],
                "width": box["width"],
                "height": box["height"]
            } if box else None
        except:
            position = None

        return {
            "element_type": await element.evaluate("el => el.tagName.toLowerCase()"),
            "selector": await self._generate_selector(element),
            "attributes": await element.evaluate("""el => {
                const attrs = {};
                for (const attr of el.attributes) {
                    attrs[attr.name] = attr.value;
                }
                return attrs;
            }"""),
            "visible_text": await element.evaluate("el => el.textContent?.trim()"),
            "position": position
        }

    async def _generate_selector(self, element) -> str:
        # Try to find a unique identifier
        if await element.get_attribute("id"):
            return f"#{await element.get_attribute('id')}"
        
        # Try to use data-testid if available
        if await element.get_attribute("data-testid"):
            return f"[data-testid='{await element.get_attribute('data-testid')}']"
        
        # Try to use name attribute
        if await element.get_attribute("name"):
            return f"[name='{await element.get_attribute('name')}']"
        
        # Fallback to a more complex selector
        return await element.evaluate("""el => {
            if (el.id) return '#' + el.id;
            if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
            if (el.getAttribute('name')) return `[name="${el.getAttribute('name')}"]`;
            
            let path = [];
            while (el && el.nodeType === Node.ELEMENT_NODE) {
                let selector = el.nodeName.toLowerCase();
                if (el.id) {
                    selector += '#' + el.id;
                    path.unshift(selector);
                    break;
                } else {
                    let sibling = el;
                    let nth = 1;
                    while (sibling = sibling.previousElementSibling) {
                        if (sibling.nodeName.toLowerCase() === selector) nth++;
                    }
                    if (nth !== 1) selector += ":nth-of-type("+nth+")";
                }
                path.unshift(selector);
                el = el.parentNode;
            }
            return path.join(' > ');
        }""")

    async def _get_element_location_context(self, element) -> str:
        """Determine where the element is located on the page (nav, footer, main, etc.)"""
        try:
            location = await element.evaluate("""element => {
                // Check if element is in navigation
                const nav = element.closest('nav, header, [role="navigation"], .navigation, .nav, .navbar, .header');
                if (nav) {
                    // Check if it's specifically a mobile nav
                    if (nav.matches('.mobile-nav, .mobile-menu, [class*="mobile"], [id*="mobile"]')) {
                        return 'mobile_navigation';
                    }
                    return 'main_navigation';
                }
                
                // Check if element is in footer
                const footer = element.closest('footer, [role="contentinfo"], .footer');
                if (footer) return 'footer';
                
                // Check if element is in main content
                const main = element.closest('main, [role="main"], article, .main-content, .content');
                if (main) return 'main_content';
                
                // Check if element is in sidebar
                const sidebar = element.closest('aside, [role="complementary"], .sidebar');
                if (sidebar) return 'sidebar';
                
                // Check if element is in breadcrumbs
                const breadcrumbs = element.closest('nav[aria-label*="breadcrumb"], .breadcrumb, .breadcrumbs');
                if (breadcrumbs) return 'breadcrumbs';
                
                return 'other';
            }""")
            return location
        except Exception as e:
            logger.warning(f"Failed to determine element location context: {e}")
            return 'unknown'

    async def _score_element_relevance(self, element, search_keywords: List[str], search_patterns: List[str]) -> float:
        """
        Score how relevant an element is for the search criteria.
        Higher scores = more relevant = should be prioritized.
        """
        score = 0.0
        
        try:
            # Get element properties
            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
            element_text = await element.evaluate('el => el.textContent?.trim()') or ''
            href = await element.evaluate('el => el.getAttribute("href")') or ''
            aria_label = await element.evaluate('el => el.getAttribute("aria-label")') or ''
            element_type = await element.evaluate('el => el.getAttribute("type")') or ''
            classes = await element.evaluate('el => el.className') or ''
            
            # Base score by element type (prioritize actionable elements)
            actionable_elements = {
                'a': 10.0,      # Links are highly actionable
                'button': 10.0,  # Buttons are highly actionable
                'input': 8.0,    # Inputs are actionable
                'select': 7.0,   # Selects are actionable
                'textarea': 6.0  # Textareas are actionable
            }
            
            container_elements = {
                'div': 2.0,      # Divs are usually containers
                'span': 2.0,     # Spans are usually text
                'p': 1.0,        # Paragraphs are usually text
                'article': 1.0,  # Articles are content
                'section': 1.0,  # Sections are content
                'li': 3.0        # List items might contain links
            }
            
            score += actionable_elements.get(tag_name, container_elements.get(tag_name, 0.5))
            
            # Bonus for exact keyword matches in text
            element_text_lower = element_text.lower()
            for keyword in search_keywords:
                if keyword.lower() in element_text_lower:
                    # Exact word match gets higher score than partial match
                    if f' {keyword.lower()} ' in f' {element_text_lower} ':
                        score += 5.0
                    else:
                        score += 2.0
            
            # Bonus for pattern matches in href (for links)
            if href:
                for pattern in search_patterns:
                    if pattern.lower() in href.lower():
                        score += 8.0  # URLs are very specific
            
            # Bonus for pattern matches in aria-label
            if aria_label:
                for keyword in search_keywords:
                    if keyword.lower() in aria_label.lower():
                        score += 4.0
            
            # Penalty for elements that are likely noise
            noise_indicators = ['cookie', 'consent', 'banner', 'modal', 'popup', 'advertisement', 'ad-']
            for noise in noise_indicators:
                if (noise in element_text_lower or 
                    noise in classes.lower() or 
                    noise in aria_label.lower()):
                    score -= 5.0
            
            # Penalty for very long text (likely content blocks, not actionable elements)
            if len(element_text) > 100:
                score -= 3.0
                
            # Penalty for elements with no visible text (unless they're inputs)
            if not element_text.strip() and tag_name not in ['input', 'textarea', 'select']:
                score -= 2.0
                
            return max(0.0, score)  # Don't return negative scores
            
        except Exception as e:
            logger.warning(f"Error scoring element relevance: {e}")
            return 0.0

    async def _filter_and_prioritize_elements(self, elements: List, search_keywords: List[str], search_patterns: List[str], max_elements: int = 5) -> List:
        """
        Filter and prioritize elements based on relevance scores.
        Returns the top N most relevant elements.
        """
        if not elements:
            return []
            
        # Score all elements
        scored_elements = []
        for element in elements:
            try:
                score = await self._score_element_relevance(element, search_keywords, search_patterns)
                if score > 0:  # Only include elements with positive scores
                    scored_elements.append((element, score))
            except Exception as e:
                logger.warning(f"Error scoring element: {e}")
                continue
        
        # Sort by score (highest first) and take top N
        scored_elements.sort(key=lambda x: x[1], reverse=True)
        top_elements = [elem for elem, score in scored_elements[:max_elements]]
        
        logger.info(f"Filtered {len(elements)} elements down to {len(top_elements)} high-quality elements")
        if scored_elements:
            logger.info(f"Top element score: {scored_elements[0][1]:.1f}, Lowest included score: {scored_elements[min(len(scored_elements)-1, max_elements-1)][1]:.1f}")
        
        return top_elements

    async def _find_elements_semantically(self, page, element_desc: Dict[str, Any]) -> List:
        """
        Generic semantic element finder that works with any AI-generated search criteria.
        No hardcoded patterns - relies entirely on the strategist's semantic analysis.
        """
        found_elements = []
        
        # Extract search criteria from AI strategist
        semantic_keywords = element_desc.get('semantic_keywords', [])
        content_patterns = element_desc.get('content_patterns', [])
        element_types = element_desc.get('element_types', ['*'])
        attributes = element_desc.get('attributes', {})
        purpose = element_desc.get('purpose', '')
        
        logger.info(f"Generic semantic search for: {purpose}")
        logger.info(f"Keywords: {semantic_keywords}")
        logger.info(f"Content patterns: {content_patterns}")
        
        # Strategy 1: Content pattern matching (URLs, text, etc.)
        for pattern in content_patterns:
            try:
                # Search for any links containing the pattern
                if pattern:
                    # Case-insensitive href search
                    elements = await page.query_selector_all(f'a[href*="{pattern}" i]')
                    found_elements.extend(elements)
                    
                    # Search for text content containing the pattern - FIXED API
                    for element_type in element_types:
                        # Use compiled regex with re.IGNORECASE flag
                        regex_pattern = re.compile(f'.*{re.escape(pattern)}.*', re.IGNORECASE)
                        locator = page.locator(element_type).filter(has_text=regex_pattern)
                        elements = await locator.all()
                        found_elements.extend(elements)
                        
            except Exception as e:
                logger.warning(f"Error searching for content pattern '{pattern}': {e}")
        
        # Strategy 2: Semantic keyword matching across all text content
        for keyword in semantic_keywords:
            try:
                # Search across all element types for keyword in text - FIXED API
                for element_type in element_types + ['a', 'button', 'div', 'span', 'p', 'h1', 'h2', 'h3', 'li', 'section', 'article']:
                    # Use compiled regex with re.IGNORECASE flag
                    regex_pattern = re.compile(f'.*{re.escape(keyword)}.*', re.IGNORECASE)
                    locator = page.locator(element_type).filter(has_text=regex_pattern)
                    elements = await locator.all()
                    found_elements.extend(elements)
                    
                # Search in common attributes that might contain descriptive text
                attribute_selectors = [
                    f'[aria-label*="{keyword}" i]',
                    f'[alt*="{keyword}" i]', 
                    f'[title*="{keyword}" i]',
                    f'[placeholder*="{keyword}" i]',
                    f'[data-*="{keyword}" i]'
                ]
                
                for selector in attribute_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        found_elements.extend(elements)
                    except:
                        continue  # Some selectors might not be valid, skip them
                        
            except Exception as e:
                logger.warning(f"Error searching for semantic keyword '{keyword}': {e}")
        
        # Strategy 3: Class and ID pattern matching using keywords
        for keyword in semantic_keywords:
            try:
                # Search for elements with classes/IDs containing the keyword
                class_id_selectors = [
                    f'[class*="{keyword}" i]',
                    f'[id*="{keyword}" i]'
                ]
                
                for selector in class_id_selectors:
                    elements = await page.query_selector_all(selector)
                    found_elements.extend(elements)
                    
            except Exception as e:
                logger.warning(f"Error searching for class/id pattern '{keyword}': {e}")
        
        # Strategy 4: Attribute-based search (fallback for specific requirements)
        if attributes:
            try:
                for element_type in element_types:
                    attr_conditions = []
                    for attr_name, attr_value in attributes.items():
                        if attr_value == '*':
                            attr_conditions.append(f'[{attr_name}]')
                        elif attr_value == 'contains':
                            # Use keywords to search within attributes
                            for keyword in semantic_keywords:
                                attr_conditions.append(f'[{attr_name}*="{keyword}" i]')
                        else:
                            escaped_value = str(attr_value).replace('"', '\\"')
                            attr_conditions.append(f'[{attr_name}="{escaped_value}"]')
                    
                    for condition in attr_conditions:
                        selector = f"{element_type}{condition}"
                        elements = await page.query_selector_all(selector)
                        found_elements.extend(elements)
                        
            except Exception as e:
                logger.warning(f"Error with attribute-based search: {e}")
        
        # Remove duplicates while preserving order
        unique_elements = []
        seen_elements = set()
        
        for element in found_elements:
            try:
                # Create a unique identifier using element position and tag
                bounds = await element.bounding_box()
                tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
                element_key = f"{tag_name}_{bounds['x']}_{bounds['y']}" if bounds else f"{tag_name}_{hash(str(element))}"
                
                if element_key not in seen_elements:
                    seen_elements.add(element_key)
                    unique_elements.append(element)
            except:
                # Fallback: just add the element if we can't get its position
                unique_elements.append(element)
        
        logger.info(f"Found {len(unique_elements)} unique elements for purpose: {purpose}")
        return unique_elements

    async def _find_elements_with_structured_hints(self, page, element_desc: Dict[str, Any], structured_content: Dict[str, Any]) -> List:
        """
        Enhanced semantic element finder that uses structured content as hints to guide the search.
        This combines the power of pre-extracted content with flexible semantic matching.
        """
        found_elements = []
        
        # Extract search criteria from AI strategist
        semantic_keywords = element_desc.get('semantic_keywords', [])
        content_patterns = element_desc.get('content_patterns', [])
        element_types = element_desc.get('element_types', ['*'])
        attributes = element_desc.get('attributes', {})
        purpose = element_desc.get('purpose', '')
        
        logger.info(f"Structured-hint search for: {purpose}")
        logger.info(f"Using {len(structured_content.get('interactive_elements', []))} interactive elements and {len(structured_content.get('navigation_elements', []))} navigation elements as hints")
        
        # Strategy 1: Use structured content as primary hints
        interactive_elements = structured_content.get('interactive_elements', [])
        navigation_elements = structured_content.get('navigation_elements', [])
        
        # Check structured content for direct matches first
        for element_info in interactive_elements + navigation_elements:
            element_text = element_info.get('text', '').lower()
            element_href = element_info.get('href', '').lower()
            element_aria_label = element_info.get('aria_label', '').lower()
            element_placeholder = element_info.get('placeholder', '').lower()
            element_classes = element_info.get('classes', '').lower()
            
            # Check if any keyword matches this element's content
            keyword_match = any(keyword.lower() in element_text or 
                              keyword.lower() in element_href or 
                              keyword.lower() in element_aria_label or 
                              keyword.lower() in element_placeholder or
                              keyword.lower() in element_classes
                              for keyword in semantic_keywords)
            
            # Check if any content pattern matches
            pattern_match = any(pattern.lower() in element_text or 
                              pattern.lower() in element_href or 
                              pattern.lower() in element_aria_label or
                              pattern.lower() in element_placeholder
                              for pattern in content_patterns)
            
            if keyword_match or pattern_match:
                try:
                    # Try to find this element on the page using its unique characteristics
                    selectors_to_try = []
                    
                    # Build potential selectors based on the structured content
                    if element_info.get('id'):
                        selectors_to_try.append(f"#{element_info['id']}")
                    if element_info.get('name'):
                        selectors_to_try.append(f"[name='{element_info['name']}']")
                    if element_text:
                        selectors_to_try.append(f"{element_info.get('type', 'a')}:has-text('{element_text}')")
                    if element_href and element_info.get('type') == 'link':
                        selectors_to_try.append(f"a[href*='{element_href}']")
                    
                    # Try each selector
                    for selector in selectors_to_try:
                        try:
                            elements = await page.query_selector_all(selector)
                            found_elements.extend(elements)
                            if elements:
                                logger.info(f"Found {len(elements)} elements using structured hint: {selector}")
                                break
                        except:
                            continue
                            
                except Exception as e:
                    logger.warning(f"Error using structured hint: {e}")
        
        # Strategy 2: Fall back to generic semantic search for broader coverage
        semantic_elements = await self._find_elements_semantically(page, element_desc)
        found_elements.extend(semantic_elements)
        
        # Filter and prioritize elements by relevance
        filtered_elements = await self._filter_and_prioritize_elements(
            found_elements, 
            semantic_keywords, 
            content_patterns, 
            max_elements=3  # Limit to top 3 most relevant elements
        )
        
        logger.info(f"Found {len(filtered_elements)} high-quality elements (after filtering) for: {purpose}")
        return filtered_elements

    async def crawl(self, url: str, strategy: ScanStrategy, auth: dict = None) -> Dict[str, Any]:
        if not strategy:
            logger.warning("No strategy provided. Cannot scan")
        logger.info(f"Starting crawl of {url}")
        page = await self.browser.new_page()
        
        try:
            # Apply authentication if provided
            if auth:
                auth_config = AuthConfig(**auth) if isinstance(auth, dict) else auth
                await self._apply_auth(page, auth_config)
            
            # Navigate to the page
            await page.goto(url, wait_until="networkidle")
            
            # Enhanced waiting for dynamic content to fully load
            await self._wait_for_dynamic_content(page)
            
            # Extract complete HTML snapshot for potential LLM use
            html_snapshot = await self._extract_html_snapshot(page)
            
            # Extract structured content for better LLM analysis
            structured_content = await self._extract_structured_content(page)
            
            # Get page title
            page_title = await page.title()
            logger.info(f"Page title: {page_title}")
            
            # Track elements by their unique selector to avoid duplicates
            elements_by_selector = {}
            
            for desc in strategy.target_elements_description:
                try:
                    purpose = desc.get('purpose', '')
                    logger.info(f"Processing element description: {purpose}")
                    
                    # Use new semantic matching approach
                    found_elements = await self._find_elements_with_structured_hints(page, desc, structured_content)
                    
                    # Process found elements
                    for i, element in enumerate(found_elements):
                        try:
                            element_info = await self._extract_element_info(element)
                            actual_selector = element_info['selector']
                            
                            # Get location context
                            location_context = await self._get_element_location_context(element)
                            element_info['attributes']['location_context'] = location_context
                            
                            # Create a unique key that includes both selector and location
                            unique_key = f"{actual_selector}::{location_context}"
                            
                            if unique_key in elements_by_selector:
                                # Add this purpose to the existing element
                                existing_element = elements_by_selector[unique_key]
                                existing_purposes = existing_element.attributes.get('purposes', '')
                                if existing_purposes:
                                    existing_purposes = f"{existing_purposes}, {purpose}"
                                else:
                                    existing_purposes = purpose
                                existing_element.attributes['purposes'] = existing_purposes
                                logger.info(f"Added purpose '{purpose}' to existing element at {location_context}")
                                continue
                            
                            # Create new element with location-aware ID
                            purpose_slug = purpose.lower().replace(' ', '_')[:30]
                            location_slug = location_context.lower().replace(' ', '_')
                            element_id = f"{element_info['element_type']}_{location_slug}_{purpose_slug}_{i}"
                            
                            ui_element = UIElement(
                                element_id=element_id,
                                **element_info
                            )
                            ui_element.attributes['purposes'] = purpose  # Store single purpose as string
                            
                            elements_by_selector[unique_key] = ui_element
                            logger.info(f"Found new element for purpose '{purpose}' at {location_context}")
                            
                        except Exception as extract_err:
                            logger.warning(f"Failed to extract element info: {extract_err}")
                            continue
                    
                except Exception as e:
                    logger.error(f"Error processing element description: {e}")
                    continue
            
            # Convert back to list
            elements = list(elements_by_selector.values())
            logger.info(f"Found {len(elements)} unique elements on {url}")
            
            # Return enhanced data including HTML snapshot and structured content
            return {
                "elements": elements,
                "page_title": page_title,
                "html_snapshot": html_snapshot,
                "structured_content": structured_content
            }
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
            raise
        finally:
            await page.close() 