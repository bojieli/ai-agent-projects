from openai import OpenAI, OpenAIError
import tempfile
from typing import List, Dict, Optional
import logging
from functools import lru_cache
from utils.api_error_handler import handle_openai_error, APIError

class ContentAnalyzer:
    def __init__(self, config):
        self.client = OpenAI(api_key=config.openai_key)
        self.vision_model = "o3-mini"
        self.max_threads = config.max_threads
        self.logger = logging.getLogger(__name__)
        
    @classmethod
    def process_batch(cls, sources: List[Dict], api_key: str) -> Optional[Dict]:
        """Static method for processing a batch of sources in a separate process"""
        try:
            # Create new analyzer instance for this process
            analyzer = cls._get_process_analyzer(api_key)
            return analyzer.process_content(sources)
        except Exception as e:
            logging.error(f"Batch processing error: {str(e)}")
            return None
            
    @classmethod
    @lru_cache(maxsize=None)
    def _get_process_analyzer(cls, api_key: str) -> 'ContentAnalyzer':
        """Get or create analyzer instance for this process"""
        from dataclasses import dataclass
        
        @dataclass
        class ProcessConfig:
            openai_key: str
            max_threads: int = 1
            
        return cls(ProcessConfig(openai_key=api_key))
        
    def process_content(self, sources: List[Dict]) -> Dict:
        """Process a batch of sources"""
        try:
            # Combine all text content for batch analysis
            combined_text = "\n\n".join(
                f"Source {i+1}:\n{s['content']}" 
                for i, s in enumerate(sources)
            )
            
            # Analyze combined text
            text_analysis = self.analyze_text(combined_text)
            
            analysis = {
                'summary': text_analysis,
                'sources': [s['metadata'] for s in sources]
            }
            
            # Process visual content if any
            visual_analyses = []
            for source in sources:
                if source.get('needs_visual') and source.get('screenshot'):
                    visual_analysis = self.analyze_visual(source['screenshot'])
                    visual_analyses.append(visual_analysis)
                    
            if visual_analyses:
                analysis['visual_analysis'] = "\n\n".join(visual_analyses)
                
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error in batch analysis: {str(e)}")
            raise
            
    def synthesize_findings(self, analyses: List[Dict]) -> Dict:
        """Combine multiple analyses into final results"""
        valid_analyses = [a for a in analyses if a is not None]
        synthesis_prompt = self._create_synthesis_prompt(valid_analyses)
        
        response = self.client.chat.completions.create(
            model="o3-mini",
            messages=[{"role": "user", "content": synthesis_prompt}]
        )
        
        return {
            'summary': response.choices[0].message.content,
            'sources': [source for analysis in valid_analyses for source in analysis['sources']]
        }

    def _create_synthesis_prompt(self, analyses: List[Dict]) -> str:
        return f"""Synthesize the following research findings into a coherent summary:
        
        Sources analyzed: {len(analyses)}
        
        Key findings:
        {self._format_findings(analyses)}
        
        Create a comprehensive summary that:
        1. Identifies main themes and patterns
        2. Highlights key evidence and sources
        3. Notes any contradictions or gaps
        4. Suggests areas for further research"""
        
    def _format_findings(self, analyses: List[Dict]) -> str:
        """Format analyzed findings for synthesis prompt"""
        formatted = []
        for i, analysis in enumerate(analyses, 1):
            formatted.append(f"\nSource {i}: {analysis['url']}")
            formatted.append("Text Analysis:")
            formatted.append(analysis['text_analysis'])
            
            if 'visual_analysis' in analysis:
                formatted.append("\nVisual Analysis:")
                formatted.append(analysis['visual_analysis'])
                
        return "\n".join(formatted)
        
    def analyze_text(self, content: str) -> str:
        """Analyze text content with error handling"""
        try:
            response = self.client.chat.completions.create(
                model="o3-mini",
                messages=[{
                    "role": "user",
                    "content": f"Analyze and summarize this content:\n{content[:3000]}"
                }]
            )
            return response.choices[0].message.content
            
        except OpenAIError as e:
            raise handle_openai_error(e)
            
    def analyze_visual(self, screenshot_path: str) -> str:
        """Analyze visual content with error handling"""
        try:
            with open(screenshot_path, "rb") as img_file:
                response = self.client.chat.completions.create(
                    model=self.vision_model,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe and analyze this screenshot"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_file.read().hex()}"}}
                        ]
                    }]
                )
            return response.choices[0].message.content
            
        except OpenAIError as e:
            raise handle_openai_error(e) 