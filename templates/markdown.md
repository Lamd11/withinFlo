# QA Test Documentation: {{ source_url }}
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
