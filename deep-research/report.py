from openai import OpenAI
import os
from typing import Dict, List
import json
from datetime import datetime
from utils.text_generation import TextGenerator

class ReportGenerator:
    def __init__(self, config):
        self.text_gen = TextGenerator(
            api_token=config.openai_key,
            deepseek_api_key=config.deepseek_key,
            siliconflow_key=config.siliconflow_key,
            ark_key=config.ark_key
        )
        
    def generate_report(self, analyzed_data: Dict, output_path: str):
        """Generate full research report with progress tracking"""
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate outline
        outline = self.generate_outline(analyzed_data)
        sections = outline['sections']
        
        # Create progress file
        progress_file = os.path.join(output_dir, 'progress.json')
        self._init_progress(progress_file, sections)
        
        # Generate each section
        report_content = []
        for section in sections:
            content = self.write_section(section, analyzed_data)
            report_content.append(content)
            self._update_progress(progress_file, section['title'])
            
        # Combine and save final report
        final_report = self._combine_sections(report_content)
        self._save_report(final_report, output_path)
        
    def _init_progress(self, progress_file: str, sections: List[Dict]):
        progress = {
            'start_time': datetime.now().isoformat(),
            'sections': {s['title']: {'status': 'pending'} for s in sections}
        }
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
            
    def _update_progress(self, progress_file: str, section_title: str):
        with open(progress_file, 'r') as f:
            progress = json.load(f)
        progress['sections'][section_title]['status'] = 'completed'
        progress['sections'][section_title]['completed_at'] = datetime.now().isoformat()
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
            
    def _combine_sections(self, sections: List[str]) -> str:
        return "\n\n".join(sections)
        
    def _save_report(self, content: str, output_path: str):
        """Save the report content to the specified path"""
        with open(output_path, 'w') as f:
            f.write(content)
        
    def generate_outline(self, research_data: Dict) -> Dict:
        """Generate report outline from research data"""
        prompt = f"""Create a detailed outline for a research report based on these findings:

Summary: {research_data['summary']}

Available sources: {len(research_data['sources'])}

Generate an outline with:
1. Executive Summary
2. Introduction
3. Main sections covering key themes
4. Methodology
5. Findings and Analysis
6. Conclusions
7. References

Output as JSON with structure:
{{
    "sections": [
        {{"title": "section_title", "content_prompt": "specific guidance for section"}}
    ]
}}"""
        
        response = self._get_completion(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            raise ValueError("Failed to generate valid outline structure")
        
    def write_section(self, section, context):
        prompt = f"""Write the '{section}' section using this context:
        {context}
        Use academic tone with proper citations."""
        
        return self._get_completion(prompt)
        
    def _get_completion(self, prompt: str) -> str:
        """Get completion using DeepSeek-R1"""
        try:
            result = self.text_gen.generate_text_sync(prompt)
            return result["content"]
        except Exception as e:
            raise ValueError(f"Text generation failed: {str(e)}") 