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

    def create_llm_messages(self, user_prompt: str, url: str, existing_website_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """
        Helper method to create system and user messages to insert into OpenAI's model. To formulate the scan strategy
        """ 

        if existing_website_context:
            context_str = json.dumps(existing_website_context)
        else:
            context_str = None
        
        system_message_content = f"""
        You are an expert QA Analyst and Web Interaction Strategist.
        Your task is to analyze the user's request, the provided URL, and any page context. From this, create a concise, high-impact, and focused 'scan strategy' to guide a web crawler.
        
        Your scan strategy must:
            1. Identify the most critical and representative elements relevant to the user’s request (avoid listing every minor variation).
            2. Avoid creating repetitive or overlapping test coverage.
            3. Bundle similar interactions under a unified purpose (e.g., group multiple nav links into one navigational test case).
            4. Minimize total test cases while maximizing functional coverage.
            5. If the user’s request is vague (e.g., "about button"), use semantic inference to guess likely intent:
            - Look for sections labeled "About", "Our Story", or similar
            - Include elements with synonyms, partial matches, or similar positioning (e.g., nav menus, header buttons)
            6. If no direct match is found, propose a best-guess fallback element that likely aligns with the user's intent.
            7. Generate no more than 3 test cases unless additional elements serve distinct user goals.
            8. If the requested element (e.g., “about button”) cannot be found through direct matching or semantic inference, include a best-guess placeholder element in the output with an appropriate explanation.
            9. If the request refers to a UI element and no clear match is found, explore the nav bar, header, footer links, or anywhere on the entire page for potential intent matches. Use proximity, link order, or semantic cues to approximate user intent.
            

        **Generate no more than 3 test cases unless additional elements serve distinct user goals.**

        Respond ONLY with a valid JSON object structured according to the ScanStrategy model:
        {{
          "focus_areas": ["area1", "area2"],
          "target_elements_description": [
            {{"type": "element_tag", "attributes": {{"attr_name": "value"}}, "text_contains": "some text", "purpose": "brief description of element's role in the user's goal"}},
            // ... more element descriptions (can be based on user prompt, not necessarily strict HTML tags)
          ],
          // ... any other fields you define in your ScanStrategy Pydantic model
        }}
        Ensure 'purpose' in 'target_elements_description' clearly explains how the element relates to achieving the user's specific request.
        If the user's request is vague, try to define broader focus_areas.
        """

        user_message_content = f"""
        User Request: "{user_prompt}"
        Target URL: "{url}"
        Existing Website Content: "{existing_website_context}"

        Please generate generate the scan strategy JSON based on this information.
        """
        return [
            {"role": "system", "content": system_message_content.strip()},
            {"role": "user", "content": user_message_content.strip()}
        ]


    def develop_scan_strategy(self, user_prompt: str, url: str, page_html_snapshot: Optional[str] = None, existing_website_context: Optional[Dict[str, Any]] = None) -> Optional[ScanStrategy]:
        """
        Main public method of this class. It takes the user's request and other relevant info and returns the structured scan strategy.
        """

        llm_res = self.prompt_formulation(user_prompt, url, existing_website_context)
        parsed_stategy = self.parse_llm_response_to_strategy(llm_res)
        print(parsed_stategy)
        return parsed_stategy
    
    def prompt_formulation(self, user_prompt: str, url: str, existing_website_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Calls the LLM with the constructed prompt and returns the strategy content string.
        """
        messages = self.create_llm_messages(user_prompt, url, existing_website_context)
        try:
            logger.info("Attempting to generate prompt into format user's prompt into JSON search pattern")
            response = self.client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=messages,
                temperature=0.5,
                max_tokens=2000
            )
            logger.info("Successfully transformed user's prompt into JSON search pattern")
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
    

