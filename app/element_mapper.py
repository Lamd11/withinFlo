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
        self.functional_groups = {}  # Track groups of related elements
        
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

    def _get_element_signature(self, element: ElementMapEntry) -> tuple:
        """Generate a unique signature for an element based on its functional characteristics."""
        return (
            element.selector,
            element.element_type,
            element.visible_text,
            tuple(sorted(element.attributes.items())),
            tuple(element.position.items()) if element.position else None,
            element.interaction_type
        )

    def _calculate_similarity_score(self, elem1: ElementMapEntry, elem2: ElementMapEntry) -> float:
        """Calculate a similarity score between two elements."""
        score = 0.0
        
        # Position overlap check with improved accuracy
        if elem1.position and elem2.position:
            x1, y1 = elem1.position.get('x', 0), elem1.position.get('y', 0)
            x2, y2 = elem2.position.get('x', 0), elem2.position.get('y', 0)
            w1, h1 = elem1.position.get('width', 0), elem1.position.get('height', 0)
            w2, h2 = elem2.position.get('width', 0), elem2.position.get('height', 0)
            
            # Calculate overlap area
            x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            y_overlap = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
            overlap_area = x_overlap * y_overlap
            total_area = min(w1 * h1, w2 * h2)
            
            if total_area > 0:
                overlap_ratio = overlap_area / total_area
                if overlap_ratio > 0.8:  # If elements overlap by more than 80%
                    score += 0.5  # Increased weight for significant overlap
                elif overlap_ratio > 0.5:  # If elements overlap by more than 50%
                    score += 0.3
        
        # Text similarity with improved matching
        if elem1.visible_text and elem2.visible_text:
            text1 = elem1.visible_text.lower().strip()
            text2 = elem2.visible_text.lower().strip()
            if text1 == text2:
                score += 0.3
            elif text1 in text2 or text2 in text1:
                score += 0.2
        
        # Selector similarity check
        if self._are_selectors_related(elem1.selector, elem2.selector):
            score += 0.2
        
        # Attribute similarity with improved matching
        common_attrs = set(elem1.attributes.items()) & set(elem2.attributes.items())
        if common_attrs:
            # Give more weight to important attributes
            important_attrs = {'id', 'name', 'data-testid', 'href', 'role'}
            important_matches = sum(1 for k, _ in common_attrs if k in important_attrs)
            if important_matches > 0:
                score += 0.2
            score += 0.1 * (len(common_attrs) / max(len(elem1.attributes), len(elem2.attributes)))
        
        # Interaction type similarity
        if elem1.interaction_type == elem2.interaction_type:
            score += 0.1
            
        return score

    def _are_selectors_related(self, selector1: str, selector2: str) -> bool:
        """Check if two selectors are related (one might be a parent/child of the other)."""
        # Clean selectors for comparison
        s1 = selector1.replace(':nth-of-type(1)', '').strip()
        s2 = selector2.replace(':nth-of-type(1)', '').strip()
        
        # Check if selectors are the same after cleaning
        if s1 == s2:
            return True
            
        # Check if one selector is contained within the other
        if s1 in s2 or s2 in s1:
            return True
            
        # Check if they share the same ID
        id_pattern = r'#[\w-]+'
        ids1 = set(re.findall(id_pattern, s1))
        ids2 = set(re.findall(id_pattern, s2))
        if ids1 & ids2:
            return True
            
        return False

    def _analyze_parent_child_relationship(self, elem1: ElementMapEntry, elem2: ElementMapEntry) -> Optional[str]:
        """Analyze if two elements have a parent-child relationship and determine which is preferred."""
        # If one element contains the other in DOM
        if elem1.selector in elem2.selector or elem2.selector in elem1.selector:
            # Prefer interactive elements over containers
            interactive_types = {'a', 'button', 'input', 'select', 'textarea'}
            if elem1.element_type in interactive_types and elem2.element_type not in interactive_types:
                return 'elem1'
            if elem2.element_type in interactive_types and elem1.element_type not in interactive_types:
                return 'elem2'
            
            # Prefer elements with direct event handlers
            if 'onclick' in elem1.attributes and 'onclick' not in elem2.attributes:
                return 'elem1'
            if 'onclick' in elem2.attributes and 'onclick' not in elem1.attributes:
                return 'elem2'
            
            # Prefer elements with ARIA roles
            if elem1.accessibility.get('role') and not elem2.accessibility.get('role'):
                return 'elem1'
            if elem2.accessibility.get('role') and not elem1.accessibility.get('role'):
                return 'elem2'
        
        return None

    def _should_merge_elements(self, elem1: ElementMapEntry, elem2: ElementMapEntry) -> bool:
        """Determine if two elements should be merged into a functional group."""
        # Calculate similarity score
        similarity_score = self._calculate_similarity_score(elem1, elem2)
        
        # Check for parent-child relationship
        relationship = self._analyze_parent_child_relationship(elem1, elem2)
        
        # Check if elements serve the same purpose
        same_purpose = (
            # Same visible text
            (elem1.visible_text and elem1.visible_text == elem2.visible_text) or
            # Same ARIA label
            (elem1.accessibility.get('ariaLabel') and 
             elem1.accessibility.get('ariaLabel') == elem2.accessibility.get('ariaLabel')) or
            # Same ID attribute
            (elem1.attributes.get('id') and 
             elem1.attributes.get('id') == elem2.attributes.get('id'))
        )
        
        # Elements are similar enough to merge if any of these conditions are met:
        # 1. High similarity score (> 0.6 - lowered threshold)
        # 2. Clear parent-child relationship
        # 3. Same functional purpose
        return (similarity_score > 0.6 or 
                relationship is not None or 
                same_purpose)

    def _merge_functional_groups(self, elements: List[ElementMapEntry]) -> List[ElementMapEntry]:
        """Merge elements into functional groups and select the best representative."""
        groups = {}
        processed_elements = []
        
        # First pass: group similar elements
        for elem in elements:
            added_to_group = False
            elem_sig = self._get_element_signature(elem)
            
            # Check against existing groups
            for group_id, group_elements in groups.items():
                if any(self._should_merge_elements(elem, existing_elem) 
                      for existing_elem in group_elements):
                    groups[group_id].append(elem)
                    added_to_group = True
                    break
            
            # Create new group if no match found
            if not added_to_group:
                groups[elem_sig] = [elem]
        
        # Second pass: select best representative from each group
        for group_elements in groups.values():
            if len(group_elements) == 1:
                processed_elements.append(group_elements[0])
                continue
            
            # Score each element to find the best representative
            scored_elements = []
            for elem in group_elements:
                score = 0
                # Prefer elements with direct interaction capabilities
                if elem.element_type in {'a', 'button', 'input'}:
                    score += 3
                # Prefer elements with ARIA roles
                if elem.accessibility.get('role'):
                    score += 2
                # Prefer elements with event handlers
                if any(attr.startswith('on') for attr in elem.attributes):
                    score += 2
                # Prefer elements with IDs
                if 'id' in elem.attributes:
                    score += 1
                scored_elements.append((score, elem))
            
            # Add the highest scored element
            best_element = max(scored_elements, key=lambda x: x[0])[1]
            processed_elements.append(best_element)
        
        return processed_elements

    async def create_element_map(self, page: Page) -> PageElementMap:
        """Creates a comprehensive map of all interactive elements on the page."""
        logger.info(f"Creating element map for page: {page.url}")
        
        # Reset tracking sets
        self.seen_elements = set()
        self.functional_groups = {}
        
        # Get all interactive elements
        elements = await self._get_all_interactive_elements(page)
        
        # Create element map entries
        element_entries = []
        for element in elements:
            entry = await self._create_element_entry(element, page)
            if entry and self._should_include_element(entry):
                entry.selector = self._clean_selector(entry.selector)
                entry.attributes = {k: v for k, v in entry.attributes.items() if v}
                entry.accessibility = {k: v for k, v in entry.accessibility.items() if v is not None}
                if not entry.visible_text:
                    entry.visible_text = None
                element_entries.append(entry)
        
        # Merge similar elements and select best representatives
        element_entries = self._merge_functional_groups(element_entries)
        
        # Build relationships between remaining elements
        await self._build_element_relationships(element_entries, page)
        
        # Sort elements by position and visibility
        element_entries.sort(
            key=lambda x: (
                x.state != ElementState.VISIBLE,
                not x.position,
                x.position.get('y', float('inf')) if x.position else float('inf'),
                x.position.get('x', float('inf')) if x.position else float('inf')
            )
        )
        
        return PageElementMap(
            url=page.url,
            timestamp=datetime.utcnow(),
            title=await page.title(),
            elements=element_entries
        )
    
    async def _get_all_interactive_elements(self, page: Page) -> List[Any]:
        """Gets all potentially interactive elements on the page."""
        # First, get all elements that match our criteria
        elements = await page.query_selector_all("""
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
        
        # Create a set to track processed elements
        processed = set()
        unique_elements = []
        
        for element in elements:
            # Get element's unique identifier
            identifier = await element.evaluate("""el => {
                if (el.id) return `#${el.id}`;
                if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
                return el.outerHTML;
            }""")
            
            if identifier not in processed:
                processed.add(identifier)
                unique_elements.append(element)
        
        return unique_elements
    
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