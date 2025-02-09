---
transition: fade
---

# Key Results

<div grid="~ cols-2 gap-8">

{% for result in results %}
<div class="p-4 border rounded">
📈 **{{ result.metric }}**  
{{ result.value }}  
<span class="text-sm opacity-75">{{ result.description }}</span>
</div>
{% endfor %}

</div>

<Footer :authors="metadata.authors" :venue="metadata.venue"/> 