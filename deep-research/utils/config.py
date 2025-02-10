import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    openai_key: str
    google_key: str
    search_engine_id: str
    deepseek_key: str
    siliconflow_key: str
    ark_key: str
    output_dir: str
    cache_dir: str
    max_threads: int
    crawl_timeout: int

    @classmethod
    def from_env(cls) -> 'Config':
        """Create config from environment variables"""
        load_dotenv()
        
        return cls(
            openai_key=os.getenv('OPENAI_API_KEY'),
            google_key=os.getenv('GOOGLE_API_KEY'),
            search_engine_id=os.getenv('SEARCH_ENGINE_ID'),
            deepseek_key=os.getenv('DEEPSEEK_API_KEY'),
            siliconflow_key=os.getenv('SILICONFLOW_API_KEY'),
            ark_key=os.getenv('ARK_API_KEY'),
            output_dir=os.getenv('OUTPUT_DIR', './reports'),
            cache_dir=os.getenv('CACHE_DIR', './.cache'),
            max_threads=int(os.getenv('MAX_CONCURRENT_THREADS', '5')),
            crawl_timeout=int(os.getenv('CRAWL_TIMEOUT', '30'))
        )

    def validate(self) -> None:
        """Validate required configuration"""
        required = {
            'OPENAI_API_KEY': self.openai_key,
            'GOOGLE_API_KEY': self.google_key,
            'SEARCH_ENGINE_ID': self.search_engine_id,
            'DEEPSEEK_API_KEY': self.deepseek_key,
            'SILICONFLOW_API_KEY': self.siliconflow_key,
            'ARK_API_KEY': self.ark_key
        }
        
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

def load_config():
    return Config.from_env() 