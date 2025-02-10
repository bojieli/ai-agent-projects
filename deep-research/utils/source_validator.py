import re
from urllib.parse import urlparse
from typing import Dict, List

class SourceValidator:
    def __init__(self):
        self.academic_domains = {'.edu', '.ac.uk', '.gov'}
        self.blocked_domains = {'pinterest.com', 'facebook.com', 'twitter.com'}
        
    def validate_source(self, url: str) -> Dict:
        """Validate source quality and type"""
        parsed = urlparse(url)
        domain = parsed.netloc
        
        return {
            'url': url,
            'is_academic': self._is_academic(domain),
            'is_blocked': self._is_blocked(domain),
            'quality_score': self._calculate_quality_score(url, domain),
            'source_type': self._determine_source_type(url, domain)
        }
        
    def _is_academic(self, domain: str) -> bool:
        return any(domain.endswith(d) for d in self.academic_domains)
        
    def _is_blocked(self, domain: str) -> bool:
        return any(b in domain for b in self.blocked_domains)
        
    def _calculate_quality_score(self, url: str, domain: str) -> float:
        score = 0.0
        if self._is_academic(domain):
            score += 0.4
        if 'https' in url:
            score += 0.1
        if re.search(r'\d{4}', url):  # Has year in URL
            score += 0.2
        return min(1.0, score)
        
    def _determine_source_type(self, url: str, domain: str) -> str:
        if self._is_academic(domain):
            return 'academic'
        if re.search(r'news|article|blog', url):
            return 'article'
        if '.gov' in domain:
            return 'government'
        return 'other' 