from typing import List, Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from .models import AnalysisResult, TestCase, UIElement
import json
from datetime import datetime

class DocumentationGenerator:
    def __init__(self):
        template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml', 'json'])
        )
        
        # Create templates directory if it doesn't exist
        os.makedirs(template_dir, exist_ok=True)
        
        # Create default templates if they don't exist
        self._create_default_templates(template_dir)

    def _create_default_templates(self, template_dir: str):
        # Create markdown template with support for website context
        markdown_template = """# QA Test Documentation: {{ source_url }}
**Analysis Date:** {{ analysis_timestamp }}

## Page: {{ page_title or "Untitled" }}

{% if website_context %}
## Context Information
{% if website_context.type %}* **Website Type:** {{ website_context.type }}{% endif %}
{% if website_context.current_page_description %}* **Page Description:** {{ website_context.current_page_description }}{% endif %}
{% if website_context.user_goal_on_page %}* **User Goal:** {{ website_context.user_goal_on_page }}{% endif %}
{% endif %}

## Generated Test Cases

{% for test_case in generated_test_cases %}
{{ test_case.description }}

---
{% endfor %}

## Identified UI Elements
{% for element in identified_elements %}
### Element ID: {{ element.element_id }}
* **Type:** {{ element.element_type }}
* **Selector:** `{{ element.selector }}`
{% if element.visible_text %}
* **Visible Text:** {{ element.visible_text }}
{% endif %}
{% if element.attributes %}
* **Attributes:**
{% for key, value in element.attributes.items() %}
    * {{ key }}: `{{ value }}`
{% endfor %}
{% endif %}
{% if element.position %}
* **Position:**
    * X: {{ element.position.x }}
    * Y: {{ element.position.y }}
    * Width: {{ element.position.width }}
    * Height: {{ element.position.height }}
{% endif %}

{% endfor %}
"""

        # Create JSON template
        json_template = """{
    "sourceUrl": "{{ source_url }}",
    "analysisTimestamp": "{{ analysis_timestamp }}",
    "pageTitle": "{{ page_title }}",
    {% if website_context %}
    "websiteContext": {{ website_context | tojson }},
    {% endif %}
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
            generated_test_cases=result.generated_test_cases,
            identified_elements=[element.dict() for element in result.identified_elements],
            website_context=result.website_context
        )

    def generate_json(self, result: AnalysisResult) -> Dict[str, Any]:
        template = self.env.get_template("json.json")
        json_str = template.render(
            source_url=result.source_url,
            analysis_timestamp=result.analysis_timestamp.isoformat(),
            page_title=result.page_title,
            identified_elements=[element.dict() for element in result.identified_elements],
            generated_test_cases=[test_case.dict() for test_case in result.generated_test_cases],
            website_context=result.website_context
        )
        return json.loads(json_str)

    def generate_documentation(self, result: AnalysisResult) -> Dict[str, Any]:
        return {
            "markdown": self.generate_markdown(result),
            "json": self.generate_json(result)
        }
