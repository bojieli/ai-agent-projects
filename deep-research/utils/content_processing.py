import re
from markdown import markdown
import markdownify
from bs4 import BeautifulSoup
from typing import Optional

def html_to_markdown(html: str) -> str:
    """Convert HTML to markdown with custom options"""
    return markdownify.markdownify(
        html,
        heading_style="ATX",
        bullets="-",
        strip=["script", "style", "form"]
    )

def needs_visual_analysis(content: str) -> bool:
    """Determine if content needs visual analysis"""
    # Convert to lowercase for case-insensitive matching
    content_lower = content.lower()
    
    # Keywords indicating visual content
    visual_indicators = [
        "table", "graph", "chart", "diagram", "figure",
        "visualization", "plot", "image", "illustration"
    ]
    
    return any(indicator in content_lower for indicator in visual_indicators) 