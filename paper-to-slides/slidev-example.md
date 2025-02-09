---
# You can also start simply with 'default'
theme: seriph
# random image from a curated Unsplash collection by Anthony
# like them? see https://unsplash.com/collections/94734566/slidev
background: https://cover.sli.dev
# some information about your slides (markdown enabled)
title: "AI Agents: Demo ➡️ Production"
info: |
  ## AI Agents: Demo ➡️ Production

# apply unocss classes to the current slide
class: text-center
# https://sli.dev/features/drawing
drawings:
  persist: false
# slide transition: https://sli.dev/guide/animations.html#slide-transitions
transition: slide-left
# enable MDC Syntax: https://sli.dev/features/mdc
mdc: true
---

# AI Agents: Demo ➡️ Production

Bojie Li

Jan 11, 2025

<div @click="$slidev.nav.next" class="mt-12 py-1" hover:bg="white op-10">
  Press Space for next page <carbon:arrow-right />
</div>

<!--
The last comment block of each slide will be treated as slide notes. It will be visible and editable in Presenter Mode along with the slide. [Read more in the docs](https://sli.dev/guide/syntax.html#notes)
-->

---
transition: fade-out
---

# Table of contents

<Toc text-sm minDepth="1" maxDepth="2" columns="2" />

---
transition: slide-up
layout: two-cols
---

# Coding: The First Major Use Case for AI Agents

Spent 60% of the time on a personal project, iCourses (course rating platform):

- 🚀 **Nov. 10**: project launched
- 📈 **Dec. 10**: 50K lines of code, feature complete
- ✅ **Jan. 9**: production ready with 67K lines of code

<img src="/images/icourse.jpg" alt="iCourses" width="400">

::right::

<img src="/images/code.jpg" alt="Coding Statistics">

---
transition: slide-up
layout: image-right
image: /images/cursor-agent.png
level: 2
---

# Cursor Agent vs. Windsurf: Context is All You Need
- Cursor Agent: 
  - 📖 Reads full source code file
  - 🔄 Never generates duplicate functions
  - 💰 More costly due to more input tokens
- Windsurf: 
  - 📄 Only reads 100 lines of code at a time
  - 🔄 Often generates duplicate functions
  - 💵 Saves cost due to fewer input tokens

---
transition: slide-up
layout: image-right
image: /images/cursor-agent-code-review.png
level: 2
---

# Code Review is Important for Coding Agents

Without code review:

- ❌ LLMs often generate incorrect import paths or API usage.
- ⚠️ Applying diff is often inaccurate and removes a large fraction of code.

With code review:

1. ✅ Run a linter after applying diff to check for import/API usage errors.
2. 🔍 Use an LLM to check whether the diff removes too much code, and fix the errors.

---
transition: slide-up
level: 2
---

# MetaGPT: Inefficient Multi-Agent Architecture

<div grid="~ cols-2 gap-4">
<div>

- MetaGPT replicates inefficient corporate structures:
  - 📋 Product manager
  - ⏰ Project manager
  - 🎨 UI designer
  - 🖥️ Frontend developer
  - 💾 Backend developer
  - 📊 Data engineer
  - 🧪 Test engineer
</div>
<div>

- Problems with this approach:
  - 🐌 Slow progress due to role coordination
  - 💬 Communication overhead between roles
  - ⚔️ Conflicts between different roles
</div>
</div>

---
transition: slide-up
level: 2
---

# Why Single Agent is Better for Coding

<div grid="~ cols-2 gap-4">
<div>

- Human teams need multiple roles because:
  - 🧑‍💻 Individual skill limitations
  - 💪 Complementary capabilities
  - ⏱️ Limited development speed
  - 👥 Humans need emotional support from peers
</div>
<div>

- AI doesn't need this structure because:
  - 🎯 Single SOTA model has all capabilities
  - ⚡ Can handle full-stack development
  - 🚀 Much faster than humans
  - 🤖 No need for emotional support from peers
</div>
</div>


---
transition: slide-up
level: 2
---

# Devin/OpenHands: From Co-pilot to Autopilot
- Pre-requisites:
  - 📝 **Code must be well-documented**
  - ✅ **Have complete test coverage**
- Devin/OpenHands can fully automate 50% development requirements
  - 🔍 Requirement analysis
  - 💻 Code generation
  - 👀 Code review
  - 🧪 Running tests
  - 🚀 Deployment
- Human developer is still needed for the remaining 50% requirements
  - 🛠️ Devin/OpenHands for simple bug fixes, feature enhancements, and refactoring
  - 👥 Human + Cursor Agent for the remaining work
- **4x development velocity increase possible**
  - 50% time saved by autopilot ✖️ 50% speedup with co-pilot


---
transition: slide-up
level: 2
---

# When Autopilot Coding Agents Fail

<div grid="~ cols-2 gap-4">
<div>

- 🔄 **Linear thinking trap**
  - Keeps modifying incorrect code
  - Unable to backtrack to working versions
  - Gets stuck in local optimization
- 🏗️ **Ignoring existing codebase**
  - Generates inconsistent code style
  - Misses project constraints
  - Creates integration issues
- 🔍 **Incomplete fixes**
  - Only fixes found instances of issues
  - Misses similar problems elsewhere
  - Creates inconsistencies across codebase
</div>
<div>

- 🔧 **Poor library choices**
  - Keeps patching problematic libraries
  - Fails to consider alternatives
  - Creates technical debt
- ⚠️ **Undetected regressions**
  - Changes break existing features
  - Lacks comprehensive test coverage
  - Hard to catch without automation
- 🔁 **Code duplication**
  - Violates DRY principle
  - Doesn't reuse existing code
  - Makes maintenance difficult
</div>
</div>

<div class="mt-4">
<strong>Key Takeaway:</strong> Comprehensive automated testing is crucial before using autopilot AI coding agents
</div>

---
transition: slide-up
level: 2
---

# VLMs are Essential for Autopilot Coding Agents

<div grid="~ cols-2 gap-4">
<div>

Traditional Playwright/Selenium testing are not sufficient for autopilot coding agents:

- 📐 Cannot detect layout issues like misalignment and poor formatting
- 📝 Cannot detect content data errors 
- 🔄 Cannot detect data inconsistencies between UI components (e.g., form input vs display, statistics vs original data)

👨‍💻 Therefore, current coding agents still requires human acceptance testing and iterative modifications, and cannot achieve end-to-end automated autopilot.

🎯 Autopilot should enable hands-off development rather than requiring constant babysitting from developers.

</div>
<div>

🧠 Common sense and 👁️ visual capabilities are needed to detect UI issues.

💡 Solution: 👁️ VLMs with 🖥️ computer use capabilities like Claude 3.5 Sonnet or CogAgent.

<img src="/images/cogagent.png" alt="CogAgent">

</div>
</div>


---
transition: slide-up
level: 2
---

# Agents for Testing & Security

<div grid="~ cols-2 gap-4">
<div>

## Automated Testing
- 🖥️ **Vision LLMs-based Testing**
  - Visual regression testing
  - Layout verification
  - Cross-browser compatibility
  - Responsive design validation
- 🤖 **VLM-based End-to-End Testing**
  - User journey simulation
  - Edge case discovery
  - Fuzz testing

</div>
<div>

## Security & Validation
- 🔒 **LLM-based Security Testing**
  - Vulnerability scanning
  - Penetration testing
  - API security validation
  - Authentication testing
- 📝 **LLM-based Documentation Testing**
  - Spec-implementation alignment
  - API documentation generation & validation
  - Consistency checking

</div>
</div>


---
transition: slide-up
layout: center
class: text-center
level: 2
---

# AI Coding Agents: The Future

---
transition: slide-up
level: 2
---

# Pair Programming with Coding Agents
<div grid="~ cols-2 gap-4">
<div>

## Independent Developer
- 🚀 Solo full-stack developer empowered by AI
- 💡 Ideas rapidly prototyped and deployed
- ⚡ Development velocity increase to **4x**
  - 50% work completed by autopilot ✖️ 50% speedup with co-pilot
- 📉 Lower cost of experimentation for startups
- 👤 "Billion-dollar one-person companies" (Sam Altman)
</div>
<div>

## Enterprise Software Dev
- 🏭 Industry workflows transformed through AI Agents
- 🖥️ GUI transformed into Natural Language UI 
- 📊 Unstructured knowledge becomes structured data
- 💪 Customization costs significantly reduced
- 🔄 Digital transformation of traditional industries become possible
</div>
</div>

<br>

<div class="text-center">
<p class="opacity-75 italic">
The future of programming is not about writing code, but about expressing ideas and letting AI handle the implementation.
</p>
</div>

---
transition: slide-up
level: 2
---

# The Future Role of Software Engineers: From Coder to Architect & Product Manager

For software projects with moderate technical complexity:

- 🎯 Engineers will evolve into **architects + product managers + project managers**
- ⚡ Break down projects into clear, verifiable 1-hour tasks for AI
  - AI may complete 1-hour tasks in 10 minutes, including requirement analysis, code generation, code review, and testing
- ✅ Human focus on requirements validation and iteration
- 🗣️ Soft skills like communication become crucial
- 🏗️ System architecture and problem-solving remain human-centric

---
transition: slide-up
layout: center
class: text-center
level: 2
---

# Which LLM is the Best for Coding?

---
transition: slide-up
level: 2
---

# OpenAI o1 vs. Claude 3.5 Sonnet

<div grid="~ cols-2 gap-4">
<div>
<h3>OpenAI o1</h3>
<ul>
<li>🏆 Good at solving contest problems and complex reasoning</li>
<li>✨ Generated code is more accurate given enough context</li>
<li>🔧 Less knowledge of real-world engineering</li>
<li>🐌 Slower due to test-time reasoning</li>
<li>💰 More expensive</li>
</ul>
<p>Suitable for code generation for tasks with less context, e.g., creating a demo from scratch</p>
<p>Suitable for tasks that require high IQ, e.g., reverse engineering and algorithmic problems</p>
</div>
<div>
<h3>Claude 3.5 Sonnet</h3>
<ul>
<li>👨‍💻 Better software engineering skills</li>
<li>⚡ Faster</li>
<li>💰 Cheaper</li>
<li>⚠️ Often make mistakes in details</li>
</ul>
<p>Suitable for simple tasks, e.g., intent analysis, code review, code refactoring, language translation</p>
<p>Suitable for code/patch generation in a large codebase</p>
<p>Recommended workflow: Start with Claude 3.5 Sonnet for code generation, and if results are unsatisfactory, escalate to o1</p>
</div>
</div>


---
transition: slide-up
layout: image-right
image: /images/open-source-coding.png
level: 2
---

# SOTA Open Models Enable On-Premise Deployment

Information security requirements of many companies require on-premise deployments.

See the Chatbot Arena coding leaderboard: https://lmarena.ai/
1. 🔒 OpenAI o1: $60 / 1M tokens
2. 🔒 Claude 3.5 Sonnet: $15 / 1M tokens
3. **DeepSeek V3: $0.28 / 1M tokens**
4. 🔒 OpenAI GPT-4o: $10 / 1M tokens
5. Yi-Lightning: $0.14 / 1M tokens

On-premise AI coding agents are now possible with DeepSeek V3 🚀


---
transition: fade-out
layout: center
class: text-center
---

# Building Effective RAG Agents

---
transition: slide-up
level: 2
---

# Why AI Agents Haven't Reached Production?

<div grid="~ cols-3 gap-4">
<div>

### 1. RAG Accuracy Issues
- 🎯 Low precision in retrieval results
  - Irrelevant or outdated information
  - Wrong context leads to wrong answers
- 📊 Poor recall of critical information
  - Missing key facts and context
  - Incomplete knowledge base
</div>
<div>

### 2. Weak Reasoning Abilities
- 🧮 Frequent calculation errors
- 🤔 Logic and inference problems
  - Cannot handle complex dependencies
  - Struggles with multi-step reasoning
- ⚠️ Inconsistent outputs
</div>
<div>

### 3. Lack of Adaptability
- 🔄 Gets stuck in repetitive loops
- 🚫 Unable to change strategies when stuck
- ❌ No creative problem-solving when original approach fails
</div>
</div>

---
transition: slide-up
level: 2
---

# RAG: Retrieval is More Important than Generation

Domain-specific search applications can outperform generic ones.

<div grid="~ cols-2 gap-4">
<img src="/images/perplexity-search.png" alt="Perplexity Search" width="400">
<img src="/images/icourse-search.png" alt="iCourses Search" width="400">
</div>

---
transition: slide-up
layout: two-cols
level: 2
---

# RAG: Generic Search Engines Have Low Precision and Recall

<img src="/images/perplexity-search-sources.png" alt="Perplexity Search" width="400">

::right::

🔍 Query: "对比中科大微积分课程各个老师的给分情况"

❌ Problems of retrieval in Perplexity:

- 🎯 **Precision: irrelevant results**
  - The webpage "数学分析测评" is for 国科大 (UCAS) rather than 中科大 (USTC)
  - The 3 courses found are "微分方程引论", "实分析", "近世代数", NOT "微积分"
- 📊 **Recall: missing relevant results**
  - Only 3 courses are found, but there are actually 6 courses related to "微积分" in USTC

Keyword or embedding search on unstructured data is hard to achieve high precision and recall.

---
transition: slide-up
layout: two-cols
layoutClass: gap-16
level: 2
---

# RAG Applications should be Agents based on Structured Data

1. 🧠 **Intent analysis**: generate entity types and search queries
2. 🔍 **Information retrieval**: search structured database and rerank based on relevance
3. 📝 **Build context**: generate prompt for LLM from search results and user memory
4. 🤖 **LLM Generation**:
  - If information is enough, generate the answer and stream to user
  - If information is not enough, generate a next search query and return to step 2

::right::

<img src="/images/icourse-search.png" alt="iCourses Search">

---
transition: slide-up
layout: center
class: text-center
level: 2
---

# Data is the Moat for Most Apps

Everyone can use SOTA LLMs, but LLMs themselves do not contain domain-specific knowledge.

---
transition: slide-up
level: 2
---

# VLMs can Automate Structured Data Collection

<div grid="~ cols-3 gap-4">
<div>
Traditional crawler pipelines need customization for each website in order to extract structured data.

With VLMs, data collection and cleaning can be automated.
1. 🖥️ **Computer Use**: analyze the screenshot and a11y tree to generate code for traversing the website
2. 📊 **Extraction**: run the crawler and extract structured data from each webpage

</div>
<div>
<img src="/images/crawling-ucsd.png" alt="UCSD Crawling Code" width="330">
</div>
<div>
<img src="/images/crawling-ucsd-result.png" alt="UCSD Crawling Code" width="330">
</div>
</div>

---
transition: slide-up
layout: two-cols
layoutClass: gap-16
level: 2
---

# Will VLM-based Crawler be Very Expensive?

- 💰 1 VLM call = $0.001
- 📚 A typical university website has 10K ~ 100K courses
  - 💵 $10 ~ $100 for a university  
- 👨‍💻 Writing a crawler manually costs $100 ~ $500
- 🎯 For more fragmented data collection tasks, i.e., collecting instructor information for each department, manually writing crawler is prohibitively expensive
  - 👥 A department only have 100 ~ 1K instructors
  - 🤖 Only VLM can handle this task in a cost-effective way

::right::

<img src="/images/ai-crawler.png" alt="AI Crawler" width="330">

---
transition: slide-up
layout: two-cols
layoutClass: gap-16
level: 2
---

# Can We Reduce the VLM Cost in Data Collection?

<img src="/images/a11y-tree.png" alt="A11y Tree">

::right::

🌳 Use a11y tree to generate code for traversing the website, so we no longer need to invoke VLM for each webpage.

⚠️ Note: do not use HTML source code because it may be too long and contains too much noise.

- 🔄 VLM can still be used for cross-validation with crawled data based on the a11y tree.
- 🧹 LLM can still be used for data cleaning, but with much less context and thus much less cost.

---
transition: slide-up
class: text-center
layout: center
level: 2
---

# Reasoning is Crucial for Reliable AI Agents

Can reasoning models be inexpensive?

---
transition: slide-up
level: 2
---

# Reasoning Models vs. Code Generation

<div grid="~ cols-2 gap-4">
<div>
<p>Direct Reasoning</p>
<img src="/images/reasoning-models.png" alt="Reasoning Models">
</div>
<div>
<p>Generate Code to Solve the Problem</p>
<img src="/images/code-generation.png" alt="Code Generation">
</div>
</div>

---
transition: slide-up
level: 2
---

# Reasoning Models can be Small and Inexpensive

<img src="/images/rstar-math.png" alt="Reasoning is Not Hard">

<p class="text-sm opacity-75 italic">
Source: <a href="https://arxiv.org/pdf/2501.04519">rStar-Math: Small LLMs Can Master Math Reasoning with Self-Evolved Deep Thinking</a>
</p>

🧠 Reasoning will be a standard feature for all LLMs.

⚠️ LLMs without reasoning capabilities will be deprecated soon.

🚀 Reasoning capabilities will make AI coding agents truly reliable and enable autopilot in more scenarios.


---
transition: fade-out
---

# Key Takeaways

<div grid="~ cols-2 gap-4">
<div>

## AI Coding Agents
- 🔍 Context is crucial for accurate code generation
- ✅ Code review is crucial for AI-generated code
- 🎯 Single agent > multi-agent for coding tasks
- 🧪 Comprehensive testing needed before autopilot
- 🚀 4x development velocity: 50% work completed by autopilot ✖️ 50% speedup with co-pilot
- 🔄 Claude 3.5 for large codebases, o1 for new projects
- 🚀 DeepSeek V3 enables on-premise deployment
- 👥 Future: human architects + AI implementers
</div>
<div>

## RAG Agents
- 🗃️ Structured data > unstructured data for RAG
- 🏰 Domain-specific data may build moat for apps
- 🤖 VLMs can automate data collection & cleaning
- 🌳 A11y trees reduce VLM costs in web crawling
- 🎯 Domain-specific search > generic search
- 🔄 Multi-step RAG with intent analysis works better
- 🧠 Small reasoning models can be inexpensive and effective
- ⚡ Reasoning will become standard for all LLMs

</div>
</div>

<p class="italic opacity-75">
The future belongs to those who can effectively collaborate with AI agents while maintaining strategic oversight.
</p>

---
transition: fade-out
layout: center
class: text-center
---

# Thanks!

May AI Agents with you!

[Permalink of this slide deck](https://01.me/files/ai-agent-talk-202401/dist/)

<PoweredBySlidev mt-10 />
