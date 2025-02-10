from openai import OpenAI, OpenAIError
import tempfile
from typing import List, Dict, Optional
import logging
import traceback
from functools import lru_cache
from utils.api_error_handler import handle_openai_error, APIError
from utils.cache_manager import CacheManager
from utils.text_generation import TextGenerator
import hashlib
from dotenv import load_dotenv
import os

class ContentAnalyzer:
    def __init__(self, config):
        self.text_gen = TextGenerator(
            api_token=config.openai_key,
            deepseek_api_key=config.deepseek_key,
            siliconflow_key=config.siliconflow_key,
            ark_key=config.ark_key
        )
        self.vision_model = "gpt-4o"
        self.max_threads = config.max_threads
        self.logger = logging.getLogger(__name__)
        
    @classmethod
    def process_batch(cls, sources: List[Dict], api_key: str, cache_manager: Optional[CacheManager] = None, query: str = "", response_language: str = "en") -> Optional[Dict]:
        """Static method for processing a batch of sources in a separate process"""
        try:
            # Create new analyzer instance for this process
            analyzer = cls._get_process_analyzer(api_key)
            
            # Generate content hash for caching
            content_hash = analyzer._get_content_hash(sources)
            
            # Check cache
            if cache_manager:
                cached_analysis = cache_manager.get_analyzed_content(content_hash)
                if cached_analysis:
                    logging.info("Using cached analysis")
                    return cached_analysis
                    
            # Process content with query for relevance filtering
            analysis = analyzer.process_content(sources, query, response_language)
            
            # Add language information for synthesis
            analysis['response_language'] = response_language
            
            # Cache result
            if cache_manager:
                cache_manager.cache_analyzed_content(content_hash, analysis)
                
            return analysis
            
        except Exception as e:
            logging.error(f"Batch processing error: {str(e)}\n{traceback.format_exc()}")
            return None
            
    @classmethod
    @lru_cache(maxsize=None)
    def _get_process_analyzer(cls, api_key: str) -> 'ContentAnalyzer':
        """Get or create analyzer instance for this process"""
        from dataclasses import dataclass
        
        @dataclass
        class ProcessConfig:
            openai_key: str
            deepseek_key: str
            siliconflow_key: str
            ark_key: str
            max_threads: int = 1
            
        # Load environment variables for API keys
        load_dotenv()
        
        return cls(ProcessConfig(
            openai_key=api_key,
            deepseek_key=os.getenv('DEEPSEEK_API_KEY'),
            siliconflow_key=os.getenv('SILICONFLOW_API_KEY'),
            ark_key=os.getenv('ARK_API_KEY'),
            max_threads=1
        ))
        
    def _filter_irrelevant_content(self, sources: List[Dict], query: str) -> List[Dict]:
        """Filter out sources that are not relevant to the query"""
        filtered_sources = []
        for source in sources:
            # Get the content text
            content = source.get('content', {}).get('content', '') if isinstance(source.get('content'), dict) else str(source.get('content', ''))
            
            # Create relevance check prompt
            check_prompt = f"""Determine if this content is directly relevant to the query: "{query}"
            
            Content:
            {content[:1000]}  # Check first 1000 chars for efficiency
            
            Consider:
            1. Does it directly address the query topic?
            2. Is it on-topic but potentially misleading?
            3. Is it tangentially related but not useful?
            
            Output only "relevant" or "irrelevant"."""
            
            try:
                result = self.text_gen.generate_text_sync(check_prompt)
                if result["content"].lower().strip() == "relevant":
                    filtered_sources.append(source)
            except Exception as e:
                self.logger.error(f"Error checking relevance: {str(e)}")
                # Include source if relevance check fails
                filtered_sources.append(source)
                
        return filtered_sources

    def process_content(self, sources: List[Dict], query: str = "", response_language: str = "en") -> Dict:
        """Process a batch of sources"""
        try:
            # Combine all text content for batch analysis
            combined_text = "\n\n".join(
                f"Source {i+1}:\n{s.get('content', {}).get('content', '')}"  # Handle nested content
                if isinstance(s.get('content'), dict)
                else f"Source {i+1}:\n{str(s.get('content', ''))}"
                for i, s in enumerate(sources)
            )
            
            # Analyze combined text with language setting and query context
            text_analysis = self.analyze_text(combined_text, response_language, query)
            
            analysis = {
                'summary': text_analysis,
                'sources': [s['metadata'] for s in sources]
            }
            
            # Process visual content if any
            visual_analyses = []
            for source in sources:
                content = source.get('content', {})
                if isinstance(content, dict):
                    needs_visual = content.get('needs_visual', False)
                    screenshot = content.get('screenshot')
                else:
                    needs_visual = source.get('needs_visual', False)
                    screenshot = source.get('screenshot')
                    
                if needs_visual and screenshot:
                    try:
                        visual_analysis = self.analyze_visual(screenshot, response_language, query)
                        visual_analyses.append(visual_analysis)
                    except Exception as e:
                        self.logger.error(f"Error processing visual content: {str(e)}")
                        visual_analyses.append("Error analyzing visual content")
                    
            if visual_analyses:
                analysis['visual_analysis'] = "\n\n".join(visual_analyses)
                
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error in batch analysis: {str(e)}")
            raise
            
    def synthesize_findings(self, analyses: List[Dict], query_language: str = "en") -> Dict:
        """Combine multiple analyses into final results"""
        try:
            valid_analyses = [a for a in analyses if a is not None]
            if not valid_analyses:
                return {
                    'summary': "No valid analyses available",
                    'sources': []
                }
                
            synthesis_prompt = self._create_synthesis_prompt(valid_analyses, query_language)
            result = self.text_gen.generate_text_sync(synthesis_prompt)
            
            return {
                'summary': result["content"],
                'sources': [
                    source 
                    for analysis in valid_analyses 
                    for source in analysis.get('sources', [])
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error in synthesis: {str(e)}\n{traceback.format_exc()}")
            raise

    def _format_findings(self, analyses: List[Dict]) -> str:
        """Format analyzed findings for synthesis prompt"""
        formatted = []
        for i, analysis in enumerate(analyses, 1):
            # Get sources for this analysis
            sources = analysis.get('sources', [])
            source_links = [s.get('link', 'No URL') for s in sources]
            
            # Add source information
            formatted.append(f"\nAnalysis {i}:")
            formatted.append("Sources:")
            for j, link in enumerate(source_links, 1):
                formatted.append(f"  {j}. {link}")
                
            # Add text analysis
            formatted.append("\nText Analysis:")
            formatted.append(analysis.get('summary', 'No analysis available'))
            
            # Add visual analysis if available
            if 'visual_analysis' in analysis:
                formatted.append("\nVisual Analysis:")
                formatted.append(analysis['visual_analysis'])
                
        return "\n".join(formatted)
        
    def _create_synthesis_prompt(self, analyses: List[Dict], query_language: str = "en") -> str:
        """Create prompt for synthesizing multiple analyses"""
        total_sources = sum(len(analysis.get('sources', [])) for analysis in analyses)
        
        # Define language-specific templates
        templates = {
            "zh": {
                "title": "将以下研究发现综合成连贯的总结：",
                "total_analyses": "分析总数：",
                "total_sources": "来源总数：",
                "key_findings": "主要发现：",
                "requirements": [
                    "识别主要主题和模式",
                    "突出关键证据和来源",
                    "注意任何矛盾或差距",
                    "建议进一步研究的领域"
                ]
            },
            "en": {
                "title": "Synthesize the following research findings into a coherent summary:",
                "total_analyses": "Total Analyses:",
                "total_sources": "Total Sources:",
                "key_findings": "Key findings:",
                "requirements": [
                    "Identifies main themes and patterns",
                    "Highlights key evidence and sources",
                    "Notes any contradictions or gaps",
                    "Suggests areas for further research"
                ]
            }
            # Add more language templates as needed
        }
        
        # Use English template as fallback
        template = templates.get(query_language.lower()[:2], templates["en"])
        
        return f"""{template["title"]}
        
        {template["total_analyses"]} {len(analyses)}
        {template["total_sources"]} {total_sources}
        
        {template["key_findings"]}
        {self._format_findings(analyses)}
        
        {template["requirements"][0]}
        {template["requirements"][1]}
        {template["requirements"][2]}
        {template["requirements"][3]}"""
        
    def analyze_text(self, content: str, language: str = "en", query: str = "") -> str:
        """Analyze text content with error handling"""
        try:
            # Define language-specific prompts
            prompts = {
                "zh": f"""分析并总结以下内容，重点关注与查询相关的信息：

查询：{query}

内容：
{content[:3000]}

请提供一个全面的总结，包括：
1. 与查询最相关的主要观点和论述
2. 重要的支持数据和证据
3. 关键结论和发现
4. 潜在的影响和意义

注意：
- 重点关注与查询直接相关的内容
- 简要提及相关的背景信息
- 忽略无关内容，但不要完全过滤掉可能有用的信息""",

                "en": f"""Analyze and summarize the following content, focusing on information relevant to the query:

Query: {query}

Content:
{content[:3000]}

Provide a comprehensive summary that includes:
1. Main points and arguments most relevant to the query
2. Important supporting data and evidence
3. Key conclusions and findings
4. Potential implications and significance

Note:
- Focus on content directly relevant to the query
- Briefly mention relevant background information
- Ignore irrelevant content but don't completely filter out potentially useful information"""
            }
            
            # Use appropriate prompt based on language
            prompt = prompts.get(language.lower()[:2], prompts["en"])
            result = self.text_gen.generate_text_sync(prompt)
            return result["content"]
        except Exception as e:
            self.logger.error(f"Error in text analysis: {str(e)}\n{traceback.format_exc()}")
            raise
            
    def analyze_visual(self, screenshot_data: str, language: str = "en", query: str = "") -> str:
        """Analyze visual content with error handling"""
        try:
            # Check if data is already base64
            if isinstance(screenshot_data, str) and screenshot_data.startswith('iVBOR'):
                image_data = screenshot_data
            else:
                # Read file if path provided
                with open(screenshot_data, "rb") as img_file:
                    image_data = img_file.read().hex()
            
            # Define language-specific prompts
            prompts = {
                "zh": f"""详细描述并分析这张截图的内容，重点关注与查询相关的信息：

查询：{query}

请分析以下方面：
1. 描述与查询相关的主要视觉元素
2. 解释重要的信息和数据
3. 分析图片对理解查询主题的价值
4. 指出任何支持或补充查询的细节""",

                "en": f"""Describe and analyze this screenshot in detail, focusing on information relevant to the query:

Query: {query}

Please analyze:
1. Describe main visual elements relevant to the query
2. Explain key information and data
3. Analyze the image's value for understanding the query topic
4. Point out any details that support or complement the query"""
            }
            
            # Use appropriate prompt based on language
            prompt = prompts.get(language.lower()[:2], prompts["en"])
            result = self.text_gen.generate_text_sync(prompt, image_data=image_data)
            return result["content"]
            
        except Exception as e:
            self.logger.error(f"Error analyzing visual content: {str(e)}\n{traceback.format_exc()}")
            error_messages = {
                "zh": "分析视觉内容时出错",
                "en": "Error analyzing visual content"
            }
            return error_messages.get(language.lower()[:2], error_messages["en"])

    def _get_content_hash(self, sources: List[Dict]) -> str:
        """Generate a hash of the source contents for caching"""
        content_str = "".join(
            source.get('content', {}).get('content', '')  # Handle nested content structure
            if isinstance(source.get('content'), dict)
            else str(source.get('content', ''))
            for source in sources
        )
        return hashlib.md5(content_str.encode()).hexdigest() 