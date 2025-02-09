import yaml
from pathlib import Path

class Config:
    def __init__(self):
        self.path = Path("config.yaml")
        self.defaults = {
            "max_slides": 20,
            "tts_enabled": True,
            "voice": "alloy",
            "slide_theme": "seriph",
            "review_passes": 3,
            "figure_quality": "high"
        }
        self.load()
        
    def load(self):
        try:
            with open(self.path) as f:
                self.data = {**self.defaults, **yaml.safe_load(f)}
        except FileNotFoundError:
            self.data = self.defaults
            self.save()
            
    def save(self):
        with open(self.path, 'w') as f:
            yaml.safe_dump(self.data, f)
            
    def __getattr__(self, name):
        return self.data.get(name) 