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

    def develop_scan_strategy(self, user_prompt: str, url: str, website_content: Optional[Dict[str, Any]] = None, element_map: Optional[PageElementMap] = None, existing_website_context: Optional[Dict[str, Any]] = None) -> Optional[ScanStrategy]:
        """
        Main public method of this class. It takes the user's request and other relevant info and returns the structured scan strategy.
        """
        llm_res = self.prompt_formulation(user_prompt, url, website_content, element_map, existing_website_context)
        parsed_strategy = self.parse_llm_response_to_strategy(llm_res)
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
    

