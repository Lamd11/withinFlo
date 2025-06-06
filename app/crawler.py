from playwright.async_api import async_playwright
from typing import List, Dict, Any
from .models import UIElement, AuthConfig, ScanStrategy
import logging
import json

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
            
            # Find all interactive elements using existing strategy-based approach
            elements = []
            
            for desc in strategy.target_elements_description:
                try:
                    # Building selector based on the element's description
                    tag_type = desc.get('type', '*')
                    attributes = desc.get('attributes', {})
                    text_contains = desc.get('text_contains', '')
                    purpose = desc.get('purpose', '')

                    # Build Attribute selector strings
                    attr_selector = []
                    for attr_name, attr_value in attributes.items():
                        if attr_value == '*': # Handles wild card values
                            attr_selector.append(f'[{attr_name}]')
                        else: # Handles specific attribute values and can escape double quotes
                            escaped_value = str(attr_value).replace('"', '\\"')
                            attr_selector.append(f'[{attr_name}="{escaped_value}"]')
                    attr_selector_string = ''.join(attr_selector)
                    base_css_selector = f"{tag_type}{''.join(attr_selector)}"

                    logger.info(f"Searching for elements with selector: {base_css_selector}")
                    
                    locator = page.locator(base_css_selector)
                    # Filtering if specified
                    if text_contains:
                        locator = locator.filter(has_text=text_contains)
                    
                    found_elements = await locator.all()

                    # Processing elements
                    for i, element in enumerate(found_elements):
                        try:
                            element_info = await self._extract_element_info(element)
                            purpose_slug = purpose.lower().replace(' ', '_')[:30]

                            elements.append(UIElement(
                                element_id=f"{element_info['element_type']}_{purpose_slug}_{i}",
                                **element_info
                            ))
                            logger.info(f"Found matching element for purpose: {purpose}")
                        except Exception as extract_err:
                            logger.warning(f"Failed to extract element info: {extract_err}")
                            continue
                    
                except Exception as e:
                    logger.error(f"Error processing element description {e}")
                    continue
            
            logger.info(f"Found {len(elements)} elements on {url}")
            
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