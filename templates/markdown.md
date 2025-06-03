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

