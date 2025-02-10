# Deep Research Agent

Autonomous AI agent for conducting in-depth research through multi-modal analysis and iterative report generation.

## Features
- **Intelligent Planning**  
  Uses OpenAI o3-mini to analyze research queries and generate execution plans
- **Multi-source Data Collection**
  - Google Search API integration for initial source discovery
  - Selenium-based web crawler with headless Chrome for dynamic content
  - Automatic content extraction to structured markdown
- **Multi-modal Analysis**
  - Text analysis using o3-mini for content summarization and synthesis
  - Visual analysis using OpenAI o3-mini for screenshot understanding
  - Automatic detection of tables/figures requiring visual parsing
- **Iterative Report Generation**
  - Outline-first approach with AI-generated structure
  - Section-by-section content development
  - Built-in fact verification and source citation

## Workflow
1. **Query Analysis**  
   LLM parses research objectives and success criteria
2. **Plan Generation**  
   Creates step-by-step execution plan with source targets
3. **Content Gathering**  
   Parallelized web crawling with automatic quality filtering
4. **Multi-modal Analysis**  
   Combined text and visual understanding pipeline
5. **Report Structuring**  
   Generates hierarchical outline with weighted section priorities
6. **Iterative Generation**  
   Section-by-section writing with context-aware LLM prompts

## Technologies
- OpenAI API (o3-mini, o3-mini)
- Google Custom Search JSON API
- Selenium WebDriver (Chrome)
- Beautiful Soup 4 (HTML processing)
- Pillow (Screenshot analysis)

## Prerequisites
- OpenAI API key
- Google Programmable Search Engine ID & API key
- ChromeDriver installed
- Python 3.8+

## Setup

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API keys:
- Get OpenAI API key from: https://platform.openai.com/account/api-keys
- Get Google API key from: https://console.cloud.google.com/apis/credentials
- Create Search Engine ID at: https://programmablesearchengine.google.com/

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python research_agent.py --query "Impact of quantum computing on asymmetric cryptography" --output-dir ./reports
```

## Configuration
Set environment variables in `.env`:
```ini
OPENAI_API_KEY=sk-your-key
GOOGLE_API_KEY=your-google-key
SEARCH_ENGINE_ID=your-engine-id
MAX_CONCURRENT_THREADS=5
LLM_TEMPERATURE=0.3
```
