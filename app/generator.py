from typing import List, Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from .models import AnalysisResult, TestCase, UIElement
import json
from datetime import datetime
import io # Added for in-memory PDF generation
from markdown_pdf import MarkdownPdf, Section # Added for PDF generation

# Path to the CSS file
PDF_STYLES_PATH = os.path.join(os.path.dirname(__file__), "static", "pdf_styles.css")

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

    def generate_pdf(self, result: AnalysisResult) -> bytes:
        markdown_content = self.generate_markdown(result)
        
        pdf_doc = MarkdownPdf(toc_level=2)

        # Read custom CSS
        user_css = ""
        try:
            with open(PDF_STYLES_PATH, 'r') as f:
                user_css = f.read()
        except FileNotFoundError:
            # Handle case where CSS file might be missing, or log a warning
            print(f"Warning: CSS file not found at {PDF_STYLES_PATH}")
        except Exception as e:
            print(f"Warning: Error reading CSS file at {PDF_STYLES_PATH}: {e}")

        pdf_doc.add_section(Section(markdown_content, toc=True), user_css=user_css)
        
        # Save PDF to an in-memory bytes buffer
        buffer = io.BytesIO()
        pdf_doc.save(buffer)
        buffer.seek(0)
        pdf_bytes = buffer.read()
        buffer.close()
        return pdf_bytes

    def generate_documentation(self, result: AnalysisResult) -> Dict[str, Any]:
        # PDF will be generated on-demand by the dedicated PDF endpoint
        return {
            "markdown": self.generate_markdown(result),
            "json": self.generate_json(result)
            # "pdf" key is removed from here
        }
