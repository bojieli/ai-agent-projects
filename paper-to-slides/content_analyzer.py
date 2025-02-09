from .error_handling import retry

class ContentAnalyzer:
    def __init__(self, llm_client, vlm_client):
        self.llm = llm_client
        self.vlm = vlm_client
        
    @retry(max_retries=3)
    def analyze_paper_structure(self, paper_text):
        """Analyze paper structure using VLM layout understanding"""
        prompt = f"""Analyze this academic paper's structure:
        
        {paper_text[:10000]}
        
        Return JSON with:
        - section_breakdown (list of sections with type/content)
        - key_diagrams (list of important figures)
        - technical_components (equations/algorithms)
        """
        return self.llm.process(prompt)
    
    def create_narrative_flow(self, analysis):
        """Create presentation narrative flow"""
        prompt = f"""Create presentation flow from analysis:
        
        {json.dumps(analysis)}
        
        Output format:
        - slide_sequence (ordered list of slide topics)
        - transition_types (between slides)
        - hierarchy (main vs subsidiary points)
        """
        return self.llm.process(prompt)

class LayoutAnalyzer:
    def detect_special_components(self, page_image):
        """Detect equations, algorithms, proofs using VLM"""
        prompt = "Identify technical components in this paper page image"
        return self.vlm.analyze_image(page_image, prompt) 