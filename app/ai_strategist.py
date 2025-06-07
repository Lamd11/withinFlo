import os
from openai import OpenAI 
from typing import List, Dict, Any, Optional
import logging
import json
from dotenv import load_dotenv
from .models import ScanStrategy, PageElementMap
from pydantic import ValidationError


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
        self.test_case_cache = {}  # Cache for storing and comparing test cases

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
            context_parts.append("\nDetailed Element Map:")
            for element in element_map.elements:
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
        
        You have been provided with a detailed map of all interactive elements on the page.
        Use this information to create a precise strategy that targets the exact elements needed.
        
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
              "selector": "exact_selector_from_element_map"  # Use this when possible
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
        """
        
        return [
            {"role": "system", "content": system_message_content.strip()},
            {"role": "user", "content": user_message_content.strip()}
        ]

    def _calculate_test_case_similarity(self, test1: Dict[str, Any], test2: Dict[str, Any]) -> float:
        """Calculate similarity score between two test cases."""
        score = 0.0
        
        # Compare test titles (high weight)
        if test1['test_case_title'].lower() == test2['test_case_title'].lower():
            score += 0.3
        
        # Compare steps (highest weight)
        steps1 = [s['action'].lower() for s in test1['steps']]
        steps2 = [s['action'].lower() for s in test2['steps']]
        
        # Calculate step similarity using sequence matching
        from difflib import SequenceMatcher
        steps_similarity = SequenceMatcher(None, str(steps1), str(steps2)).ratio()
        score += 0.4 * steps_similarity
        
        # Compare expected results
        results1 = [s['expected_result'].lower() for s in test1['steps']]
        results2 = [s['expected_result'].lower() for s in test2['steps']]
        results_similarity = SequenceMatcher(None, str(results1), str(results2)).ratio()
        score += 0.2 * results_similarity
        
        # Compare preconditions
        precond_similarity = SequenceMatcher(None, 
                                           str(test1['preconditions']), 
                                           str(test2['preconditions'])).ratio()
        score += 0.1 * precond_similarity
        
        return score

    def _should_merge_test_cases(self, test1: Dict[str, Any], test2: Dict[str, Any]) -> bool:
        """Determine if two test cases should be merged."""
        similarity_score = self._calculate_test_case_similarity(test1, test2)
        return similarity_score > 0.8  # High threshold for merging

    def _merge_test_cases(self, test1: Dict[str, Any], test2: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two similar test cases into one optimized test case."""
        # Start with the test case that has more steps
        base_test = test1 if len(test1['steps']) >= len(test2['steps']) else test2
        other_test = test2 if len(test1['steps']) >= len(test2['steps']) else test1
        
        merged_test = base_test.copy()
        
        # Merge preconditions
        merged_preconditions = list(set(base_test['preconditions'] + other_test['preconditions']))
        merged_test['preconditions'] = merged_preconditions
        
        # Merge descriptions
        if len(other_test['description']) > len(base_test['description']):
            merged_test['description'] = other_test['description']
        
        # Take the higher priority
        if other_test['priority'] == 'high' and base_test['priority'] != 'high':
            merged_test['priority'] = 'high'
        
        # Combine feature tested if different
        if other_test.get('feature_tested') and other_test['feature_tested'] != base_test.get('feature_tested'):
            merged_test['feature_tested'] = f"{base_test.get('feature_tested', '')} and {other_test['feature_tested']}"
        
        return merged_test

    def _optimize_test_cases(self, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize test cases by merging similar ones and removing duplicates."""
        if not test_cases:
            return []
            
        optimized_cases = []
        merged_indices = set()
        
        for i, test1 in enumerate(test_cases):
            if i in merged_indices:
                continue
                
            merged_test = test1.copy()
            merged_indices.add(i)
            
            # Look for similar test cases to merge
            for j, test2 in enumerate(test_cases[i + 1:], start=i + 1):
                if j in merged_indices:
                    continue
                    
                if self._should_merge_test_cases(merged_test, test2):
                    merged_test = self._merge_test_cases(merged_test, test2)
                    merged_indices.add(j)
            
            optimized_cases.append(merged_test)
        
        return optimized_cases

    def _cache_test_case(self, test_case: Dict[str, Any], element_id: str):
        """Cache a test case for future comparison."""
        if element_id not in self.test_case_cache:
            self.test_case_cache[element_id] = []
        self.test_case_cache[element_id].append(test_case)

    def _get_similar_cached_tests(self, test_case: Dict[str, Any], element_id: str) -> List[Dict[str, Any]]:
        """Get similar test cases from cache."""
        similar_tests = []
        if element_id in self.test_case_cache:
            for cached_test in self.test_case_cache[element_id]:
                if self._should_merge_test_cases(test_case, cached_test):
                    similar_tests.append(cached_test)
        return similar_tests

    def develop_scan_strategy(self, user_prompt: str, url: str, website_content: Optional[Dict[str, Any]] = None, element_map: Optional[PageElementMap] = None, existing_website_context: Optional[Dict[str, Any]] = None) -> Optional[ScanStrategy]:
        """
        Main public method of this class. It takes the user's request and other relevant info and returns the structured scan strategy.
        """
        # Reset test case cache for new scan
        self.test_case_cache = {}
        
        llm_res = self.prompt_formulation(user_prompt, url, website_content, element_map, existing_website_context)
        parsed_strategy = self.parse_llm_response_to_strategy(llm_res)
        
        if parsed_strategy and element_map:
            # Optimize test cases based on element relationships
            for element in element_map.elements:
                if element.relations.parent_id:
                    # Get test cases for both parent and child
                    parent_tests = self.test_case_cache.get(element.relations.parent_id, [])
                    child_tests = self.test_case_cache.get(element.element_id, [])
                    
                    # If both have test cases, try to optimize
                    if parent_tests and child_tests:
                        optimized_tests = self._optimize_test_cases(parent_tests + child_tests)
                        # Update cache with optimized tests
                        self.test_case_cache[element.relations.parent_id] = optimized_tests
                        self.test_case_cache[element.element_id] = optimized_tests
        
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
    

