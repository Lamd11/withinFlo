import os
from openai import OpenAI 
from typing import List, Dict, Any, Optional
import logging
import json
from dotenv import load_dotenv
from .models import ScanStrategy
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

    def create_llm_messages(self, user_prompt: str, url: str, page_map: Dict[str, Any], existing_website_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """
        Enhanced version that uses the comprehensive page map to create more informed messages for the LLM
        """
        # Create a detailed context from the page map
        context_parts = []
        
        # Add page metadata
        context_parts.append(f"Page Title: {page_map['page_metadata']['title']}")
        context_parts.append(f"Page URL: {page_map['page_metadata']['url']}")
        
        # Add interactive elements summary
        if page_map.get('interactive_elements'):
            context_parts.append("\nInteractive Elements:")
            for element in page_map['interactive_elements']:
                element_desc = f"- {element['tagName']}"
                if element.get('id'):
                    element_desc += f" (id: {element['id']})"
                if element.get('textContent'):
                    element_desc += f" with text: '{element['textContent']}'"
                context_parts.append(element_desc)
        
        # Add form elements summary
        if page_map.get('form_elements'):
            context_parts.append("\nForms:")
            for form in page_map['form_elements']:
                form_desc = f"- Form"
                if form.get('id'):
                    form_desc += f" (id: {form['id']})"
                if form.get('action'):
                    form_desc += f" action: {form['action']}"
                context_parts.append(form_desc)
                if form.get('fields'):
                    for field in form['fields']:
                        field_desc = f"  - {field['tagName']}"
                        if field.get('type'):
                            field_desc += f" type={field['type']}"
                        if field.get('name'):
                            field_desc += f" name={field['name']}"
                        context_parts.append(field_desc)
        
        # Add navigation elements
        if page_map.get('navigation_elements'):
            context_parts.append("\nNavigation Elements:")
            for nav in page_map['navigation_elements']:
                nav_desc = f"- {nav['tagName']}"
                if nav.get('textContent'):
                    nav_desc += f" with text: '{nav['textContent']}'"
                if nav.get('href'):
                    nav_desc += f" linking to: {nav['href']}"
                context_parts.append(nav_desc)
        
        # Add content structure
        if page_map.get('content_structure'):
            if page_map['content_structure'].get('headings'):
                context_parts.append("\nHeadings:")
                for heading in page_map['content_structure']['headings']:
                    context_parts.append(f"- h{heading['level']}: {heading['text']}")
            
            if page_map['content_structure'].get('sections'):
                context_parts.append("\nMain Sections:")
                for section in page_map['content_structure']['sections']:
                    section_desc = f"- {section['tagName']}"
                    if section.get('role'):
                        section_desc += f" (role: {section['role']})"
                    context_parts.append(section_desc)

        # Add existing context if provided
        if existing_website_context:
            context_parts.append("\nAdditional Context:")
            context_parts.append(json.dumps(existing_website_context, indent=2))

        website_context = "\n".join(context_parts)
        
        system_message_content = """
        You are an expert QA Analyst and Web Interaction Strategist.
        Your task is to analyze the provided comprehensive page map and user's request to create a precise scan strategy.
        You have been provided with ACTUAL page content and structure - use this to create accurate element selectors.
        
        Focus on creating a strategy that will reliably find the elements needed for the user's specific request.
        
        You must respond with ONLY a valid JSON object, with no additional text or explanation.
        The JSON must follow this structure:
        {
          "focus_areas": ["specific_area1", "specific_area2"],
          "target_elements_description": [
            {
              "type": "actual_element_tag",
              "attributes": {"attr_name": "actual_value"},
              "text_contains": "exact_text_if_present",
              "purpose": "specific_purpose_in_testing"
            }
          ],
          "scan_depth": number,
          "page_navigation_rules": [
            {
              "source_page": "url_or_pattern",
              "target_pattern": "url_pattern",
              "navigation_element": {
                "selector": "precise_selector",
                "text": "link_text_if_any"
              }
            }
          ]
        }
        
        Use ONLY element types and attributes that actually exist in the page map.
        Be as specific as possible with selectors to ensure reliable element identification.
        """

        user_message_content = f"""
        User Request: "{user_prompt}"
        Target URL: "{url}"
        
        Complete Page Information:
        {website_context}

        Generate a precise scan strategy JSON that will reliably find the specific elements needed for the user's request,
        using only elements and attributes that are actually present in the page map.
        """
        
        return [
            {"role": "system", "content": system_message_content.strip()},
            {"role": "user", "content": user_message_content.strip()}
        ]

    def develop_scan_strategy(self, user_prompt: str, url: str, page_map: Dict[str, Any], existing_website_context: Optional[Dict[str, Any]] = None) -> Optional[ScanStrategy]:
        """
        Enhanced version that uses the comprehensive page map to develop a more accurate scan strategy
        """
        if not user_prompt:
            logger.warning("No user prompt provided. Cannot generate meaningful scan strategy.")
            return None

        logger.info(f"Developing scan strategy for URL: {url}")
        logger.info(f"User prompt: {user_prompt}")
        logger.debug(f"Page map summary:")
        logger.debug(f"- Interactive elements: {len(page_map.get('interactive_elements', []))}")
        logger.debug(f"- Form elements: {len(page_map.get('form_elements', []))}")
        logger.debug(f"- Navigation elements: {len(page_map.get('navigation_elements', []))}")

        llm_res = self.prompt_formulation(user_prompt, url, page_map, existing_website_context)
        
        # Log the strategy before parsing
        logger.debug(f"Generated strategy (raw):\n{llm_res}")
        
        parsed_strategy = self.parse_llm_response_to_strategy(llm_res)
        
        if parsed_strategy:
            logger.info(f"Successfully generated strategy with {len(parsed_strategy.target_elements_description)} target elements")
            logger.debug(f"Strategy details: {json.dumps(parsed_strategy.dict(), indent=2)}")
        else:
            logger.error("Failed to generate valid strategy")
            
        return parsed_strategy
    
    def prompt_formulation(self, user_prompt: str, url: str, page_map: Dict[str, Any], existing_website_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Enhanced version that uses the comprehensive page map for more accurate prompt formulation
        """
        messages = self.create_llm_messages(user_prompt, url, page_map, existing_website_context)
        try:
            logger.info("Generating scan strategy using comprehensive page map")
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.3,  # Lower temperature for more focused responses
                max_tokens=2000
            )
            logger.info("Successfully generated scan strategy")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error analyzing prompt: {e}")
            raise

    def parse_llm_response_to_strategy(self, llm_response_content: str) -> Optional[ScanStrategy]:
        """Converting JSON response into Pydantic model"""
        logger.info("Attempting to convert JSON into ScanStrategy Model")
        try:
            strategy_dict = json.loads(llm_response_content)
            strategy_model = ScanStrategy(**strategy_dict)
            logger.info("Successfully parsed LLM response into ScanStrategy model")
            return strategy_model
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode LLM response as JSON: {e}")
            logger.error(f"LLM Response was: {llm_response_content}")
            return None
        except ValidationError as e:
            logger.error(f"LLM JSON does not match ScanStrategy model: {e}")
            logger.error(f"LLM Response (parsed dict attempt) was: {strategy_dict if 'strategy_dict' in locals() else 'JSON parsing failed earlier'}")
            return None
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
    

