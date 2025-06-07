from typing import List, Dict, Any, Optional, Set, Tuple
from .models import UIElement, TestCase
import logging
from difflib import SequenceMatcher
import re
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class FunctionalGroup:
    """Represents a group of functionally similar elements."""
    primary_element: UIElement
    similar_elements: List[UIElement]
    purpose: str
    interaction_type: str

class TestCaseDeduplicator:
    """Handles deduplication of test cases by analyzing element relationships and functional similarity."""
    
    def __init__(self):
        self.functional_groups: Dict[str, FunctionalGroup] = {}
        self.similarity_threshold = 0.85
        self.functional_patterns = {
            'navigation': {
                'keywords': {'next', 'previous', 'prev', 'forward', 'back'},
                'common_parents': {'nav', 'pagination', 'slider', 'carousel'},
                'typical_elements': {'a', 'button', 'span'},
            },
            'form_input': {
                'keywords': {'submit', 'input', 'text', 'email', 'search'},
                'common_parents': {'form', 'fieldset'},
                'typical_elements': {'input', 'textarea', 'select'},
            },
            'action': {
                'keywords': {'click', 'submit', 'send', 'save', 'delete'},
                'common_parents': {'form', 'modal', 'dialog'},
                'typical_elements': {'button', 'a'},
            }
        }

    def _calculate_element_similarity(self, elem1: UIElement, elem2: UIElement) -> float:
        """Calculate similarity score between two elements based on multiple factors."""
        scores = []
        
        # Compare selectors (30% weight)
        if self._are_selectors_related(elem1.selector, elem2.selector):
            scores.append(0.3)
        
        # Compare visible text (25% weight)
        if elem1.visible_text and elem2.visible_text:
            text_similarity = SequenceMatcher(None, 
                elem1.visible_text.lower(), 
                elem2.visible_text.lower()
            ).ratio()
            scores.append(text_similarity * 0.25)
            
        # Compare element types (20% weight)
        if elem1.element_type == elem2.element_type:
            scores.append(0.2)
            
        # Compare attributes (15% weight)
        attr_similarity = self._calculate_attribute_similarity(
            elem1.attributes, 
            elem2.attributes
        )
        scores.append(attr_similarity * 0.15)
        
        # Compare position (10% weight)
        if elem1.position and elem2.position:
            pos_similarity = self._calculate_position_similarity(
                elem1.position, 
                elem2.position
            )
            scores.append(pos_similarity * 0.1)
            
        return sum(scores)

    def _are_selectors_related(self, selector1: str, selector2: str) -> bool:
        """Check if two selectors are related (parent-child or sharing common attributes)."""
        # Normalize selectors
        s1 = re.sub(r'\s+', ' ', selector1.strip())
        s2 = re.sub(r'\s+', ' ', selector2.strip())
        
        # Check for direct parent-child relationship
        if s1 in s2 or s2 in s1:
            return True
            
        # Check for common identifying attributes
        attr_pattern = r'(?:id|class|name|data-testid)=["\']([^"\']+)["\']'
        attrs1 = set(re.findall(attr_pattern, s1))
        attrs2 = set(re.findall(attr_pattern, s2))
        
        return bool(attrs1 & attrs2)  # Return True if there are common attributes

    def _calculate_attribute_similarity(self, attrs1: Dict[str, str], attrs2: Dict[str, str]) -> float:
        """Calculate similarity score between two sets of attributes."""
        if not attrs1 or not attrs2:
            return 0.0
            
        # Focus on important attributes
        important_attrs = {'id', 'class', 'name', 'data-testid', 'role', 'aria-label'}
        
        # Get important attributes from both elements
        attrs1_important = {k: v for k, v in attrs1.items() if k in important_attrs}
        attrs2_important = {k: v for k, v in attrs2.items() if k in important_attrs}
        
        if not attrs1_important or not attrs2_important:
            return 0.0
            
        # Calculate similarity based on common attributes and their values
        common_keys = set(attrs1_important.keys()) & set(attrs2_important.keys())
        if not common_keys:
            return 0.0
            
        value_similarities = []
        for key in common_keys:
            value_sim = SequenceMatcher(None, 
                str(attrs1_important[key]).lower(), 
                str(attrs2_important[key]).lower()
            ).ratio()
            value_similarities.append(value_sim)
            
        return sum(value_similarities) / len(value_similarities)

    def _calculate_position_similarity(self, pos1: Dict[str, Any], pos2: Dict[str, Any]) -> float:
        """Calculate similarity score based on element positions."""
        try:
            x1, y1 = pos1.get('x', 0), pos1.get('y', 0)
            x2, y2 = pos2.get('x', 0), pos2.get('y', 0)
            w1, h1 = pos1.get('width', 0), pos1.get('height', 0)
            w2, h2 = pos2.get('width', 0), pos2.get('height', 0)
            
            # Calculate overlap area
            x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            y_overlap = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
            overlap_area = x_overlap * y_overlap
            
            # Calculate total area
            total_area = (w1 * h1 + w2 * h2) / 2  # Average area
            
            if total_area == 0:
                return 0.0
                
            return overlap_area / total_area
        except (TypeError, ValueError):
            return 0.0

    def _identify_element_purpose(self, element: UIElement) -> Tuple[str, str]:
        """Identify the functional purpose and interaction type of an element."""
        text = (element.visible_text or '').lower()
        selector = element.selector.lower()
        element_type = element.element_type.lower()
        
        # Extract all text content including attributes
        all_text = ' '.join([
            text,
            selector,
            str(element.attributes),
            element_type
        ]).lower()

        # Check against functional patterns
        for pattern_type, pattern in self.functional_patterns.items():
            # Check keywords
            if any(keyword in all_text for keyword in pattern['keywords']):
                # Check if it's part of a common parent structure
                if any(parent in selector for parent in pattern['common_parents']):
                    if element_type in pattern['typical_elements']:
                        return pattern_type, self._determine_interaction_type(element, all_text)

        return 'generic', 'click'

    def _determine_interaction_type(self, element: UIElement, all_text: str) -> str:
        """Determine how this element should be interacted with."""
        element_type = element.element_type.lower()
        
        if element_type in {'input', 'textarea', 'select'}:
            return 'input'
        if 'submit' in all_text or element_type == 'button':
            return 'click'
        if element_type == 'a':
            return 'navigate'
        return 'click'

    def _group_elements_by_function(self, elements: List[UIElement]) -> List[FunctionalGroup]:
        """Group elements by their functional purpose."""
        groups: Dict[str, List[UIElement]] = defaultdict(list)
        
        for element in elements:
            purpose, interaction = self._identify_element_purpose(element)
            key = f"{purpose}_{interaction}"
            
            # Find similar existing group or create new one
            found_group = False
            for group_key, group_elements in groups.items():
                if group_elements and self._are_functionally_similar(element, group_elements[0]):
                    groups[group_key].append(element)
                    found_group = True
                    break
            
            if not found_group:
                groups[f"{key}_{len(groups)}"].append(element)

        # Convert groups to FunctionalGroup objects
        return [
            FunctionalGroup(
                primary_element=group[0],
                similar_elements=group[1:],
                purpose=key.split('_')[0],
                interaction_type=key.split('_')[1]
            )
            for key, group in groups.items()
        ]

    def _are_functionally_similar(self, elem1: UIElement, elem2: UIElement) -> bool:
        """Determine if two elements serve the same functional purpose."""
        # Get base similarity score
        similarity = self._calculate_element_similarity(elem1, elem2)
        
        # If elements are very similar structurally, they're likely functional duplicates
        if similarity >= self.similarity_threshold:
            return True
            
        # Check if they're part of the same functional group
        purpose1, interaction1 = self._identify_element_purpose(elem1)
        purpose2, interaction2 = self._identify_element_purpose(elem2)
        
        if purpose1 == purpose2 and interaction1 == interaction2:
            # Check if they're close to each other in the DOM
            if self._are_dom_siblings(elem1, elem2):
                return True
                
            # Check if they share common parent patterns
            if self._share_common_parent_pattern(elem1, elem2):
                return True
        
        return False

    def _are_dom_siblings(self, elem1: UIElement, elem2: UIElement) -> bool:
        """Check if elements are siblings or closely related in the DOM."""
        selector_parts1 = elem1.selector.split('>')
        selector_parts2 = elem2.selector.split('>')
        
        # Check if they share the same parent
        if len(selector_parts1) > 1 and len(selector_parts2) > 1:
            parent1 = '>'.join(selector_parts1[:-1])
            parent2 = '>'.join(selector_parts2[:-1])
            return parent1 == parent2
        
        return False

    def _share_common_parent_pattern(self, elem1: UIElement, elem2: UIElement) -> bool:
        """Check if elements share common parent patterns (e.g., both in a nav section)."""
        for pattern in self.functional_patterns.values():
            for parent in pattern['common_parents']:
                if parent in elem1.selector.lower() and parent in elem2.selector.lower():
                    return True
        return False

    def filter_elements(self, elements: List[UIElement]) -> List[UIElement]:
        """Filter out elements that would generate redundant test cases."""
        # Group elements by function
        functional_groups = self._group_elements_by_function(elements)
        
        # Select representative elements from each group
        unique_elements = []
        for group in functional_groups:
            # Always include the primary element
            unique_elements.append(group.primary_element)
            
            # Log the grouping decision
            logger.info(f"Created functional group for {group.purpose} with "
                       f"{len(group.similar_elements) + 1} elements. "
                       f"Using {group.primary_element.element_id} as primary element.")
            
            for element in group.similar_elements:
                logger.info(f"Skipping element {element.element_id} as it's functionally "
                          f"similar to {group.primary_element.element_id} "
                          f"(purpose: {group.purpose}, interaction: {group.interaction_type})")
        
        logger.info(f"Filtered {len(elements) - len(unique_elements)} redundant elements "
                   f"out of {len(elements)} total elements")
        return unique_elements 