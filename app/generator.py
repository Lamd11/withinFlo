from typing import List, Dict, Any
from jinja2 import Environment, FileSystemLoader
import os
from .models import AnalysisResult, TestCase, UIElement
import json
from datetime import datetime

class DocumentationGenerator:
    def __init__(self):
        template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        self.env = Environment(loader=FileSystemLoader(template_dir))
        
        # Create templates directory if it doesn't exist
        os.makedirs(template_dir, exist_ok=True)
        
        # Create default templates if they don't exist
        self._create_default_templates(template_dir)

    def _create_default_templates(self, template_dir: str):
        # Create markdown template
        markdown_template = """# QA Test Documentation: {{ source_url }}
**Analysis Date:** {{ analysis_timestamp }}

## Page: {{ page_title }}

{% for test_case in generated_test_cases %}
### Test Case ID: {{ test_case.test_case_id }}
* **Title:** {{ test_case.test_case_title }}
* **Type:** {{ test_case.type }}
* **Priority:** {{ test_case.priority }}
* **Description:** {{ test_case.description }}
{% if test_case.preconditions %}
* **Preconditions:**
{% for precondition in test_case.preconditions %}
    * {{ precondition }}
{% endfor %}
{% endif %}
* **Steps:**
{% for step in test_case.steps %}
    {{ step.step_number }}. **Action:** {{ step.action }}
        **Expected Result:** {{ step.expected_result }}
{% endfor %}

{% endfor %}
"""
        
        # Create JSON template
        json_template = """{
    "sourceUrl": "{{ source_url }}",
    "analysisTimestamp": "{{ analysis_timestamp }}",
    "pageTitle": "{{ page_title }}",
    "identifiedElements": {{ identified_elements | tojson }},
    "generatedTestCases": {{ generated_test_cases | tojson }}
}"""

        # Write templates to files
        with open(os.path.join(template_dir, "markdown.md"), "w") as f:
            f.write(markdown_template)
        
        with open(os.path.join(template_dir, "json.json"), "w") as f:
            f.write(json_template)

    def generate_markdown(self, result: AnalysisResult) -> str:
        template = self.env.get_template("markdown.md")
        return template.render(
            source_url=result.source_url,
            analysis_timestamp=result.analysis_timestamp.isoformat(),
            page_title=result.page_title,
            generated_test_cases=result.generated_test_cases
        )

    def generate_json(self, result: AnalysisResult) -> Dict[str, Any]:
        template = self.env.get_template("json.json")
        json_str = template.render(
            source_url=result.source_url,
            analysis_timestamp=result.analysis_timestamp.isoformat(),
            page_title=result.page_title,
            identified_elements=[element.dict() for element in result.identified_elements],
            generated_test_cases=[test_case.dict() for test_case in result.generated_test_cases]
        )
        return json.loads(json_str)

    def generate_documentation(self, result: AnalysisResult) -> Dict[str, Any]:
        return {
            "markdown": self.generate_markdown(result),
            "json": self.generate_json(result)
        } 