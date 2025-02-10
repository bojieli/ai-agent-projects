import json
import os
from typing import Dict, Optional
from datetime import datetime

class RecoveryManager:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.checkpoint_file = os.path.join(output_dir, "checkpoint.json")
        
    def save_checkpoint(self, state: Dict):
        """Save current execution state"""
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'state': state
        }
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
            
    def load_checkpoint(self) -> Optional[Dict]:
        """Load last saved checkpoint if exists"""
        if not os.path.exists(self.checkpoint_file):
            return None
            
        with open(self.checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
        return checkpoint['state']
        
    def clear_checkpoint(self):
        """Clear checkpoint after successful completion"""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file) 