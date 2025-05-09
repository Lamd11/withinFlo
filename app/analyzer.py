from typing import List, Dict, Any
import openai
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
        openai.api_key = self.api_key

    def _generate_test_case_prompt(self, element: UIElement) -> str:
        return f"""Given the following UI element, generate a comprehensive test case:

Element Type: {element.element_type}
Selector: {element.selector}
Visible Text: {element.visible_text}
Attributes: {element.attributes}

Please generate a test case that includes:
1. A descriptive title
2. The type of test (functional, usability, or edge case)
3. Priority level (high, medium, or low)
4. A clear description
5. Preconditions
6. Step-by-step test steps with expected results

Format the response as a JSON object with the following structure:
{{
    "test_case_title": "string",
    "type": "functional|usability|edge_case",
    "priority": "high|medium|low",
    "description": "string",
    "preconditions": ["string"],
    "steps": [
        {{
            "step_number": 1,
            "action": "string",
            "expected_result": "string"
        }}
    ]
}}

Focus on testing the element's core functionality and potential edge cases."""

    def analyze_element(self, element: UIElement) -> TestCase:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a QA expert specializing in test case generation."},
                    {"role": "user", "content": self._generate_test_case_prompt(element)}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            # Parse the response
            test_case_data = response.choices[0].message.content
            # Convert the string response to a dictionary
            import json
            test_case_dict = json.loads(test_case_data)

            # Create TestCase object
            return TestCase(
                test_case_id=f"TC_{element.element_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                test_case_title=test_case_dict["test_case_title"],
                type=test_case_dict["type"],
                priority=test_case_dict["priority"],
                description=test_case_dict["description"],
                preconditions=test_case_dict["preconditions"],
                steps=[
                    TestStep(
                        step_number=step["step_number"],
                        action=step["action"],
                        expected_result=step["expected_result"]
                    )
                    for step in test_case_dict["steps"]
                ],
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