import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import logging

class CacheManager:
    CACHE_TYPES = {
        "plans": "plans_dir",
        "crawled": "crawl_dir",
        "analyzed": "analysis_dir"
    }
    
    def __init__(self, cache_dir: str = ".cache", ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)
        self.logger = logging.getLogger(__name__)
        
        # Create cache subdirectories
        self.plans_dir = os.path.join(cache_dir, "plans")
        self.crawl_dir = os.path.join(cache_dir, "crawled")
        self.analysis_dir = os.path.join(cache_dir, "analyzed")
        
        # Create all cache directories
        for directory in [self.plans_dir, self.crawl_dir, self.analysis_dir]:
            os.makedirs(directory, exist_ok=True)
            
    def get(self, key: str, cache_type: str = "plans") -> Optional[Any]:
        """Get value from cache if it exists and is not expired"""
        if cache_type not in self.CACHE_TYPES:
            self.logger.error(f"Invalid cache type: {cache_type}")
            return None
            
        cache_file = self._get_cache_path(key, cache_type)
        if not os.path.exists(cache_file):
            return None
            
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                
            if datetime.fromisoformat(data['timestamp']) + self.ttl < datetime.now():
                os.remove(cache_file)  # Clean up expired cache
                return None
                
            self.logger.info(f"Cache hit for {cache_type}: {key}")
            return data['value']
            
        except Exception as e:
            self.logger.error(f"Error reading cache for {key}: {str(e)}")
            return None
            
    def set(self, key: str, value: Any, cache_type: str = "plans"):
        """Save value to cache with timestamp"""
        if cache_type not in self.CACHE_TYPES:
            self.logger.error(f"Invalid cache type: {cache_type}")
            return
            
        cache_file = self._get_cache_path(key, cache_type)
        data = {
            'timestamp': datetime.now().isoformat(),
            'value': value
        }
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Cached {cache_type}: {key}")
        except Exception as e:
            self.logger.error(f"Error caching {key}: {str(e)}")
            
    def _get_cache_path(self, key: str, cache_type: str) -> str:
        """Generate a file path for the cache key"""
        hash_key = hashlib.md5(key.encode()).hexdigest()
        dir_attr = self.CACHE_TYPES[cache_type]
        cache_dir = getattr(self, dir_attr)
        return os.path.join(cache_dir, f"{hash_key}.json")
        
    def get_crawled_content(self, url: str) -> Optional[Dict]:
        """Get cached webpage content"""
        return self.get(url, "crawled")
        
    def cache_crawled_content(self, url: str, content: Dict):
        """Cache webpage content"""
        self.set(url, content, "crawled")
        
    def get_analyzed_content(self, content_hash: str) -> Optional[Dict]:
        """Get cached analysis results"""
        return self.get(content_hash, "analyzed")
        
    def cache_analyzed_content(self, content_hash: str, analysis: Dict):
        """Cache analysis results"""
        self.set(content_hash, analysis, "analyzed")
        
    def clear_expired(self):
        """Clear all expired cache entries"""
        for cache_type in self.CACHE_TYPES:
            dir_attr = self.CACHE_TYPES[cache_type]
            cache_dir = getattr(self, dir_attr)
            
            for filename in os.listdir(cache_dir):
                filepath = os.path.join(cache_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    if datetime.fromisoformat(data['timestamp']) + self.ttl < datetime.now():
                        os.remove(filepath)
                        self.logger.info(f"Removed expired cache: {filename}")
                except Exception as e:
                    self.logger.error(f"Error checking cache file {filename}: {str(e)}") 