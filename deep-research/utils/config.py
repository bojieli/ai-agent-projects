import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    openai_key: str
    google_key: str
    search_engine_id: str
    output_dir: str
    cache_dir: str
    max_threads: int
    llm_temperature: float
    crawl_timeout: int

    @classmethod
    def from_env(cls) -> 'Config':
        """Create config from environment variables"""
        load_dotenv()
        
        return cls(
            openai_key=os.getenv('OPENAI_API_KEY'),
            google_key=os.getenv('GOOGLE_API_KEY'),
            search_engine_id=os.getenv('SEARCH_ENGINE_ID'),
            output_dir=os.getenv('OUTPUT_DIR', './reports'),
            cache_dir=os.getenv('CACHE_DIR', './.cache'),
            max_threads=int(os.getenv('MAX_CONCURRENT_THREADS', '5')),
            llm_temperature=float(os.getenv('LLM_TEMPERATURE', '0.3')),
            crawl_timeout=int(os.getenv('CRAWL_TIMEOUT', '30'))
        )

    def validate(self) -> None:
        """Validate required configuration"""
        required = {
            'OPENAI_API_KEY': self.openai_key,
            'GOOGLE_API_KEY': self.google_key,
            'SEARCH_ENGINE_ID': self.search_engine_id
        }
        
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

def load_config():
    return Config.from_env() 