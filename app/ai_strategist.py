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

    def create_llm_messages(self, user_prompt: str, url: str, structured_content: Optional[Dict[str, Any]] = None, existing_website_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """
        Helper method to create system and user messages to insert into OpenAI's model. To formulate the scan strategy
        Enhanced to use structured content from the page for better decision making.
        """ 

        if existing_website_context:
            context_str = json.dumps(existing_website_context)
        else:
            context_str = None
            
        # Prepare structured content information for the LLM
        content_summary = ""
        if structured_content:
            interactive_elements = structured_content.get('interactive_elements', [])
            navigation_elements = structured_content.get('navigation_elements', [])
            
            if interactive_elements or navigation_elements:
                content_summary = "\n\nAvailable Page Elements:\n"
                
                if navigation_elements:
                    content_summary += "Navigation Elements:\n"
                    for elem in navigation_elements[:10]:  # Limit to first 10 to avoid overwhelming
                        content_summary += f"- {elem.get('tag', 'element')}: '{elem.get('text', '')}' (href: {elem.get('href', 'N/A')})\n"
                
                if interactive_elements:
                    content_summary += "\nInteractive Elements:\n"
                    for elem in interactive_elements[:15]:  # Limit to first 15 for better focus
                        elem_type = elem.get('type', 'unknown')
                        text = elem.get('text', '')
                        aria_label = elem.get('aria_label', '')
                        placeholder = elem.get('placeholder', '')
                        name = elem.get('name', '')
                        
                        desc_parts = []
                        if text: desc_parts.append(f"text: '{text}'")
                        if aria_label: desc_parts.append(f"aria-label: '{aria_label}'")
                        if placeholder: desc_parts.append(f"placeholder: '{placeholder}'")
                        if name: desc_parts.append(f"name: '{name}'")
                        
                        if desc_parts:
                            content_summary += f"- {elem_type}: {', '.join(desc_parts)}\n"
        
        system_message_content = f"""
        You are an expert QA Analyst and Web Interaction Strategist.
        Your task is to analyze the user's request, the provided URL, any page context, and the ACTUAL PAGE CONTENT to create a precise, targeted 'scan strategy' to guide a web crawler.
        
        IMPORTANT: You now have access to the actual elements on the page. Use this information to make informed decisions rather than guessing.
        
        Your scan strategy must:
            1. **Use the provided page elements** to identify the most relevant elements for the user's request.
            2. For vague requests (e.g., "about button"), search through the provided elements to find the best semantic matches:
               - Look for text containing "about", "our story", "company", etc.
               - Consider navigation elements that might lead to about pages
               - Use partial matches and semantic similarity
            3. Prioritize elements that directly match the user's intent based on the actual page content.
            4. If no exact match is found, select the closest semantic matches from the available elements.
            5. Focus on 1-3 most relevant elements to avoid overwhelming the crawler.
            6. Always explain your reasoning in the 'purpose' field.
            7. Base your 'type' and 'attributes' on what you see in the structured content, not assumptions.
            8. If the user asks for something not present on the page, create a fallback strategy targeting the most relevant available elements.

        **Generate no more than 3 test cases unless additional elements serve distinct user goals.**

        Respond ONLY with a valid JSON object structured according to the ScanStrategy model:
        {{
          "focus_areas": ["area1", "area2"],
          "target_elements_description": [
            {{"type": "element_tag", "attributes": {{"attr_name": "value"}}, "text_contains": "some text", "purpose": "brief description of element's role in the user's goal and why it was selected from the available options"}},
            // ... more element descriptions based on actual page content
          ]
        }}
        
        Ensure 'purpose' in 'target_elements_description' clearly explains:
        1. How the element relates to the user's specific request
        2. Why this element was chosen from the available page elements
        3. What semantic connection was made if the request was vague
        """

        user_message_content = f"""
        User Request: "{user_prompt}"
        Target URL: "{url}"
        Existing Website Context: "{context_str}"
        {content_summary}

        Based on the actual page elements shown above, please generate a targeted scan strategy JSON that focuses on the most relevant elements for the user's request.
        """
        
        return [
            {"role": "system", "content": system_message_content.strip()},
            {"role": "user", "content": user_message_content.strip()}
        ]


    def develop_scan_strategy(self, user_prompt: str, url: str, structured_content: Optional[Dict[str, Any]] = None, page_html_snapshot: Optional[str] = None, existing_website_context: Optional[Dict[str, Any]] = None) -> Optional[ScanStrategy]:
        """
        Main public method of this class. It takes the user's request and other relevant info and returns the structured scan strategy.
        Enhanced to use structured content and HTML snapshot for better analysis.
        """

        llm_res = self.prompt_formulation(user_prompt, url, structured_content, existing_website_context)
        parsed_strategy = self.parse_llm_response_to_strategy(llm_res)
        print(parsed_strategy)
        return parsed_strategy
    
    def prompt_formulation(self, user_prompt: str, url: str, structured_content: Optional[Dict[str, Any]] = None, existing_website_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Calls the LLM with the constructed prompt and returns the strategy content string.
        Enhanced to include structured content in the prompt.
        """
        messages = self.create_llm_messages(user_prompt, url, structured_content, existing_website_context)
        try:
            logger.info("Attempting to generate informed scan strategy using actual page content")
            response = self.client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=messages,
                temperature=0.3,  # Lower temperature for more deterministic results when working with actual data
                max_tokens=2000
            )
            logger.info("Successfully generated informed scan strategy")
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
    

