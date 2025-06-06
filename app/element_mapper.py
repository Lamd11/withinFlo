from playwright.async_api import Page
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from .models import ElementMapEntry, PageElementMap, ElementState, ElementRelation
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ElementMapper:
    """
    Handles the initial discovery phase of web page scanning.
    Creates a comprehensive map of all interactive elements on the page.
    """
    
    def __init__(self):
        self.seen_elements = set()  # Track unique elements
        
    def _clean_selector(self, selector: str) -> str:
        """Clean up selector to be more readable and maintainable."""
        # Remove unnecessary :nth-of-type when there's an ID
        if '#' in selector:
            selector = re.sub(r':nth-of-type\(\d+\)', '', selector)
        
        # Simplify nested divs
        selector = re.sub(r'div > div > div', 'div', selector)
        
        # If we have an ID, just use that
        if '#' in selector:
            id_part = re.search(r'#[\w-]+', selector)
            if id_part:
                return id_part.group()
        
        return selector.strip()

    def _is_duplicate_element(self, element: ElementMapEntry) -> bool:
        """Check if this element is a duplicate based on key properties."""
        element_key = (
            element.selector,
            element.element_type,
            element.visible_text,
            element.attributes.get('href', ''),
            element.position.get('x', 0) if element.position else 0,
            element.position.get('y', 0) if element.position else 0
        )
        
        if element_key in self.seen_elements:
            return True
            
        self.seen_elements.add(element_key)
        return False

    def _should_include_element(self, element: ElementMapEntry) -> bool:
        """Determine if an element should be included in the map."""
        # Skip hidden elements unless they're important
        if element.state == ElementState.HIDDEN:
            important_attributes = ['data-testid', 'id', 'name']
            has_important_attr = any(attr in element.attributes for attr in important_attributes)
            if not has_important_attr:
                return False

        # Skip elements without meaningful interaction
        if element.interaction_type == 'unknown' and not element.visible_text:
            return False

        # Skip elements with overly complex selectors unless they have an ID
        if '#' not in element.selector and len(element.selector.split(' > ')) > 3:
            return False

        return True

    async def create_element_map(self, page: Page) -> PageElementMap:
        """Creates a comprehensive map of all interactive elements on the page."""
        logger.info(f"Creating element map for page: {page.url}")
        
        # Reset seen elements for new page
        self.seen_elements = set()
        
        # Get all interactive elements
        elements = await self._get_all_interactive_elements(page)
        
        # Create element map entries
        element_entries = []
        for element in elements:
            entry = await self._create_element_entry(element, page)
            if entry and self._should_include_element(entry) and not self._is_duplicate_element(entry):
                # Clean up the selector
                entry.selector = self._clean_selector(entry.selector)
                # Clean up empty or None values
                entry.attributes = {k: v for k, v in entry.attributes.items() if v}
                entry.accessibility = {k: v for k, v in entry.accessibility.items() if v is not None}
                if not entry.visible_text:
                    entry.visible_text = None
                element_entries.append(entry)
        
        # Build relationships between elements
        await self._build_element_relationships(element_entries, page)
        
        # Sort elements by position and visibility
        element_entries.sort(
            key=lambda x: (
                x.state != ElementState.VISIBLE,  # Visible elements first
                not x.position,  # Elements with position info first
                x.position.get('y', float('inf')) if x.position else float('inf'),  # Sort by Y position
                x.position.get('x', float('inf')) if x.position else float('inf')  # Then by X position
            )
        )
        
        return PageElementMap(
            url=page.url,
            timestamp=datetime.utcnow(),
            title=await page.title(),
            elements=element_entries
        )
    
    async def _get_all_interactive_elements(self, page: Page) -> List[Any]:
        """
        Gets all potentially interactive elements on the page.
        """
        return await page.query_selector_all("""
            button, 
            input, 
            select, 
            textarea,
            a[href],
            [role="button"],
            [role="link"],
            [role="menuitem"],
            [role="tab"],
            [role="checkbox"],
            [role="radio"],
            [role="switch"],
            [role="textbox"],
            [role="combobox"],
            [onclick],
            [onsubmit],
            form
        """)
    
    async def _create_element_entry(self, element: Any, page: Page) -> Optional[ElementMapEntry]:
        """
        Creates a detailed entry for a single element.
        """
        try:
            # Basic element properties
            element_type = await element.evaluate("el => el.tagName.toLowerCase()")
            
            # Generate a unique selector
            selector = await self._generate_unique_selector(element)
            selector = self._clean_selector(selector)
            
            # Get element attributes
            attributes = await element.evaluate("""el => {
                const attrs = {};
                for (const attr of el.attributes) {
                    if (attr.value) {  // Only include non-empty attributes
                        attrs[attr.name] = attr.value;
                    }
                }
                return attrs;
            }""")
            
            # Get element position
            position = await element.bounding_box()
            position_dict = None
            if position:
                position_dict = {
                    "x": round(position["x"], 2),
                    "y": round(position["y"], 2),
                    "width": round(position["width"], 2),
                    "height": round(position["height"], 2)
                }
            
            # Check visibility and state
            is_visible = await element.is_visible()
            is_enabled = await element.evaluate("el => !el.disabled")
            state = ElementState.VISIBLE if is_visible and is_enabled else \
                   ElementState.DISABLED if not is_enabled else \
                   ElementState.HIDDEN
            
            # Get accessibility properties (only non-null values)
            accessibility = await element.evaluate("""el => {
                const props = {
                    role: el.getAttribute('role'),
                    ariaLabel: el.getAttribute('aria-label'),
                    ariaDescribedby: el.getAttribute('aria-describedby'),
                    ariaExpanded: el.getAttribute('aria-expanded'),
                    ariaHidden: el.getAttribute('aria-hidden'),
                    tabIndex: el.tabIndex
                };
                return Object.fromEntries(Object.entries(props).filter(([_, v]) => v != null));
            }""")
            
            # Get visible text (trimmed)
            visible_text = await element.text_content()
            visible_text = visible_text.strip() if visible_text else None
            
            # Determine interaction type
            interaction_type = await self._determine_interaction_type(element)
            
            return ElementMapEntry(
                element_id=selector,
                element_type=element_type,
                selector=selector,
                attributes=attributes,
                visible_text=visible_text,
                position=position_dict,
                state=state,
                accessibility=accessibility,
                relations=ElementRelation(),
                page_url=page.url,
                page_title=await page.title(),
                interaction_type=interaction_type
            )
            
        except Exception as e:
            logger.error(f"Error creating element entry: {str(e)}")
            return None
    
    async def _generate_unique_selector(self, element: Any) -> str:
        """
        Generates a unique selector for the element.
        """
        return await element.evaluate("""el => {
            if (el.id) return '#' + el.id;
            if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
            
            const path = [];
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
                    if (nth !== 1) selector += `:nth-of-type(${nth})`;
                }
                path.unshift(selector);
                el = el.parentNode;
            }
            return path.join(' > ');
        }""")
    
    async def _determine_interaction_type(self, element: Any) -> str:
        """
        Determines the type of interaction possible with this element.
        """
        return await element.evaluate("""el => {
            if (el.tagName === 'BUTTON' || el.getAttribute('role') === 'button' || el.onclick) return 'clickable';
            if (el.tagName === 'A' || el.getAttribute('role') === 'link') return 'link';
            if (el.tagName === 'INPUT') {
                const type = el.type.toLowerCase();
                if (type === 'text' || type === 'email' || type === 'password') return 'input';
                if (type === 'checkbox' || type === 'radio') return type;
                if (type === 'submit') return 'submit';
            }
            if (el.tagName === 'SELECT') return 'select';
            if (el.tagName === 'TEXTAREA') return 'input';
            if (el.tagName === 'FORM') return 'form';
            return 'unknown';
        }""")
    
    async def _build_element_relationships(self, elements: List[ElementMapEntry], page: Page) -> None:
        """
        Builds parent/child/sibling relationships between elements.
        """
        for element in elements:
            try:
                # Get the actual element again
                el = await page.query_selector(element.selector)
                if not el:
                    continue
                
                # Find parent
                parent = await el.evaluate("""el => {
                    const parent = el.parentElement;
                    if (!parent) return null;
                    if (parent.id) return '#' + parent.id;
                    return null;  // For now, only track parents with IDs
                }""")
                
                # Find children
                children = await el.evaluate("""el => {
                    return Array.from(el.children)
                        .filter(child => child.id)
                        .map(child => '#' + child.id);
                }""")
                
                # Find siblings
                siblings = await el.evaluate("""el => {
                    const siblings = [];
                    let sibling = el.parentElement?.firstElementChild;
                    while (sibling) {
                        if (sibling !== el && sibling.id) {
                            siblings.push('#' + sibling.id);
                        }
                        sibling = sibling.nextElementSibling;
                    }
                    return siblings;
                }""")
                
                element.relations = ElementRelation(
                    parent_id=parent,
                    child_ids=children,
                    siblings_ids=siblings
                )
                
            except Exception as e:
                logger.error(f"Error building relationships for element {element.selector}: {str(e)}")
                continue 