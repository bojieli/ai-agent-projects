import requests
from typing import List, Dict
from urllib.parse import urlencode
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

class GoogleSearchClient:
    def __init__(self, api_key: str, engine_id: str):
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.params = {
            "key": api_key,
            "cx": engine_id,
            "num": 10  # Results per page
        }
        self.logger = logging.getLogger(__name__)
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def search(self, query: str, start_index: int = 1) -> List[Dict]:
        """Execute Google Custom Search with retry logic"""
        try:
            params = {
                **self.params,
                "q": query,
                "start": start_index
            }
            response = requests.get(f"{self.base_url}?{urlencode(params)}")
            response.raise_for_status()
            return self._parse_results(response.json())
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Search failed for query '{query}': {str(e)}")
            raise
            
    def search_all(self, query: str, max_results: int = 30) -> List[Dict]:
        """Get multiple pages of search results"""
        all_results = []
        start_index = 1
        
        while len(all_results) < max_results:
            results = self.search(query, start_index)
            if not results:
                break
                
            all_results.extend(results)
            start_index += len(results)
            
        return all_results[:max_results]
        
    def _parse_results(self, data: Dict) -> List[Dict]:
        """Parse Google Search API response"""
        if 'items' not in data:
            return []
            
        return [{
            'title': item.get('title', ''),
            'link': item.get('link', ''),
            'snippet': item.get('snippet', ''),
            'source_type': self._determine_source_type(item),
            'date': item.get('pagemap', {}).get('metatags', [{}])[0].get('article:published_time')
        } for item in data['items']]
        
    def _determine_source_type(self, item: Dict) -> str:
        """Determine the type of source based on URL and metadata"""
        url = item.get('link', '').lower()
        
        if any(domain in url for domain in ['.edu', '.ac.']):
            return 'academic'
        elif any(domain in url for domain in ['.gov', '.org']):
            return 'official'
        elif 'arxiv.org' in url or 'doi.org' in url:
            return 'research_paper'
        elif any(domain in url for domain in ['news', 'article', 'blog']):
            return 'article'
        return 'other' 