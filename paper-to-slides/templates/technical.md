---
transition: slide-up
layout: two-cols
---

# Technical Approach

::left::
**Core Methodology**
{% for section in sections %}
{% if section.type == 'methodology' %}
- {{ section.summary }}
{% endif %}
{% endfor %}

::right::
```python
{{ sections[0].code_snippet }}
```

<div class="text-xs mt-4">
*Implementation details from section 3.2*
</div> 