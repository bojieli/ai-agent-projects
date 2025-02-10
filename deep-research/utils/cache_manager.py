import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional

class CacheManager:
    def __init__(self, cache_dir: str = ".cache", ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)
        os.makedirs(cache_dir, exist_ok=True)
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if it exists and is not expired"""
        cache_file = self._get_cache_path(key)
        if not os.path.exists(cache_file):
            return None
            
        with open(cache_file, 'r') as f:
            data = json.load(f)
            
        if datetime.fromisoformat(data['timestamp']) + self.ttl < datetime.now():
            os.remove(cache_file)  # Clean up expired cache
            return None
            
        return data['value']
        
    def set(self, key: str, value: Any):
        """Save value to cache with timestamp"""
        cache_file = self._get_cache_path(key)
        data = {
            'timestamp': datetime.now().isoformat(),
            'value': value
        }
        with open(cache_file, 'w') as f:
            json.dump(data, f)
            
    def _get_cache_path(self, key: str) -> str:
        """Generate a file path for the cache key"""
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_key}.json") 