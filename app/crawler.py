from playwright.async_api import async_playwright
from typing import List, Dict, Any
from .models import UIElement, AuthConfig, ScanStrategy
import logging

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
        Get initial content from the website before creating a scan strategy.
        This includes visible text content, page title, and basic structure.
        """
        logger.info(f"Getting initial content from {url}")
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
            
            # Get page title
            page_title = await page.title()
            
            # Get visible text content
            text_content = await page.evaluate('''() => {
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                
                let text = [];
                let node;
                
                while(node = walker.nextNode()) {
                    const trimmed = node.textContent.trim();
                    if (trimmed) {
                        text.push(trimmed);
                    }
                }
                
                return text.join(" ");
            }''')
            
            # Get basic page structure (headings and main sections)
            structure = await page.evaluate('''() => {
                const headings = Array.from(document.querySelectorAll('h1, h2, h3')).map(h => ({
                    level: h.tagName.toLowerCase(),
                    text: h.textContent.trim()
                }));
                
                const mainSections = Array.from(document.querySelectorAll('main, section, article, nav, header, footer')).map(section => ({
                    type: section.tagName.toLowerCase(),
                    id: section.id || '',
                    class: section.className || ''
                }));
                
                return { headings, mainSections };
            }''')
            
            return {
                "page_title": page_title,
                "text_content": text_content,
                "structure": structure
            }
            
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
        """Enhanced crawl method with multi-page support."""
        if not strategy:
            logger.warning("No strategy provided. Cannot scan")
            return None
            
        logger.info(f"Starting multi-page crawl from {url}")
        page = await self.browser.new_page()
        all_results = []
        
        try:
            # Apply authentication if provided
            if auth:
                auth_config = AuthConfig(**auth) if isinstance(auth, dict) else auth
                await self._apply_auth(page, auth_config)
            
            # Initialize queue with start URL
            pages_to_scan = [(url, 0)]  # (url, depth)
            self.scanned_urls = {url}
            
            while pages_to_scan and len(self.scanned_urls) < strategy.max_pages_to_scan:
                current_url, current_depth = pages_to_scan.pop(0)
                
                if current_depth > strategy.scan_depth:
                    continue
                
                # Navigate to the page
                try:
                    await page.goto(current_url, wait_until="networkidle")
                    await page.wait_for_timeout(5000)  # Wait for dynamic content
                except Exception as e:
                    logger.error(f"Failed to navigate to {current_url}: {str(e)}")
                    continue
                
                # Get page title
                page_title = await page.title()
                logger.info(f"Scanning page: {page_title} ({current_url})")
                
                # Find elements on current page
                elements = []
                for desc in strategy.target_elements_description:
                    try:
                        # Building selector based on the element's description
                        tag_type = desc.get('type', '*')
                        attributes = desc.get('attributes', {})
                        text_contains = desc.get('text_contains', '')
                        purpose = desc.get('purpose', '')

                        # Build multiple selector strategies
                        selectors = []
                        
                        # Strategy 1: Direct attribute matching
                        attr_selector = []
                        for attr_name, attr_value in attributes.items():
                            if attr_value == '*':
                                attr_selector.append(f'[{attr_name}]')
                            else:
                                escaped_value = str(attr_value).replace('"', '\\"')
                                attr_selector.append(f'[{attr_name}="{escaped_value}"]')
                        selectors.append(f"{tag_type}{''.join(attr_selector)}")
                        
                        # Strategy 2: Contains text matching
                        if text_contains:
                            text_selector = f"{tag_type}:has-text('{text_contains}')"
                            selectors.append(text_selector)
                            
                            # Also try with innerText for deeper nested elements
                            inner_text_selector = f"{tag_type} >> text={text_contains}"
                            selectors.append(inner_text_selector)
                        
                        # Strategy 3: Nested element search with contains
                        if text_contains:
                            nested_selector = f"//*[contains(text(), '{text_contains}')]"
                            selectors.append(nested_selector)

                        # Try each selector strategy
                        found_elements = []
                        for selector in selectors:
                            logger.info(f"Trying selector strategy: {selector}")
                            try:
                                # Use waitForSelector with a short timeout to handle dynamic content
                                try:
                                    await page.wait_for_selector(selector, timeout=2000)
                                except:
                                    logger.debug(f"Selector {selector} not immediately available")
                                    
                                # Get all elements matching the selector
                                current_elements = await page.locator(selector).all()
                                
                                if current_elements:
                                    logger.info(f"Found {len(current_elements)} elements with selector: {selector}")
                                    found_elements.extend(current_elements)
                                
                            except Exception as selector_error:
                                logger.debug(f"Selector strategy {selector} failed: {str(selector_error)}")
                                continue

                        # Remove duplicates based on element handle comparison
                        unique_elements = []
                        seen_handles = set()
                        
                        for element in found_elements:
                            handle = await element.evaluate('element => element.outerHTML')
                            if handle not in seen_handles:
                                seen_handles.add(handle)
                                unique_elements.append(element)

                        # Processing unique elements
                        for i, element in enumerate(unique_elements):
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
                
                # Store results for current page
                page_result = {
                    "url": current_url,
                    "page_title": page_title,
                    "elements": elements,
                    "depth": current_depth
                }
                all_results.append(page_result)
                
                # Find navigation elements if we haven't reached max depth
                if current_depth < strategy.scan_depth and strategy.page_navigation_rules:
                    nav_elements = await self._find_navigation_elements(page, strategy.page_navigation_rules)
                    
                    for nav_element in nav_elements:
                        # Get target URL either from href or by simulating navigation
                        target_url = nav_element.get('href')
                        
                        if not target_url:
                            # Create a new page to test navigation without affecting main page
                            test_page = await self.browser.new_page()
                            try:
                                await test_page.goto(current_url, wait_until="networkidle")
                                await self._navigate_to_page(test_page, nav_element)
                                target_url = test_page.url
                            finally:
                                await test_page.close()
                        
                        # Check if URL matches any target patterns and hasn't been scanned
                        if target_url and target_url not in self.scanned_urls:
                            for rule in strategy.page_navigation_rules:
                                if rule['target_pattern'] in target_url:
                                    self.scanned_urls.add(target_url)
                                    pages_to_scan.append((target_url, current_depth + 1))
                                    break
            
            # Return combined results
            return {
                "pages": all_results,
                "total_pages_scanned": len(self.scanned_urls)
            }
            
        except Exception as e:
            logger.error(f"Error in multi-page crawl: {str(e)}")
            raise
        finally:
            await page.close() 