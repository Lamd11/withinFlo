from typing import List, Dict, Any
from openai import AsyncOpenAI
from app.models import UIElement, TestCase, TestStep # Assuming TestStep might be used later if parsing full steps
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
import re # For parsing
import asyncio
from asyncio import Semaphore

# Load environment variables
load_dotenv() # Temporarily commented out

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCaseAnalyzer:
    def __init__(self, max_concurrent_requests: int = 10):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OPENAI_API_KEY environment variable is not set. (load_dotenv is commented out)")
            raise ValueError("OPENAI_API_KEY environment variable is not set. (load_dotenv is commented out)")
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.semaphore = Semaphore(max_concurrent_requests)

    def _generate_test_case_prompt(self, element: UIElement, website_context: Dict[str, Any] = None) -> str:
        """
        Generates a prompt to create a feature-aware test case for a given UI element,
        considering its potential role in a user interaction or mini-feature.
        """
        context_str = ""
        if website_context:
            context_str += "\n**Overall Website/Application Context:**\n"
            if website_context.get("type"): # e.g., "E-commerce Platform", "SaaS Dashboard", "Blog"
                context_str += f"* Primary Type: {website_context['type']}\n"
            if website_context.get("current_page_description"): # e.g., "Product Detail Page for 'XYZ Camera'", "User Login Screen"
                context_str += f"* Current Page/View: {website_context['current_page_description']}\n"
            if website_context.get("user_goal_on_page"): # e.g., "User is attempting to add a product to cart and proceed to checkout"
                context_str += f"* Likely User Goal on this Page: {website_context['user_goal_on_page']}\n"

        prompt = f"""As a QA expert, your task is to analyze the provided UI element and its context to generate a comprehensive, scenario-based test case in Markdown format.
The goal is not just to test the element in isolation, but to identify a key user interaction, workflow, or "mini-feature" that this element is part of.
Think about what a user would be trying to achieve by interacting with this element and what subsequent steps or verifications would be logical.

**Primary UI Element Details:**
* Element Type: `{element.element_type}`
* Selector: `{element.selector}`
* Visible Text: `{element.visible_text if element.visible_text else "N/A"}`
* Attributes: `{element.attributes}`
{context_str}
**Instructions for Test Case Generation:**

1.  **Identify Feature/User Flow:** Based on the element and any provided context, determine a relevant user flow or feature to test. For example, if the element is an "Add to Cart" button, the feature is "Add Product to Cart and Verify Cart Update." If it's a username field, the flow could be "Successful User Login."
2.  **Define Scope:** The test case should cover a focused scenario. This might involve a few steps: an action on the primary element, and then verification steps that might involve other related elements or system feedback.
3.  **Test Case ID:** Construct a meaningful Test Case ID. Use the format: `TC_[FEATURE_ABBREVIATION]_[SCENARIO_DESCRIPTION_ABBREVIATION]_[SEQUENCE_NUMBER]`. For example: `TC_CART_ADD_VERIFY_001` or `TC_LOGIN_SUCCESS_001`. The AI should generate this based on the test case content.
4.  **Related Elements:** If the flow involves other crucial elements for actions or verification, list their selectors and purpose.
5.  **Preconditions:** List specific conditions that must be true *before* starting the test steps.
6.  **Actionable Steps:** Write clear, sequential steps. Each step must include an "Action" and an "Expected Result."
7.  **Placeholder Data:** Use bracketed placeholders for dynamic data (e.g., `[Valid Username]`, `[Product Name]`, `[Test Item Price]`).

**Output Format (Strict Markdown):**

### Test Case ID: TC_[FEATURE_ABBREVIATION]_[SCENARIO_ABBREVIATION]_[NUMBER]
* **Feature Tested:** [e.g., Guest Checkout, User Login, Add to Cart, Search Functionality]
* **Title:** [Descriptive title, e.g., Verify successful guest checkout with one product and valid payment]
* **Type:** [End-to-End | Functional | Usability | Edge Case | Scenario-Based]
* **Priority:** [High | Medium | Low]
* **Description:** [Clear, concise description of the test case's objective and the user flow it covers.]
* **Preconditions:**
    * The user is on the [Page Name/URL where the primary element is located].
    * [e.g., At least one product is available for purchase.]
    * [e.g., User is not logged in (for a guest checkout test).]
* **Steps:**
    1. **Action:** [e.g., Navigate to the product page for '[Product Name]']
       **Expected Result:** [e.g., The product page for '[Product Name]' loads successfully.]
    2. **Action:** [e.g., Click the '{element.visible_text if element.visible_text else element.element_type}' button (selector: `{element.selector}`)]
       **Expected Result:** [e.g., A notification confirming '[Product Name] has been added to cart' appears. The cart icon updates to show 1 item.]
    3. **Action:** [e.g., Click on the cart icon (`[selector_for_cart_icon]`) ]
       **Expected Result:** [e.g., The shopping cart page loads, displaying '[Product Name]' with quantity 1.]
    *--(Add more steps as needed to complete the scenario)--*

---
Now, please generate the test case based on the Primary UI Element Details and any context provided above.
Focus on generating a test case that represents a realistic user scenario involving this element.
If the element is very generic (e.g. a 'div' with no clear text), try to infer its purpose from its attributes or common web patterns. If a meaningful multi-step scenario cannot be reasonably inferred, generate a focused functional test for the element itself, including potential interactions and expected states.
"""
        return prompt

    def _parse_markdown_to_testcase_fields(self, markdown_content: str, element_id: str, default_element_type: str) -> Dict[str, Any]:
        """
        Parses the generated markdown to extract key fields for the TestCase object.
        This is a helper and can be made more robust.
        """
        data = {
            "test_case_id": f"TC_{default_element_type.upper()}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}", # Fallback ID
            "test_case_title": "Generated Test Case", # Fallback title
            "type": "Functional", # Default
            "priority": "Medium", # Default
            "description": markdown_content, # Always store full markdown
            "preconditions": [], # Will remain in markdown
            "steps": [], # Will remain in markdown
            "related_element_id": element_id
        }

        # Regex patterns for common fields
        patterns = {
            "test_case_id": r"### Test Case ID:\s*(TC_\w+)",
            "test_case_title": r"\* \*\*Title:\*\*\s*(.+)",
            "type": r"\* \*\*Type:\*\*\s*(\w+[-\w+]*)", # Handles 'End-to-End', 'Scenario-Based'
            "priority": r"\* \*\*Priority:\*\*\s*(\w+)",
            "feature_tested": r"\* \*\*Feature Tested:\*\*\s*(.+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, markdown_content)
            if match:
                data[key] = match.group(1).strip()
        
        # Clean up the title by removing "Verify" prefix if it exists and capitalize first letter
        if data.get("test_case_title"):
            title = re.sub(r'^(?:Verify\s+|Verifies\s+|Verification\s+of\s+)', '', data["test_case_title"], flags=re.IGNORECASE)
            data["test_case_title"] = title[0].upper() + title[1:] if title else title
        
        # If a more specific title from "Feature Tested" is found, prefer it or combine
        if data.get("feature_tested") and data["test_case_title"] == "Generated Test Case":
             data["test_case_title"] = data['feature_tested']
        elif data.get("feature_tested") and data["test_case_title"] != "Generated Test Case" and data["feature_tested"] not in data["test_case_title"]:
             data["test_case_title"] = f"{data['feature_tested']} - {data['test_case_title']}"

        return data


    async def analyze_element(self, element: UIElement, website_context: Dict[str, Any] = None) -> TestCase:
        try:
            prompt_content = self._generate_test_case_prompt(element, website_context)
            
            logger.info(f"Attempting to generate test case for element: {element.selector} ({element.element_type}) with context: {website_context}")

            async with self.semaphore:  # Control concurrent requests
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert QA Automation Engineer tasked with generating detailed, scenario-based test cases in Markdown format from UI element data and contextual website information. Focus on user flows and comprehensive verification."},
                        {"role": "user", "content": prompt_content}
                    ],
                    temperature=0.6,
                    max_tokens=2500
                )
            
            test_case_markdown = response.choices[0].message.content
            logger.info(f"Successfully generated markdown for element {element.element_id}:\n{test_case_markdown[:500]}...")

            # Parse markdown for key fields
            parsed_data = self._parse_markdown_to_testcase_fields(test_case_markdown, element.element_id, element.element_type)

            return TestCase(
                test_case_id=parsed_data["test_case_id"],
                test_case_title=parsed_data["test_case_title"],
                type=parsed_data["type"],
                priority=parsed_data["priority"],
                description=parsed_data["description"], # Full markdown stored in description
                preconditions=[],   # These are embedded in the markdown
                steps=[],           # These are embedded in the markdown
                related_element_id=parsed_data["related_element_id"]
            )
        except Exception as e:
            logger.error(f"Error analyzing element {element.element_id} ({element.selector}): {str(e)}", exc_info=True)
            raise

    async def analyze_elements(self, elements: List[UIElement], website_context: Dict[str, Any] = None, progress_callback=None) -> List[TestCase]:
        # Get the current event loop
        loop = asyncio.get_event_loop()
        
        # Create tasks in the current loop
        tasks = []
        for element in elements:
            tasks.append(self.analyze_element(element, website_context))
        
        # Process all elements concurrently and gather results
        test_cases = []
        completed_count = 0
        total_count = len(tasks)
        
        for task in asyncio.as_completed(tasks):
            try:
                test_case = await task
                test_cases.append(test_case)
                completed_count += 1
                
                # Call progress callback if provided
                if progress_callback:
                    await progress_callback(completed_count, total_count)
                    
                logger.info(f"Completed processing test case: {test_case.test_case_id} ({completed_count}/{total_count})")
            except Exception as e:
                logger.warning(f"Failed to generate test case due to: {str(e)}. Skipping this element.")
                completed_count += 1
                if progress_callback:
                    await progress_callback(completed_count, total_count)
                continue
        
        return test_cases