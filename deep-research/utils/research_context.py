from typing import Dict, List, Optional
import json
import os
from datetime import datetime

class ResearchContext:
    def __init__(self, query: str, output_dir: str):
        self.query = query
        self.output_dir = output_dir
        self.start_time = datetime.now()
        self.context_file = os.path.join(output_dir, "research_context.json")
        self.sources: List[Dict] = []
        self.current_section: Optional[str] = None
        self.status = "initialized"
        
    def add_source(self, source: Dict):
        """Add a processed source to the context"""
        self.sources.append(source)
        self._save_context()
        
    def update_status(self, status: str, details: Optional[Dict] = None):
        """Update research status"""
        self.status = status
        self._save_context()
        
    def get_relevant_sources(self, section: str) -> List[Dict]:
        """Get sources relevant to a specific section"""
        # Implement relevance scoring based on section keywords
        return self.sources
        
    def _save_context(self):
        """Save current context to file"""
        context_data = {
            'query': self.query,
            'start_time': self.start_time.isoformat(),
            'status': self.status,
            'current_section': self.current_section,
            'sources_count': len(self.sources),
            'last_updated': datetime.now().isoformat()
        }
        with open(self.context_file, 'w') as f:
            json.dump(context_data, f, indent=2) 