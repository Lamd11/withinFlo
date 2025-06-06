from playwright.async_api import async_playwright
from typing import List, Dict, Any, Set, Tuple
from .models import UIElement, AuthConfig, ScanStrategy
from .page_mapper import PageMapper
import logging
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebsiteCrawler:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.scanned_urls = set()  # Track scanned URLs to prevent loops
        
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
    
    async def get_initial_content(self, url: str, auth: dict = None) -> Dict[str, Any]:
        """
        Enhanced version that uses PageMapper to get comprehensive page information
        """
        logger.info(f"Getting comprehensive initial content from {url}")
        page = await self.browser.new_page()
        
        try:
            # Apply authentication if provided
            if auth:
                auth_config = AuthConfig(**auth) if isinstance(auth, dict) else auth
                await self._apply_auth(page, auth_config)
            
            # Navigate to the page
            await page.goto(url, wait_until="networkidle")
            
            # Wait for dynamic content
            await page.wait_for_timeout(5000)  # 5 seconds wait for dynamic content
            
            # Use PageMapper to get comprehensive page information
            page_map = await PageMapper.map_page(page)
            
            return page_map
            
        except Exception as e:
            logger.error(f"Error getting initial content from {url}: {str(e)}")
            raise
        finally:
            await page.close()

    async def _find_navigation_elements(self, page, navigation_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find elements that can be used for navigation to other pages."""
        navigation_elements = []
        
        for rule in navigation_rules:
            try:
                nav_element = rule.get('navigation_element', {})
                selectors = []
                
                # Build selectors similar to the main crawl method
                tag_type = nav_element.get('type', '*')
                attributes = nav_element.get('attributes', {})
                text_contains = nav_element.get('text_contains', '')
                
                # Add different selector strategies
                attr_selector = []
                for attr_name, attr_value in attributes.items():
                    if attr_value == '*':
                        attr_selector.append(f'[{attr_name}]')
                    else:
                        escaped_value = str(attr_value).replace('"', '\\"')
                        attr_selector.append(f'[{attr_name}="{escaped_value}"]')
                selectors.append(f"{tag_type}{''.join(attr_selector)}")
                
                if text_contains:
                    selectors.append(f"{tag_type}:has-text('{text_contains}')")
                    selectors.append(f"{tag_type} >> text={text_contains}")
                    selectors.append(f"//*[contains(text(), '{text_contains}')]")
                
                # Try each selector
                for selector in selectors:
                    try:
                        elements = await page.locator(selector).all()
                        if elements:
                            for element in elements:
                                # Get href or other navigation attributes
                                href = await element.get_attribute('href')
                                onclick = await element.get_attribute('onclick')
                                
                                navigation_elements.append({
                                    'element': element,
                                    'rule': rule,
                                    'href': href,
                                    'onclick': onclick,
                                    'selector': selector
                                })
                            break  # Found elements with this selector, move to next rule
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {str(e)}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error processing navigation rule: {str(e)}")
                continue
                
        return navigation_elements

    async def _navigate_to_page(self, page, nav_element: Dict[str, Any]) -> bool:
        """Navigate to a new page using the found navigation element."""
        try:
            element = nav_element['element']
            rule = nav_element['rule']
            
            # If there's a specific wait_for_element defined, set up the wait
            wait_for_promise = None
            if rule.get('wait_for_element'):
                wait_for_promise = page.wait_for_selector(rule['wait_for_element'], timeout=5000)
            
            # Click the element
            await element.click()
            
            # Wait for navigation and any specified element
            await page.wait_for_load_state('networkidle')
            if wait_for_promise:
                try:
                    await wait_for_promise
                except Exception as e:
                    logger.warning(f"Wait for element after navigation failed: {str(e)}")
            
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {str(e)}")
            return False

    async def crawl(self, url: str, strategy: ScanStrategy, auth: dict = None) -> Dict[str, Any]:
        """
        Enhanced crawl method that uses the strategy to find elements based on the comprehensive page map
        """
        logger.info(f"Starting enhanced crawl of {url}")
        results = {
            'pages': [],
            'total_pages_scanned': 0,
            'scanned_urls': set()
        }
        
        try:
            page = await self.browser.new_page()
            
            if auth:
                auth_config = AuthConfig(**auth) if isinstance(auth, dict) else auth
                await self._apply_auth(page, auth_config)
            
            # Process pages according to strategy
            await self._process_page(page, url, strategy, results, depth=0)
            
            # Convert scanned_urls set to list for JSON serialization
            results['scanned_urls'] = list(results['scanned_urls'])
                
            return results
                
        except Exception as e:
            logger.error(f"Error during crawl: {str(e)}")
            raise
        finally:
            if page:
                await page.close()

    async def _process_page(self, page: Any, url: str, strategy: ScanStrategy, results: Dict[str, Any], depth: int = 0) -> None:
        """
        Process a single page according to the strategy
        """
        if url in results['scanned_urls'] or depth >= strategy.scan_depth:
            return

        try:
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(2000)  # Wait for dynamic content

            # Get comprehensive page information
            page_map = await PageMapper.map_page(page)
            
            # Find elements matching strategy criteria
            matched_elements = await self._find_matching_elements(page, strategy, page_map)
            
            # Add page results
            results['pages'].append({
                'url': url,
                'page_title': page_map['page_metadata']['title'],
                'elements': matched_elements,
                'depth': depth
            })
            
            results['scanned_urls'].add(url)
            results['total_pages_scanned'] += 1

            # Process navigation if needed
            if depth < strategy.scan_depth:
                await self._handle_navigation(page, strategy, results, depth)

        except Exception as e:
            logger.error(f"Error processing page {url}: {str(e)}")
            results['pages'].append({
                'url': url,
                'error': str(e),
                'depth': depth
            })

    async def _find_matching_elements(self, page: Any, strategy: ScanStrategy, page_map: Dict[str, Any]) -> List[UIElement]:
        """
        Find elements that match the strategy criteria using the page map and convert them to UIElement objects
        """
        matched_elements = []
        seen_elements = set()  # Track unique elements
        
        logger.info(f"Finding elements matching strategy with {len(strategy.target_elements_description)} targets")
        
        for target in strategy.target_elements_description:
            collections_to_search = self._determine_collections_to_search(target, page_map)
            logger.info(f"Searching for element type '{target.get('type', '*')}' in collections: {[c[0] for c in collections_to_search]}")
            
            # Search through each collection
            for collection_name, elements in collections_to_search:
                for element in elements:
                    # Create a unique identifier for the element
                    element_identifier = self._create_element_identifier(element)
                    
                    if element_identifier in seen_elements:
                        logger.debug(f"Skipping duplicate element: {element.get('tagName')} - {element.get('textContent')}")
                        continue  # Skip if we've already processed this element
                    
                    if self._element_matches_criteria(element, target):
                        seen_elements.add(element_identifier)
                        ui_element = self._create_ui_element(element, target, collection_name)
                        matched_elements.append(ui_element)
        
        logger.info(f"Found {len(matched_elements)} unique matching elements")
        return matched_elements

    def _determine_collections_to_search(self, target: Dict[str, Any], page_map: Dict[str, Any]) -> List[Tuple[str, List[Dict[str, Any]]]]:
        """
        Determine which collections to search based on element type and context
        """
        collections_to_search = []
        element_type = target.get('type', '*').lower()
        purpose = target.get('purpose', '').lower()
        
        # Check if element is part of navigation
        if target.get('is_navigation') or element_type in ['nav', 'menu'] or 'nav' in purpose:
            collections_to_search.append(('navigation_elements', page_map['navigation_elements']))
        
        # Check if element is interactive
        if element_type in ['button', 'a', 'input', 'select', 'textarea'] or target.get('is_interactive'):
            # Only add if not already added via navigation
            if not any(c[0] == 'navigation_elements' for c in collections_to_search):
                collections_to_search.append(('interactive_elements', page_map['interactive_elements']))
        
        # Check if element is part of a form
        if element_type == 'form' or target.get('is_form'):
            collections_to_search.append(('form_elements', page_map['form_elements']))
        
        # Check structural elements
        if element_type in ['ul', 'ol', 'li', 'div', 'section', 'article', 'aside', 'header', 'footer']:
            collections_to_search.append(('structural_elements', page_map['structural_elements']))
        
        # If no specific collection is identified or element could be anywhere, search all collections
        if not collections_to_search:
            collections_to_search = [
                ('navigation_elements', page_map['navigation_elements']),
                ('interactive_elements', page_map['interactive_elements']),
                ('form_elements', page_map['form_elements']),
                ('structural_elements', page_map['structural_elements'])
            ]
        
        return collections_to_search

    def _create_element_identifier(self, element: Dict[str, Any]) -> str:
        """
        Create a unique identifier for an element based on its properties
        """
        identifier_parts = [
            element.get('tagName', ''),
            element.get('textContent', ''),
            str(element.get('attributes', {})),
            str(element.get('dimensions', {}))
        ]
        
        # Add parent context if available to differentiate similar elements in different contexts
        if element.get('context', {}).get('parents'):
            parent_info = [
                f"{p.get('tagName', '')}-{p.get('id', '')}-{p.get('className', '')}"
                for p in element['context']['parents']
            ]
            identifier_parts.extend(parent_info)
        
        return hashlib.md5('|'.join(identifier_parts).encode()).hexdigest()

    def _create_ui_element(self, element: Dict[str, Any], target: Dict[str, Any], collection_name: str) -> UIElement:
        """
        Create a UIElement instance from a matched element
        """
        # Generate a unique element ID based on properties and context
        context_hash = hashlib.md5(
            f"{element.get('tagName', '')}-{element.get('textContent', '')}-{str(element.get('context', {}))}"
            .encode()
        ).hexdigest()[:8]
        
        purpose_slug = target.get('purpose', '').lower().replace(' ', '_')[:30]
        element_id = f"{element['tagName']}_{purpose_slug}_{context_hash}"
        
        return UIElement(
            element_id=element_id,
            element_type=element['tagName'],
            selector=self._generate_smart_selector(element),
            attributes=element.get('attributes', {}),
            visible_text=element.get('textContent'),
            position=element.get('dimensions'),
            metadata={
                'collection': collection_name,
                'context': element.get('context'),
                'visibility': element.get('styles'),
                'has_interactive_children': element.get('hasInteractiveChildren', False),
                'is_navigational': element.get('isNavigational', False),
                'child_count': element.get('childCount', 0)
            }
        )

    def _generate_smart_selector(self, element: Dict[str, Any]) -> str:
        """
        Generate a smart selector that considers the element's context and uniqueness
        """
        selectors = []
        
        # Try ID first (most specific)
        if element.get('id'):
            return f"#{element['id']}"
        
        # Try data-testid
        if element.get('attributes', {}).get('data-testid'):
            return f"[data-testid='{element['attributes']['data-testid']}']"
        
        # Try role with aria-label
        if element.get('role') and element.get('ariaLabel'):
            return f"[role='{element['role']}'][aria-label='{element['ariaLabel']}']"
        
        # Build context-based selector
        context = element.get('context', {})
        parents = context.get('parents', [])
        
        # Start with the furthest parent that has an ID or unique class
        for parent in parents:
            if parent.get('id'):
                selectors.append(f"#{parent['id']}")
                break
            elif parent.get('className'):
                unique_class = parent['className'].split()[0]
                selectors.append(f".{unique_class}")
                break
        
        # Add element's tag and class if available
        if element['tagName']:
            selectors.append(element['tagName'])
        
        if element.get('className'):
            classes = element['className'].split()
            # Use up to 2 classes to maintain specificity without being too rigid
            for cls in classes[:2]:
                selectors.append(f".{cls}")
        
        # Combine selectors
        return ' > '.join(selectors) if selectors else element['tagName']

    def _element_matches_criteria(self, element: Dict[str, Any], target: Dict[str, Any]) -> bool:
        """
        Enhanced element matching that considers context and purpose
        """
        # Check element type
        if target.get('type') and target['type'].lower() != element.get('tagName', '').lower():
            return False

        # Check attributes with fuzzy matching for class names
        for attr_name, attr_value in target.get('attributes', {}).items():
            element_attrs = element.get('attributes', {})
            if attr_name == 'class' and attr_value and element.get('className'):
                # For class, check if any target class exists in element's classes
                element_classes = set(element['className'].lower().split())
                target_classes = set(attr_value.lower().split())
                if not any(tc in element_classes for tc in target_classes):
                    return False
            elif attr_value == '*':
                if attr_name not in element_attrs:
                    return False
            elif element_attrs.get(attr_name) != attr_value:
                return False

        # Check text content with smart matching
        text_contains = target.get('text_contains', '').lower()
        if text_contains:
            element_text = (element.get('textContent', '') or '').lower()
            if text_contains not in element_text:
                # Check if text might be in child elements
                if not element.get('hasInteractiveChildren') and not element.get('childCount', 0) > 0:
                    return False

        # Check navigation context if specified
        if target.get('is_navigation') and not element.get('isNavigational'):
            return False

        # Check visibility if specified
        if target.get('must_be_visible', False) and not element.get('isVisible'):
            return False

        return True

    async def _handle_navigation(self, page: Any, strategy: ScanStrategy, results: Dict[str, Any], depth: int) -> None:
        """
        Handle navigation to other pages based on strategy
        """
        if not strategy.page_navigation_rules:
            return

        for rule in strategy.page_navigation_rules:
            if rule.get('source_page') == page.url or not rule.get('source_page'):
                target_pattern = rule.get('target_pattern', '')
                nav_element = rule.get('navigation_element', {})
                
                # Find and click navigation elements
                elements = await page.query_selector_all(nav_element.get('selector', ''))
                for element in elements:
                    try:
                        # Get href before clicking
                        href = await element.get_attribute('href')
                        if href and (not target_pattern or target_pattern in href):
                            # Create new page for navigation
                            new_page = await self.browser.new_page()
                            await self._process_page(new_page, href, strategy, results, depth + 1)
                            await new_page.close()
                    except Exception as e:
                        logger.error(f"Error during navigation: {str(e)}")
                        continue 