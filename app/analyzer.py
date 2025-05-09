from typing import List, Dict, Any
from openai import OpenAI
from .models import UIElement, TestCase, TestStep
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCaseAnalyzer:
    def __init__(self):
        # Load API key from environment
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = OpenAI(api_key=self.api_key)

    def _generate_test_case_prompt(self, element: UIElement) -> str:
        return f"""Given the following UI element, generate a comprehensive test case in markdown format:

Element Type: {element.element_type}
Selector: {element.selector}
Visible Text: {element.visible_text}
Attributes: {element.attributes}

Please generate a test case that follows this exact markdown format:

### Test Case ID: TC_[ELEMENT_TYPE]_[SEQUENCE]
* **Title:** [Descriptive title of what is being tested]
* **Type:** [End-to-End | Functional | Usability | Edge Case]
* **Priority:** [High | Medium | Low]
* **Description:** [Clear description of what the test case verifies]
* **Related Elements:**
    * [List all related selectors and their purposes]
* **Preconditions:**
    * [List all required preconditions]
* **Steps:**
    1. **Action:** [Detailed action to perform]
       **Expected Result:** [Expected outcome]
    [Continue with numbered steps...]
* **Postconditions:**
    * [List all expected postconditions]

Focus on creating detailed, actionable test steps that verify the element's functionality and potential edge cases. Include all relevant selectors and expected behaviors."""

    def analyze_element(self, element: UIElement) -> TestCase:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a QA expert specializing in test case generation. Generate detailed, well-structured test cases in markdown format."},
                    {"role": "user", "content": self._generate_test_case_prompt(element)}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            # Get the markdown content
            test_case_markdown = response.choices[0].message.content

            # Create TestCase object with the markdown content
            return TestCase(
                test_case_id=f"TC_{element.element_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                test_case_title=test_case_markdown,  # Store the full markdown content
                type="End-to-End",  # Default type
                priority="High",    # Default priority
                description=test_case_markdown,  # Store the full markdown content
                preconditions=[],   # These will be in the markdown
                steps=[],          # These will be in the markdown
                related_element_id=element.element_id
            )

        except Exception as e:
            logger.error(f"Error analyzing element {element.element_id}: {str(e)}")
            raise

    def analyze_elements(self, elements: List[UIElement]) -> List[TestCase]:
        test_cases = []
        for element in elements:
            try:
                test_case = self.analyze_element(element)
                test_cases.append(test_case)
            except Exception as e:
                logger.warning(f"Failed to analyze element {element.element_id}: {str(e)}")
                continue
        return test_cases 