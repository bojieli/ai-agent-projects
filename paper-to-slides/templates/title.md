---
theme: seriph
background: https://cover.sli.dev
title: "{{ title }}"
class: text-center
transition: slide-left
layout: center
---

# {{ title }}

<div class="text-xl mt-4">
  {{ authors|join(' · ') }}
  <span class="text-base opacity-75">{{ affiliations|join(' · ') }}</span>
</div>

<div class="text-sm mt-6">
  {{ venue }} · {{ date }}
</div>

<div class="absolute bottom-10 right-6 text-xs opacity-50">
  Automatically generated from research paper
</div> 