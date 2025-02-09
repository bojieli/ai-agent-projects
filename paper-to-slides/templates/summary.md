---
transition: fade-out
---

# Key Contributions

<div grid="~ cols-2 gap-4">
<div>

**Core Innovations**
{% for point in key_points.innovations %}
- {{ point }}
{% endfor %}

</div>
<div>

**Experimental Results**
{% for result in key_points.results %}
- {{ result }}
{% endfor %}

</div>
</div>

<|figure:{{ main_figure.image }}|caption:{{ main_figure.caption }}|>

<!--
SPEAKER: [pause=500] {{ main_figure.summary }}
--> 