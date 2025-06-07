import os
from openai import OpenAI 
from typing import List, Dict, Any, Optional, Set
import logging
import json
from dotenv import load_dotenv
from .models import ScanStrategy, PageElementMap, TestCase, ElementMapEntry
from pydantic import ValidationError
import itertools
from collections import defaultdict


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIStrategist:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OPEN_API_KEY environmental variable is not set")
            raise ValueError("OPEN_API_KEY environmental variable is not set")
        self.client = OpenAI(api_key=self.api_key)
        self.test_case_cache = {}  # Cache to store generated test cases
        
    def _calculate_test_similarity(self, test1: TestCase, test2: TestCase) -> float:
        """Calculate similarity score between two test cases."""
        similarity = 0.0
        
        # Compare titles (30% weight)
        from difflib import SequenceMatcher
        title_similarity = SequenceMatcher(None, test1.test_case_title, test2.test_case_title).ratio()
        similarity += 0.3 * title_similarity
        
        # Compare steps (50% weight)
        steps_similarity = 0.0
        if test1.steps and test2.steps:
            total_comparisons = 0
            for step1, step2 in itertools.zip_longest(test1.steps, test2.steps):
                if step1 and step2:
                    action_similarity = SequenceMatcher(None, step1.action, step2.action).ratio()
                    result_similarity = SequenceMatcher(None, step1.expected_result, step2.expected_result).ratio()
                    steps_similarity += (action_similarity + result_similarity) / 2
                    total_comparisons += 1
            if total_comparisons > 0:
                steps_similarity /= total_comparisons
        similarity += 0.5 * steps_similarity
        
        # Compare related elements (20% weight)
        element_similarity = 1.0 if test1.related_element_id == test2.related_element_id else 0.0
        similarity += 0.2 * element_similarity
        
        return similarity

    def _deduplicate_test_cases(self, test_cases: List[TestCase], similarity_threshold: float = 0.85) -> List[TestCase]:
        """Remove duplicate or highly similar test cases."""
        unique_tests = []
        groups = defaultdict(list)  # Group similar test cases
        
        # First pass: Group by feature tested
        for test in test_cases:
            feature_key = test.feature_tested or 'unknown'
            groups[feature_key].append(test)
            
        # Second pass: Within each feature group, find unique test cases
        for feature_group in groups.values():
            processed = set()
            for i, test1 in enumerate(feature_group):
                if i in processed:
                    continue
                    
                similar_tests = [test1]
                for j, test2 in enumerate(feature_group[i+1:], i+1):
                    if j not in processed:
                        similarity = self._calculate_test_similarity(test1, test2)
                        if similarity >= similarity_threshold:
                            similar_tests.append(test2)
                            processed.add(j)
                            
                # Select the most comprehensive test case from the similar group
                if similar_tests:
                    best_test = max(similar_tests, key=lambda t: len(t.steps))
                    unique_tests.append(best_test)
                processed.add(i)
                
        return unique_tests

    def _optimize_test_cases(self, test_cases: List[TestCase], element_map: PageElementMap) -> List[TestCase]:
        """Optimize test cases by removing redundancy and improving coverage."""
        # Step 1: Group test cases by feature and functionality
        feature_groups = defaultdict(list)
        for test in test_cases:
            feature_key = test.feature_tested or 'unknown'
            feature_groups[feature_key].append(test)
            
        optimized_tests = []
        
        for feature, tests in feature_groups.items():
            # Step 2: Remove duplicate test cases
            unique_tests = self._deduplicate_test_cases(tests)
            
            # Step 3: Sort by priority and complexity
            unique_tests.sort(key=lambda t: (
                t.priority,
                -len(t.steps),  # More complex tests first within same priority
                t.test_case_title
            ))
            
            optimized_tests.extend(unique_tests)
            
        return optimized_tests

    def create_llm_messages(self, user_prompt: str, url: str, website_content: Dict[str, Any] = None, element_map: Optional[PageElementMap] = None, existing_website_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """
        Helper method to create system and user messages to insert into OpenAI's model. To formulate the scan strategy
        """ 
        context_parts = []
        
        if website_content:
            context_parts.append(f"Page Title: {website_content.get('page_title', 'N/A')}")
            
            if website_content.get('structure'):
                headings = website_content['structure'].get('headings', [])
                if headings:
                    context_parts.append("\nPage Headings:")
                    for h in headings:
                        context_parts.append(f"- {h['level']}: {h['text']}")
                
                sections = website_content['structure'].get('mainSections', [])
                if sections:
                    context_parts.append("\nMain Page Sections:")
                    for section in sections:
                        section_desc = f"- {section['type']}"
                        if section['id']:
                            section_desc += f" (id: {section['id']})"
                        if section['class']:
                            section_desc += f" (class: {section['class']})"
                        context_parts.append(section_desc)
            
            if website_content.get('text_content'):
                # Truncate text content if it's too long
                text_content = website_content['text_content'][:1000] + "..." if len(website_content['text_content']) > 1000 else website_content['text_content']
                context_parts.append(f"\nPage Content Preview:\n{text_content}")

        if element_map:
            # Group elements by their component contexts
            component_groups = {}
            ungrouped_elements = []
            
            for element in element_map.elements:
                contexts = element.attributes.get('component_contexts', {})
                if contexts:
                    for context_type, context_info in contexts.items():
                        if context_type not in component_groups:
                            component_groups[context_type] = []
                        component_groups[context_type].append((element, context_info))
                else:
                    ungrouped_elements.append(element)
            
            # Add component-grouped elements to context
            if component_groups:
                context_parts.append("\nComponent-Grouped Elements:")
                for component_type, elements in component_groups.items():
                    context_parts.append(f"\n{component_type.title()} Component Elements:")
                    for element, context_info in elements:
                        element_desc = [
                            f"\nElement: {element.element_type} ({element.interaction_type})",
                            f"Selector: {element.selector}",
                            f"Text: {element.visible_text if element.visible_text else 'N/A'}",
                            f"State: {element.state}",
                            f"Context Info: {json.dumps(context_info)}"
                        ]
                        if element.accessibility:
                            element_desc.append(f"Accessibility: {json.dumps(element.accessibility)}")
                        context_parts.extend(element_desc)
            
            # Add ungrouped elements
            if ungrouped_elements:
                context_parts.append("\nStandalone Interactive Elements:")
                for element in ungrouped_elements:
                    element_desc = [
                        f"\nElement: {element.element_type} ({element.interaction_type})",
                        f"Selector: {element.selector}",
                        f"Text: {element.visible_text if element.visible_text else 'N/A'}",
                        f"State: {element.state}",
                    ]
                    if element.accessibility:
                        element_desc.append(f"Accessibility: {json.dumps(element.accessibility)}")
                    context_parts.extend(element_desc)
        
        if existing_website_context:
            context_str = json.dumps(existing_website_context)
            context_parts.append(f"\nAdditional Context:\n{context_str}")
        
        website_context = "\n".join(context_parts)
        
        system_message_content = f"""
        You are an expert QA Analyst and Web Interaction Strategist.
        Your task is to analyze the user's request, the target URL, and the provided page content, element map, and context.
        Based on this, formulate a focused 'scan strategy' for a web crawler that specifically addresses the user's needs.
        
        You have been provided with a detailed map of all interactive elements on the page, grouped by their component contexts.
        Use this information to create a precise strategy that targets the exact elements needed.
        
        When dealing with component-specific requests:
        1. Identify the relevant component type from the user's request
        2. Focus primarily on elements within that component's context
        3. Consider the component's structure and hierarchy
        4. Include related elements that are functionally part of the component
        5. Consider the relationships between different components if relevant
        
        The strategy should specify which elements or types of elements the crawler should focus on to fulfill the user's request.
        DO NOT generate test cases or documentation - focus only on identifying the relevant elements to scan.

        You must respond with ONLY a valid JSON object, with no additional text or explanation.
        The JSON must be structured exactly as follows:
        {{
          "focus_areas": ["area1", "area2"],
          "target_elements_description": [
            {{
              "type": "element_tag",
              "attributes": {{"attr_name": "value"}},
              "text_contains": "some text",
              "purpose": "brief description of element's role in the user's goal",
              "selector": "exact_selector_from_element_map",  # Use this when possible
              "component_context": "component_type"  # Include when relevant
            }}
          ]
        }}
        
        The target_elements_description should be SPECIFIC to what the user wants to test or analyze.
        Each element description should clearly explain how it relates to the user's specific request.
        When possible, use the exact selectors from the element map to ensure precise targeting.
        Remember: Return ONLY the JSON object with no additional text.
        """

        user_message_content = f"""
        User Request: "{user_prompt}"
        Target URL: "{url}"
        
        Website Information:
        {website_context}

        Please generate a focused scan strategy JSON that will help find ONLY the elements needed for the user's specific request.
        Prefer using exact selectors from the element map when they match the needed elements.
        Consider the component context of elements when relevant to the request.
        """
        
        return [
            {"role": "system", "content": system_message_content.strip()},
            {"role": "user", "content": user_message_content.strip()}
        ]

    def develop_scan_strategy(self, user_prompt: str, url: str, website_content: Optional[Dict[str, Any]] = None, element_map: Optional[PageElementMap] = None, existing_website_context: Optional[Dict[str, Any]] = None) -> Optional[ScanStrategy]:
        """
        Main public method of this class. It takes the user's request and other relevant info and returns the structured scan strategy.
        """
        llm_res = self.prompt_formulation(user_prompt, url, website_content, element_map, existing_website_context)
        parsed_strategy = self.parse_llm_response_to_strategy(llm_res)
        
        if parsed_strategy and element_map:
            # Cache the strategy and element map for later test case optimization
            strategy_key = f"{url}_{hash(user_prompt)}"
            self.test_case_cache[strategy_key] = {
                'strategy': parsed_strategy,
                'element_map': element_map
            }
            
        return parsed_strategy

    def prompt_formulation(self, user_prompt: str, url: str, website_content: Optional[Dict[str, Any]] = None, element_map: Optional[PageElementMap] = None, existing_website_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Calls the LLM with the constructed prompt and returns the strategy content string.
        """
        messages = self.create_llm_messages(user_prompt, url, website_content, element_map, existing_website_context)
        try:
            logger.info("Attempting to generate scan strategy from user prompt and website content")
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.5,
                max_tokens=2000
            )
            logger.info("Successfully generated scan strategy")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error analyzing prompt: {e}")
            raise

    def parse_llm_response_to_strategy(self, llm_response_content: str) -> Optional[ScanStrategy]:
        """
        Converting JSON response into Pydantic model
        """
        logger.info("Attempting to convert JSON into ScanStrategy Model")
        try:
            strategy_dict = json.loads(llm_response_content)
            strategy_model = ScanStrategy(**strategy_dict)
            logger.info("Successfully parsed LLM response into ScanStrategy model.")
            return strategy_model
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode LLM response as JSON: {e}")
            logger.error(f"LLM Response was: {llm_response_content}")
            return None # Or raise a custom error
        except ValidationError as e: # Pydantic's validation error
            logger.error(f"LLM JSON does not match ScanStrategy model: {e}")
            logger.error(f"LLM Response (parsed dict attempt) was: {strategy_dict if 'strategy_dict' in locals() else 'JSON parsing failed earlier'}")
            return None # Or raise a custom error
        except Exception as e:
            logger.error(f"An unexpected error occurred during parsing: {e}", exc_info=True)
            return None

    def optimize_test_cases(self, test_cases: List[TestCase], url: str, user_prompt: str) -> List[TestCase]:
        """
        Public method to optimize a set of test cases using cached information.
        """
        strategy_key = f"{url}_{hash(user_prompt)}"
        cached_data = self.test_case_cache.get(strategy_key)
        
        if cached_data and cached_data['element_map']:
            return self._optimize_test_cases(test_cases, cached_data['element_map'])
        
        # If no cache is available, just deduplicate
        return self._deduplicate_test_cases(test_cases)


if __name__ == "__main__":
    """Test function to demonstrate the AIStrategist functionality"""
    import json
    from dotenv import load_dotenv
    
    load_dotenv()  # Make sure environment variables are loaded
    
    # Initialize the strategist
    strategist = AIStrategist()
    
    # Sample test parameters
    user_prompt = "Test to see if the email form submission works on the website"
    url = "https://portfolio-website-kappa-hazel-20.vercel.app/"
    
    # Get the scan strategy
    print("Generating scan strategy...")
    strategy = strategist.develop_scan_strategy(user_prompt, url)
    
    # Print the result in a formatted way
    print("\n===== SCAN STRATEGY RESULT =====")
    print(f"Focus Areas: {strategy.focus_areas}")
    print("\nTarget Elements:")
    for i, element in enumerate(strategy.target_elements_description, 1):
        print(f"\n--- Element {i} ---")
        for key, value in element.items():
            print(f"{key}: {value}")
    
    print("\n===== RAW JSON OUTPUT =====")
    print(json.dumps(strategy.model_dump(), indent=2))
    

