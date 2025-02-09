import os
import time
from anthropic import Anthropic
from openai import OpenAI

class LLMClient:
    def __init__(self):
        self.config = {
            "max_retries": 3,
            "retry_delay": 1.5,
            "claude_model": "claude-3-5-sonnet-20240620",
            "gpt_model": "gpt-4-turbo-preview"
        }
        self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def process(self, prompt, system="", model="claude"):
        for attempt in range(self.config["max_retries"]):
            try:
                if model == "claude":
                    return self._call_claude(prompt, system)
                return self._call_gpt(prompt, system)
            except Exception as e:
                if attempt == self.config["max_retries"] - 1:
                    raise
                time.sleep(self.config["retry_delay"] ** (attempt + 1))
    
    def _call_claude(self, prompt, system):
        response = self.anthropic.messages.create(
            model=self.config["claude_model"],
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    
    def _call_gpt(self, prompt, system):
        response = self.openai.chat.completions.create(
            model=self.config["gpt_model"],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

class VLMClient:
    def analyze_image(self, image_bytes, prompt):
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_bytes.decode("utf-8")
                            }
                        }
                    ]
                }
            ]
        )
        return response.content[0].text 