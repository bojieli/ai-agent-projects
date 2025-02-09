from .error_handling import validate_input

class AcademicStyleEnforcer:
    def __init__(self, config):
        self.config = config
        self.citation_style = "APA"
        
    @validate_input('slides', 'paper_data')
    def enforce(self, slides, paper_data):
        """Apply academic style rules to slides"""
        slides = self._enforce_citations(slides, paper_data['references'])
        slides = self._preserve_equations(slides)
        slides = self._format_algorithms(slides)
        return self._control_length(slides)

    def _enforce_citations(self, slides, references):
        """Ensure proper citation formatting"""
        for i, slide in enumerate(slides):
            for ref in references:
                if ref['id'] in slide:
                    slides[i] = slide.replace(
                        ref['id'], 
                        self._format_citation(ref)
                    )
        return slides
    
    def _format_citation(self, ref):
        """Format citation based on selected style"""
        if self.citation_style == "APA":
            return f"{ref['authors'][0]} et al. ({ref['year']})"
        return f"[{ref['id']}]"

    def _preserve_equations(self, slides):
        """Maintain equation numbering from paper"""
        equation_count = 1
        for i, slide in enumerate(slides):
            slides[i] = re.sub(
                r'\\begin{equation}',
                f'\\begin{equation}} ({equation_count})',
                slide
            )
            equation_count += slide.count(r'\begin{equation}')
        return slides

    def _format_algorithms(self, slides):
        """Format algorithm pseudocode"""
        for i, slide in enumerate(slides):
            if '```algorithm' in slide:
                slides[i] = self._format_algorithm_block(slide)
        return slides

    def _format_algorithm_block(self, content):
        """Format algorithm pseudocode block"""
        prompt = f"""Format this algorithm for slides:
        {content}
        
        Requirements:
        1. Add line numbers
        2. Highlight key lines
        3. Add time complexity annotation"""
        return self.llm.process(prompt)

    def _control_length(self, slides):
        """Enforce slide count limits"""
        max_slides = self.config.max_slides
        return slides[:max_slides] + [
            f"\n<!-- Removed {len(slides)-max_slides} slides to meet limit -->"
        ]

    def load_citation_template(self, style):
        """Load citation format from template"""
        templates = {
            "APA": "{author_et_al} ({year})",
            "IEEE": "[{ref_number}]",
            "Nature": "({author_short}, {year})"
        }
        return templates.get(style, "APA") 