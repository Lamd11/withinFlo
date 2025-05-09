from playwright.sync_api import sync_playwright
from typing import List, Dict, Any
import time
from .models import UIElement, AuthConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebsiteCrawler:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        
    def __del__(self):
        self.browser.close()
        self.playwright.stop()

    def _apply_auth(self, page, auth: AuthConfig):
        if auth.type == "basic" and auth.username and auth.password:
            page.set_http_credentials(auth.username, auth.password)
        elif auth.type == "session" and auth.token:
            if auth.token_type == "cookie":
                page.context.add_cookies([{
                    "name": "session",
                    "value": auth.token,
                    "url": page.url
                }])
            elif auth.token_type == "bearer":
                page.set_extra_http_headers({
                    "Authorization": f"Bearer {auth.token}"
                })

    def _extract_element_info(self, element) -> Dict[str, Any]:
        try:
            box = element.bounding_box()
            position = {
                "x": box["x"],
                "y": box["y"],
                "width": box["width"],
                "height": box["height"]
            } if box else None
        except:
            position = None

        return {
            "element_type": element.evaluate("el => el.tagName.toLowerCase()"),
            "selector": self._generate_selector(element),
            "attributes": element.evaluate("""el => {
                const attrs = {};
                for (const attr of el.attributes) {
                    attrs[attr.name] = attr.value;
                }
                return attrs;
            }"""),
            "visible_text": element.evaluate("el => el.textContent?.trim()"),
            "position": position
        }

    def _generate_selector(self, element) -> str:
        # Try to find a unique identifier
        if element.get_attribute("id"):
            return f"#{element.get_attribute('id')}"
        
        # Try to use data-testid if available
        if element.get_attribute("data-testid"):
            return f"[data-testid='{element.get_attribute('data-testid')}']"
        
        # Try to use name attribute
        if element.get_attribute("name"):
            return f"[name='{element.get_attribute('name')}']"
        
        # Fallback to a more complex selector
        return element.evaluate("""el => {
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

    def crawl(self, url: str, auth: AuthConfig = None) -> List[UIElement]:
        logger.info(f"Starting crawl of {url}")
        page = self.browser.new_page()
        
        try:
            # Apply authentication if provided
            if auth:
                self._apply_auth(page, auth)
            
            # Navigate to the page
            page.goto(url, wait_until="networkidle")
            
            # Wait for dynamic content
            time.sleep(5)  # Basic wait for dynamic content
            
            # Get page title
            page_title = page.title()
            
            # Find all interactive elements
            elements = []
            selectors = [
                "button", "input", "select", "textarea", "a[href]",
                "form", "img[alt]", "h1, h2, h3, h4, h5, h6",
                "[role='button']", "[role='link']", "[role='textbox']"
            ]
            
            for selector in selectors:
                page_elements = page.query_selector_all(selector)
                for i, element in enumerate(page_elements):
                    try:
                        element_info = self._extract_element_info(element)
                        elements.append(UIElement(
                            element_id=f"{element_info['element_type']}_{i}",
                            **element_info
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to extract element info: {str(e)}")
                        continue
            
            logger.info(f"Found {len(elements)} elements on {url}")
            return elements
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
            raise
        finally:
            page.close() 