from playwright.async_api import async_playwright
from typing import List, Dict, Any
import time
from app.models import UIElement, AuthConfig
import logging

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

    async def crawl(self, url: str, auth: dict = None) -> Dict[str, Any]:
        logger.info(f"Starting crawl of {url}")
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
            logger.info(f"Page title: {page_title}")
            
            # Find all interactive elements
            elements = []
            selectors = [
                "button", "input", "select", "textarea", "a[href]",
                "form", "img[alt]", "h1, h2, h3, h4, h5, h6",
                "[role='button']", "[role='link']", "[role='textbox']",
                ".btn", ".button", "[type='submit']", "[type='button']",
                ".card", ".product", ".item", ".nav-link", ".menu-item"
            ]
            
            for selector in selectors:
                page_elements = await page.query_selector_all(selector)
                for i, element in enumerate(page_elements):
                    try:
                        element_info = await self._extract_element_info(element)
                        elements.append(UIElement(
                            element_id=f"{element_info['element_type']}_{i}",
                            **element_info
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to extract element info: {str(e)}")
                        continue
            
            logger.info(f"Found {len(elements)} elements on {url}")
            
            # Return both elements and page title in a dictionary
            return {
                "elements": elements,
                "page_title": page_title
            }
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
            raise
        finally:
            await page.close() 