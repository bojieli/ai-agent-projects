from jinja2 import Environment, FileSystemLoader
import json

class SlideGenerator:
    def __init__(self, template_dir="templates"):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,
            undefined=StrictUndefined
        )
        self._verify_templates()
        self.slide_count = 0
        
    def _verify_templates(self):
        """Ensure required templates exist"""
        required_templates = [
            'title.md', 
            'summary.md',
            'technical.md',
            'results.md'
        ]
        
        for tpl in required_templates:
            if not self.env.loader.exists(tpl):
                raise MissingTemplateError(f"Required template {tpl} missing")
        
    def generate_slides(self, paper_data, figures):
        """Generate Slidev markdown from structured content"""
        slides = []
        
        # Title slide
        slides.append(self._render_template("title.md", {
            "title": paper_data['metadata']['title'],
            "authors": paper_data['metadata']['authors'],
            "venue": paper_data['metadata']['venue']
        }))
        
        # Summary slide
        slides.append(self._render_template("summary.md", {
            "key_points": paper_data['summary']['key_points'],
            "main_figure": figures[0]['analysis']
        }))
        
        # Technical approach
        slides.append(self._render_template("technical.md", {
            "sections": paper_data['sections'],
            "figures": figures
        }))
        
        return "\n\n".join(slides)
    
    def _render_template(self, template_name, context):
        """Render a slide template with context"""
        template = self.env.get_template(template_name)
        return template.render(context)
    
    def add_speaker_notes(self, slide_md, notes):
        """Add TTS-ready speaker notes to slides"""
        return slide_md + f"\n\n<!--\nSPEAKER: {notes}\n-->"

    def estimate_timing(self, slide_content):
        """Estimate optimal slide duration"""
        prompt = f"""Estimate presentation timing for this slide:
        {slide_content}
        
        Consider:
        - Text complexity
        - Figure explanation needs
        - Transition type
        - Speaker note markers"""
        return self.llm.process(prompt)

class SlideReviewAgent:
    def __init__(self, llm_client):
        self.llm = llm_client
        
    def review_slide(self, slide_content, paper_context):
        """Review a single slide for quality and accuracy"""
        prompt = f"""
        Review this presentation slide based on the original paper:
        
        Paper Context: {paper_context}
        
        Slide Content: {slide_content}
        
        Check for:
        1. Technical accuracy
        2. Proper citations
        3. Clear visual hierarchy
        4. Appropriate pacing
        """
        return self.llm.generate(prompt)

    def full_review(self, slides, paper_data):
        """Comprehensive multi-pass review"""
        reviewed_slides = []
        
        # First pass: Individual slide review
        for i, slide in enumerate(slides):
            reviewed = self.review_slide(slide, paper_data)
            reviewed_slides.append(self.apply_fixes(reviewed))
        
        # Second pass: Flow analysis
        flow_report = self.analyze_flow(reviewed_slides)
        reviewed_slides = self.adjust_transitions(reviewed_slides, flow_report)
        
        # Final pass: Accessibility check
        return self.check_accessibility(reviewed_slides)

    def analyze_flow(self, slides):
        """Analyze narrative flow between slides"""
        prompt = f"""Analyze presentation flow:
        
        Slides: {json.dumps(slides)}
        
        Identify:
        1. Logical gaps between slides
        2. Repetitive content
        3. Optimal transition types
        4. Timing adjustments"""
        
        return self.llm.generate(prompt)

    def check_accessibility(self, slides):
        """Ensure accessibility standards"""
        prompt = f"""Check accessibility:
        
        Slides: {json.dumps(slides)}
        
        Verify:
        1. Alt-text for all images
        2. Proper heading hierarchy
        3. Color contrast ratios
        4. Screen reader compatibility"""
        
        return self.llm.generate(prompt)

    def apply_fixes(self, slide, issues):
        """Automatically fix common slide issues"""
        prompt = f"""Fix these slide issues:
        {issues}
        
        Original Slide:
        {slide}
        
        Required Fixes:
        1. Condense bullet points >3 levels deep
        2. Reposition overlapping elements
        3. Simplify complex equations
        4. Add missing alt-text"""
        return self.llm.process(prompt)

    def optimize_transitions(self, slides, flow_report):
        """Apply transition optimizations based on flow analysis"""
        prompt = f"""Optimize slide transitions:
        {flow_report}
        
        Slides: {json.dumps(slides)}
        
        Guidelines:
        1. Use 'slide-up' for hierarchical progression
        2. Use 'fade' for topic changes
        3. Use 'zoom' for technical details"""
        return json.loads(self.llm.process(prompt))

class FinalReviewAgent:
    def __init__(self, llm_client):
        self.llm = llm_client
        
    def conduct_final_review(self, slides):
        """Perform comprehensive final review"""
        checks = [
            self._check_academic_integrity,
            self._verify_disclosures,
            self._validate_citations,
            self._check_accessibility
        ]
        
        for check in checks:
            slides = check(slides)
            
        return slides
    
    def _check_academic_integrity(self, slides):
        prompt = f"""Verify academic integrity in slides:
        
        {slides}
        
        Check for:
        1. Proper credit to prior work
        2. No misleading claims
        3. Clear differentiation between original and cited work
        """
        return self._apply_llm_fixes(slides, prompt)
    
    def _verify_disclosures(self, slides):
        prompt = """Check for required disclosures:
        1. Funding sources
        2. Competing interests
        3. Data availability
        4. Ethical approvals
        """
        return self._apply_llm_fixes(slides, prompt)

class MissingTemplateError(Exception):
    """Error for missing slide templates""" 