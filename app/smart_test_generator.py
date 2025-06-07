from typing import Dict, List, Any, Optional, Tuple
from playwright.async_api import Page
from .models import ElementMapEntry, TestCase, TestStep
import logging
import re
import hashlib
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FunctionalPattern:
    """Identifies functional patterns in UI elements."""
    
    def __init__(self):
        self.patterns = {
            'navigation': {
                'indicators': ['next', 'previous', 'prev', 'forward', 'back', 'arrow'],
                'common_parents': ['slider', 'carousel', 'pagination', 'nav', 'navigation'],
                'typical_structure': ['button', 'a', 'span'],
                'test_template': {
                    'type': 'navigation',
                    'priority': 'medium',
                    'preconditions': [
                        'User is on the page with navigation controls',
                        'Content is available for navigation'
                    ]
                }
            },
            'form_input': {
                'indicators': ['submit', 'input', 'text', 'email', 'password', 'search'],
                'common_parents': ['form', 'fieldset', 'input-group'],
                'typical_structure': ['input', 'textarea', 'select', 'button'],
                'test_template': {
                    'type': 'form_interaction',
                    'priority': 'high',
                    'preconditions': [
                        'User is on the page with the form',
                        'Form is accessible and enabled'
                    ]
                }
            },
            'action_button': {
                'indicators': ['click', 'submit', 'send', 'save', 'delete', 'update'],
                'common_parents': ['button-group', 'actions', 'controls'],
                'typical_structure': ['button', 'a', 'input[type="button"]'],
                'test_template': {
                    'type': 'action',
                    'priority': 'high',
                    'preconditions': [
                        'User is on the page with the action button',
                        'Action is available and enabled'
                    ]
                }
            }
        }

    def identify_pattern(self, element: ElementMapEntry) -> Tuple[str, float]:
        """Identify the functional pattern of an element based on its characteristics."""
        pattern_scores = {}
        
        for pattern_name, pattern_rules in self.patterns.items():
            score = self._calculate_pattern_score(element, pattern_rules)
            if score > 0:
                pattern_scores[pattern_name] = score
        
        if not pattern_scores:
            return ('unknown', 0.0)
            
        best_pattern = max(pattern_scores.items(), key=lambda x: x[1])
        return best_pattern

    def _calculate_pattern_score(self, element: ElementMapEntry, rules: Dict) -> float:
        score = 0.0
        
        # Check text content against indicators
        if element.visible_text:
            text = element.visible_text.lower()
            for indicator in rules['indicators']:
                if indicator in text:
                    score += 0.4
                    break
        
        # Check attributes for indicators
        for attr_value in element.attributes.values():
            if isinstance(attr_value, str):
                for indicator in rules['indicators']:
                    if indicator in attr_value.lower():
                        score += 0.3
                        break
        
        # Check parent elements
        for parent in rules['common_parents']:
            if parent in element.selector.lower():
                score += 0.3
                break
        
        # Check element structure
        if element.element_type in rules['typical_structure']:
            score += 0.3
        
        # Check ARIA roles
        if element.accessibility.get('role'):
            role = element.accessibility['role'].lower()
            if role in rules['indicators'] or role in rules['typical_structure']:
                score += 0.2
        
        return min(score, 1.0)  # Cap score at 1.0

class BehaviorAnalyzer:
    """Analyzes the runtime behavior of UI elements."""
    
    def __init__(self):
        self.behavior_cache = {}

    async def analyze_element_behavior(self, element: ElementMapEntry, page: Page) -> Dict[str, Any]:
        """Analyze the runtime behavior of an element."""
        cache_key = self._generate_cache_key(element)
        
        if cache_key in self.behavior_cache:
            return self.behavior_cache[cache_key]
        
        behavior_signature = {
            'event_handlers': await self._get_event_handlers(element, page),
            'interaction_type': element.interaction_type,
            'state_dependencies': await self._analyze_state_dependencies(element, page),
            'position_context': self._analyze_position_context(element)
        }
        
        self.behavior_cache[cache_key] = behavior_signature
        return behavior_signature

    def _generate_cache_key(self, element: ElementMapEntry) -> str:
        """Generate a unique cache key for an element."""
        key_parts = [
            element.element_type,
            element.selector,
            element.interaction_type,
            str(element.attributes),
            str(element.position)
        ]
        return hashlib.md5(json.dumps(key_parts).encode()).hexdigest()

    async def _get_event_handlers(self, element: ElementMapEntry, page: Page) -> List[str]:
        """Get all event handlers attached to the element."""
        try:
            handlers = await page.evaluate("""(selector) => {
                const element = document.querySelector(selector);
                if (!element) return [];
                
                const handlers = [];
                const events = ['click', 'submit', 'input', 'change', 'keyup', 'keydown'];
                
                for (const event of events) {
                    const eventHandlers = element[`on${event}`];
                    if (eventHandlers) {
                        handlers.push(event);
                    }
                }
                
                return handlers;
            }""", element.selector)
            
            return handlers
        except Exception as e:
            logger.warning(f"Error getting event handlers: {str(e)}")
            return []

    async def _analyze_state_dependencies(self, element: ElementMapEntry, page: Page) -> Dict[str, Any]:
        """Analyze element's state dependencies."""
        dependencies = {
            'requires_input': False,
            'affects_other_elements': False,
            'is_form_control': False
        }
        
        try:
            results = await page.evaluate("""(selector) => {
                const element = document.querySelector(selector);
                if (!element) return {};
                
                return {
                    requires_input: element.tagName === 'INPUT' || 
                                  element.tagName === 'SELECT' || 
                                  element.tagName === 'TEXTAREA',
                    affects_other_elements: !!element.getAttribute('aria-controls') ||
                                         !!element.getAttribute('data-target'),
                    is_form_control: element.form !== null
                };
            }""", element.selector)
            
            dependencies.update(results)
        except Exception as e:
            logger.warning(f"Error analyzing state dependencies: {str(e)}")
        
        return dependencies

    def _analyze_position_context(self, element: ElementMapEntry) -> Dict[str, Any]:
        """Analyze element's position context."""
        if not element.position:
            return {}
            
        return {
            'viewport_position': {
                'x': element.position.get('x', 0),
                'y': element.position.get('y', 0)
            },
            'dimensions': {
                'width': element.position.get('width', 0),
                'height': element.position.get('height', 0)
            }
        }

class SmartTestGenerator:
    """Generates intelligent test cases based on element patterns and behaviors."""
    
    def __init__(self):
        self.pattern_recognizer = FunctionalPattern()
        self.behavior_analyzer = BehaviorAnalyzer()
        self.test_case_cache = {}

    async def generate_test_case(self, element: ElementMapEntry, page: Page) -> Optional[TestCase]:
        """Generate a smart test case for an element."""
        # Identify pattern and behavior
        pattern_name, pattern_score = self.pattern_recognizer.identify_pattern(element)
        behavior = await self.behavior_analyzer.analyze_element_behavior(element, page)
        
        # Generate signature
        signature = self._create_element_signature(pattern_name, behavior)
        
        # Check cache for existing test case
        if signature in self.test_case_cache:
            return self._adapt_existing_test_case(self.test_case_cache[signature], element)
        
        # Generate new test case
        test_case = await self._generate_new_test_case(element, pattern_name, behavior, pattern_score)
        if test_case:
            self.test_case_cache[signature] = test_case
        
        return test_case

    def _create_element_signature(self, pattern: str, behavior: Dict) -> str:
        """Create a unique signature for functionally equivalent elements."""
        signature_parts = [
            pattern,
            str(sorted(behavior['event_handlers'])),
            str(sorted(behavior['state_dependencies'].items())),
            behavior['interaction_type']
        ]
        return hashlib.md5(json.dumps(signature_parts).encode()).hexdigest()

    async def _generate_new_test_case(
        self, 
        element: ElementMapEntry, 
        pattern: str, 
        behavior: Dict,
        pattern_score: float
    ) -> Optional[TestCase]:
        """Generate a new test case based on element characteristics."""
        if pattern == 'unknown' or pattern_score < 0.3:
            return None
            
        pattern_template = self.pattern_recognizer.patterns[pattern]['test_template']
        
        # Generate a unique test case ID
        test_id = f"TC_{pattern.upper()}_{self._generate_id()}"
        
        # Create test steps based on behavior
        steps = self._generate_test_steps(element, pattern, behavior)
        
        # Determine test priority
        priority = self._determine_priority(pattern_template['priority'], behavior)
        
        return TestCase(
            test_case_id=test_id,
            test_case_title=self._generate_title(element, pattern),
            type=pattern_template['type'],
            priority=priority,
            description=self._generate_description(element, pattern, behavior),
            preconditions=self._adapt_preconditions(pattern_template['preconditions'], element, behavior),
            steps=steps,
            related_element_id=element.element_id
        )

    def _generate_id(self) -> str:
        """Generate a unique test case identifier."""
        import uuid
        return str(uuid.uuid4())[:8].upper()

    def _generate_title(self, element: ElementMapEntry, pattern: str) -> str:
        """Generate a descriptive test case title."""
        action_word = {
            'navigation': 'Navigate',
            'form_input': 'Input',
            'action_button': 'Perform'
        }.get(pattern, 'Interact with')
        
        element_name = element.visible_text or element.attributes.get('name', '') or element.element_type
        return f"{action_word} using {element_name}"

    def _generate_description(self, element: ElementMapEntry, pattern: str, behavior: Dict) -> str:
        """Generate a detailed test case description."""
        description_parts = [
            f"Verify the functionality of the {element.element_type} element",
            f"Type: {pattern}",
            f"Interaction: {behavior['interaction_type']}"
        ]
        
        if behavior['state_dependencies']['affects_other_elements']:
            description_parts.append("This element affects other elements on the page")
            
        return " | ".join(description_parts)

    def _adapt_preconditions(
        self, 
        base_preconditions: List[str], 
        element: ElementMapEntry,
        behavior: Dict
    ) -> List[str]:
        """Adapt base preconditions for specific element."""
        preconditions = base_preconditions.copy()
        
        if behavior['state_dependencies']['requires_input']:
            preconditions.append("Required input data is available")
            
        if behavior['state_dependencies']['is_form_control']:
            preconditions.append("Form is in a valid state")
            
        return preconditions

    def _generate_test_steps(
        self, 
        element: ElementMapEntry, 
        pattern: str,
        behavior: Dict
    ) -> List[TestStep]:
        """Generate appropriate test steps based on element type and behavior."""
        steps = []
        step_number = 1
        
        # Add verification step
        steps.append(
            TestStep(
                step_number=step_number,
                action=f"Verify {element.element_type} is present and visible",
                expected_result=f"Element is visible and enabled"
            )
        )
        step_number += 1
        
        # Add interaction steps based on pattern and behavior
        if pattern == 'navigation':
            steps.extend(self._generate_navigation_steps(element, step_number))
        elif pattern == 'form_input':
            steps.extend(self._generate_form_steps(element, behavior, step_number))
        elif pattern == 'action_button':
            steps.extend(self._generate_action_steps(element, behavior, step_number))
        
        return steps

    def _generate_navigation_steps(self, element: ElementMapEntry, start_step: int) -> List[TestStep]:
        """Generate steps for navigation elements."""
        return [
            TestStep(
                step_number=start_step,
                action=f"Click the {element.visible_text or 'navigation'} element",
                expected_result="Navigation occurs successfully"
            ),
            TestStep(
                step_number=start_step + 1,
                action="Verify the new state after navigation",
                expected_result="New content is loaded and visible"
            )
        ]

    def _generate_form_steps(self, element: ElementMapEntry, behavior: Dict, start_step: int) -> List[TestStep]:
        """Generate steps for form input elements."""
        steps = [
            TestStep(
                step_number=start_step,
                action=f"Enter valid data into the {element.element_type}",
                expected_result="Data is entered successfully"
            )
        ]
        
        if behavior['state_dependencies']['is_form_control']:
            steps.append(
                TestStep(
                    step_number=start_step + 1,
                    action="Submit the form",
                    expected_result="Form submits successfully"
                )
            )
        
        return steps

    def _generate_action_steps(self, element: ElementMapEntry, behavior: Dict, start_step: int) -> List[TestStep]:
        """Generate steps for action button elements."""
        steps = [
            TestStep(
                step_number=start_step,
                action=f"Click the {element.visible_text or 'action'} button",
                expected_result="Action is triggered"
            )
        ]
        
        if behavior['state_dependencies']['affects_other_elements']:
            steps.append(
                TestStep(
                    step_number=start_step + 1,
                    action="Verify affected elements",
                    expected_result="Related elements update appropriately"
                )
            )
        
        return steps

    def _determine_priority(self, base_priority: str, behavior: Dict) -> str:
        """Determine test case priority based on behavior."""
        if behavior['state_dependencies']['affects_other_elements']:
            return 'high'
        if behavior['state_dependencies']['is_form_control']:
            return 'high'
        return base_priority

    def _adapt_existing_test_case(self, base_case: TestCase, new_element: ElementMapEntry) -> TestCase:
        """Adapt an existing test case for a new but similar element."""
        adapted_case = base_case.copy()
        adapted_case.test_case_id = f"{base_case.test_case_id}_{self._generate_id()}"
        adapted_case.related_element_id = new_element.element_id
        
        # Adapt title and description if needed
        if new_element.visible_text:
            adapted_case.test_case_title = adapted_case.test_case_title.replace(
                base_case.related_element_id,
                new_element.visible_text
            )
            
        return adapted_case 