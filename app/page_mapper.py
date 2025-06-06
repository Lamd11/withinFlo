from typing import Dict, Any, List
from playwright.async_api import Page
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PageMapper:
    @staticmethod
    async def map_page(page: Page) -> Dict[str, Any]:
        """
        Creates a comprehensive map of the page including all interactive elements,
        form elements, navigation elements, and page structure.
        """
        try:
            # Get all interactive elements
            interactive_elements = await PageMapper._get_interactive_elements(page)
            
            # Get form elements
            form_elements = await PageMapper._get_form_elements(page)
            
            # Get navigation elements
            navigation_elements = await PageMapper._get_navigation_elements(page)
            
            # Get structural elements
            structural_elements = await PageMapper._get_structural_elements(page)
            
            # Get page structure
            content_structure = await PageMapper._get_content_structure(page)
            
            # Get DOM hierarchy
            dom_hierarchy = await PageMapper._get_dom_hierarchy(page)
            
            return {
                "interactive_elements": interactive_elements,
                "form_elements": form_elements,
                "navigation_elements": navigation_elements,
                "structural_elements": structural_elements,
                "content_structure": content_structure,
                "dom_hierarchy": dom_hierarchy,
                "page_metadata": {
                    "title": await page.title(),
                    "url": page.url
                }
            }
        except Exception as e:
            logger.error(f"Error mapping page: {str(e)}")
            raise

    @staticmethod
    async def _get_interactive_elements(page: Page) -> List[Dict[str, Any]]:
        """Get all interactive elements like buttons, links, inputs, etc."""
        return await page.evaluate("""() => {
            const interactiveSelectors = 'button, a, input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="radio"]';
            return Array.from(document.querySelectorAll(interactiveSelectors)).map(el => ({
                tagName: el.tagName.toLowerCase(),
                type: el.getAttribute('type') || null,
                id: el.id || null,
                name: el.getAttribute('name') || null,
                className: el.className || null,
                textContent: el.textContent?.trim() || null,
                role: el.getAttribute('role') || null,
                ariaLabel: el.getAttribute('aria-label') || null,
                isVisible: el.offsetParent !== null,
                attributes: Object.fromEntries(
                    Array.from(el.attributes).map(attr => [attr.name, attr.value])
                )
            }));
        }""")

    @staticmethod
    async def _get_form_elements(page: Page) -> List[Dict[str, Any]]:
        """Get all form-related elements and their structure"""
        return await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('form')).map(form => ({
                id: form.id || null,
                name: form.getAttribute('name') || null,
                action: form.action || null,
                method: form.method || null,
                fields: Array.from(form.elements).map(el => ({
                    tagName: el.tagName.toLowerCase(),
                    type: el.getAttribute('type') || null,
                    name: el.getAttribute('name') || null,
                    id: el.id || null,
                    required: el.required || false,
                    placeholder: el.getAttribute('placeholder') || null,
                    value: el.tagName.toLowerCase() === 'select' ? 
                        Array.from(el.options).map(opt => ({
                            value: opt.value,
                            text: opt.text,
                            selected: opt.selected
                        })) : null
                }))
            }));
        }""")

    @staticmethod
    async def _get_structural_elements(page: Page) -> List[Dict[str, Any]]:
        """Get all structural elements that form the layout and organization of the page"""
        return await page.evaluate("""() => {
            function getComputedVisibility(el) {
                const style = window.getComputedStyle(el);
                return {
                    isVisible: style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0',
                    position: style.position,
                    zIndex: style.zIndex,
                    display: style.display
                };
            }

            function getElementContext(el) {
                // Get parent context
                const parents = [];
                let parent = el.parentElement;
                while (parent && parents.length < 3) {
                    parents.unshift({
                        tagName: parent.tagName.toLowerCase(),
                        id: parent.id || null,
                        className: parent.className || null,
                        role: parent.getAttribute('role') || null
                    });
                    parent = parent.parentElement;
                }
                
                return {
                    parents,
                    siblings: Array.from(el.parentElement?.children || [])
                        .filter(sibling => sibling !== el)
                        .slice(0, 2)
                        .map(sibling => ({
                            tagName: sibling.tagName.toLowerCase(),
                            className: sibling.className || null
                        }))
                };
            }

            const structuralSelectors = `
                ul, ol, li,
                div[class*="container"], div[class*="wrapper"],
                div[class*="layout"], div[class*="grid"],
                section, article, aside,
                div[role="region"], div[role="group"],
                header, footer, main,
                div > ul, nav > ul, .menu > ul
            `;

            return Array.from(document.querySelectorAll(structuralSelectors))
                .map(el => {
                    const rect = el.getBoundingClientRect();
                    const visibility = getComputedVisibility(el);
                    const context = getElementContext(el);
                    
                    return {
                        tagName: el.tagName.toLowerCase(),
                        id: el.id || null,
                        className: el.className || null,
                        textContent: el.textContent?.trim() || null,
                        role: el.getAttribute('role') || null,
                        ariaLabel: el.getAttribute('aria-label') || null,
                        attributes: Object.fromEntries(
                            Array.from(el.attributes).map(attr => [attr.name, attr.value])
                        ),
                        isVisible: visibility.isVisible,
                        styles: visibility,
                        dimensions: {
                            width: rect.width,
                            height: rect.height,
                            top: rect.top,
                            left: rect.left
                        },
                        context: context,
                        childCount: el.children.length,
                        hasInteractiveChildren: !!el.querySelector('a, button, input, select, textarea'),
                        isNavigational: !!el.closest('nav, [role="navigation"], header, .navigation, .nav, .menu')
                    };
                });
        }""")

    @staticmethod
    async def _get_navigation_elements(page: Page) -> List[Dict[str, Any]]:
        """Get all navigation-related elements with improved detection"""
        return await page.evaluate("""() => {
            function isNavigationContainer(el) {
                // Check if element or its parent is a navigation container
                const navClasses = ['nav', 'navigation', 'menu', 'navbar'];
                const hasNavClass = navClasses.some(cls => 
                    el.className.toLowerCase().includes(cls)
                );
                return (
                    el.tagName.toLowerCase() === 'nav' ||
                    el.getAttribute('role') === 'navigation' ||
                    hasNavClass ||
                    el.matches('header nav, footer nav, .header nav, .footer nav') ||
                    (el.parentElement && isNavigationContainer(el.parentElement))
                );
            }

            function getNavigationStructure(el, depth = 0) {
                if (depth > 3) return null; // Prevent infinite recursion
                
                const children = Array.from(el.children)
                    .map(child => {
                        if (child.tagName.toLowerCase() === 'ul' || 
                            child.tagName.toLowerCase() === 'ol' ||
                            child.className.toLowerCase().includes('menu')) {
                            return getNavigationStructure(child, depth + 1);
                        }
                        return null;
                    })
                    .filter(Boolean);

                return {
                    tagName: el.tagName.toLowerCase(),
                    id: el.id || null,
                    className: el.className || null,
                    textContent: el.textContent?.trim() || null,
                    href: el.href || null,
                    role: el.getAttribute('role') || null,
                    ariaLabel: el.getAttribute('aria-label') || null,
                    isVisible: el.offsetParent !== null,
                    attributes: Object.fromEntries(
                        Array.from(el.attributes).map(attr => [attr.name, attr.value])
                    ),
                    children: children
                };
            }

            // First, find all potential navigation containers
            const navContainers = Array.from(document.querySelectorAll('nav, [role="navigation"], header, footer, .navigation, .nav, .menu'));
            
            // Then, process each container and its children
            return navContainers
                .filter(el => isNavigationContainer(el))
                .map(container => getNavigationStructure(container));
        }""")

    @staticmethod
    async def _get_content_structure(page: Page) -> Dict[str, Any]:
        """Get the content structure including headings, sections, and main content areas"""
        return await page.evaluate("""() => {
            return {
                headings: Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6')).map(h => ({
                    level: parseInt(h.tagName.substring(1)),
                    text: h.textContent?.trim() || null,
                    id: h.id || null
                })),
                sections: Array.from(document.querySelectorAll('section, article, main, div[role="main"]')).map(section => ({
                    tagName: section.tagName.toLowerCase(),
                    id: section.id || null,
                    className: section.className || null,
                    role: section.getAttribute('role') || null,
                    ariaLabel: section.getAttribute('aria-label') || null
                })),
                landmarks: Array.from(document.querySelectorAll('[role="banner"], [role="main"], [role="complementary"], [role="contentinfo"]')).map(landmark => ({
                    role: landmark.getAttribute('role'),
                    id: landmark.id || null,
                    ariaLabel: landmark.getAttribute('aria-label') || null
                }))
            };
        }""")

    @staticmethod
    async def _get_dom_hierarchy(page: Page) -> Dict[str, Any]:
        """Get a simplified DOM hierarchy focusing on important structural elements"""
        return await page.evaluate("""() => {
            function getElementInfo(element, depth = 0, maxDepth = 5) {
                if (depth >= maxDepth) return null;
                
                return {
                    tagName: element.tagName.toLowerCase(),
                    id: element.id || null,
                    className: element.className || null,
                    role: element.getAttribute('role') || null,
                    children: Array.from(element.children)
                        .map(child => getElementInfo(child, depth + 1, maxDepth))
                        .filter(Boolean)
                };
            }
            
            return getElementInfo(document.body, 0, 3);  // Limit depth to 3 levels for practicality
        }""") 