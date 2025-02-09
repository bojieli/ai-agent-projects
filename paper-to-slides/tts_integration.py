from openai import OpenAI
import os
import re

class TTSAgent:
    def __init__(self, api_key, voice="alloy", speed=1.0):
        self.client = OpenAI(api_key=api_key)
        self.voice = voice
        self.speed = speed
        self.audio_dir = "audio"
        
        os.makedirs(self.audio_dir, exist_ok=True)
        
    def generate_audio(self, text, slide_number):
        """Generate TTS audio for speaker notes"""
        response = self.client.audio.speech.create(
            model="tts-1",
            voice=self.voice,
            input=self._clean_notes(text),
            speed=self._calculate_speed(text)
        )
        
        filename = f"slide_{slide_number}.mp3"
        path = os.path.join(self.audio_dir, filename)
        response.stream_to_file(path)
        
        return path
    
    def _clean_notes(self, text):
        """Preserve pacing markers while removing control codes"""
        return re.sub(
            r'\[(pause|speed|emphasis)=([^\]]+)\]',
            lambda m: f'<{m.group(1)} {m.group(2)}>',
            text
        )
    
    def _calculate_speed(self, text):
        """More nuanced speed calculation"""
        speed_factors = {
            'equation': 0.9,
            'citation': 1.1,
            'bullet_list': 1.05,
            'figure': 0.95
        }
        
        base_speed = self.speed
        for pattern, factor in speed_factors.items():
            if re.search(rf'\[{pattern}\]', text):
                base_speed *= factor
            
        return min(max(base_speed, 0.8), 1.5) 