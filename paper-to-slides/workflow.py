from .pdf_processor import TextExtractionAgent, FigureExtractionAgent
from .slide_generator import SlideGenerator, SlideReviewAgent
from .tts_integration import TTSAgent
from .llm_integration import LLMClient, VLMClient
from .style_enforcer import AcademicStyleEnforcer
from .content_analyzer import ContentAnalyzer, LayoutAnalyzer
from .compliance_verifier import ComplianceVerifier

class PaperToSlides:
    def __init__(self, config):
        self.llm = LLMClient()
        self.vlm = VLMClient()
        self.config = config
        
    def process(self, pdf_path):
        # Phase 1: Content Extraction
        text_agent = TextExtractionAgent(pdf_path)
        text_agent.llm_client = self.llm
        paper_text = text_agent.extract_text()
        metadata = text_agent.extract_metadata()
        
        figure_agent = FigureExtractionAgent(pdf_path)
        figures = figure_agent.extract_figures()
        
        # Phase 2: Content Analysis
        layout_analyzer = LayoutAnalyzer()
        layout_report = layout_analyzer.detect_special_components(pdf_path)
        
        content_analyzer = ContentAnalyzer(self.llm, self.vlm)
        structure = content_analyzer.analyze_paper_structure(paper_text)
        narrative_flow = content_analyzer.create_narrative_flow(structure)
        
        analyzed_data = self._analyze_content(paper_text, figures)
        
        # Phase 3: Slide Generation
        generator = SlideGenerator()
        slides = generator.generate_slides(
            analyzed_data, 
            figures,
            narrative=narrative_flow
        )
        
        # Phase 4: Review & Enhancement
        reviewer = SlideReviewAgent(self.llm)
        reviewed_slides = reviewer.full_review(slides, paper_text)
        
        # Phase 5: TTS Integration
        if self.config['tts_enabled']:
            tts = TTSAgent(os.getenv("OPENAI_API_KEY"))
            self._add_audio(reviewed_slides, tts)
            
        # Phase 6: Academic Style Enforcement
        enforcer = AcademicStyleEnforcer(self.config)
        final_slides = enforcer.enforce(reviewed_slides, analyzed_data)
        
        # Add final compliance check
        compliance_checker = ComplianceVerifier()
        final_slides = compliance_checker.verify(final_slides)
        
        return final_slides
    
    def _analyze_content(self, paper_text, figures):
        analysis_prompt = f"""Analyze this academic paper content:
        
        {paper_text}
        
        Extract:
        1. 3-5 key contributions
        2. Technical novelty
        3. Experimental results summary
        4. Critical limitations
        """
        return json.loads(self.llm.process(analysis_prompt))
    
    def _add_audio(self, slides, tts):
        for i, slide in enumerate(slides):
            if '<!--\nSPEAKER:' in slide:
                notes = slide.split('<!--\nSPEAKER:')[1].split('\n-->')[0]
                audio_path = tts.generate_audio(notes, i+1)
                slides[i] = f"{slide}\n<audio src=\"{audio_path}\" />"

    def validate_extracted_content(self, paper_data, figures):
        """Quality check before slide generation"""
        required_elements = {
            'title': paper_data['metadata'].get('title'),
            'abstract': paper_data.get('abstract'),
            'key_points': paper_data['summary'].get('key_points'),
            'figures': len(figures) > 0
        }
        
        missing = [k for k,v in required_elements.items() if not v]
        if missing:
            raise ContentValidationError(
                f"Missing critical elements: {', '.join(missing)}"
            )
        
        return self._enhance_metadata(paper_data)

class ContentValidationError(Exception):
    """Specialized error for content validation""" 