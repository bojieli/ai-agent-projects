from bs4 import BeautifulSoup

class AccessibilityChecker:
    def check_slide(self, slide_md):
        """Validate accessibility standards"""
        soup = BeautifulSoup(slide_md, 'html.parser')
        report = {
            'alt_text_missing': [],
            'low_contrast': [],
            'heading_errors': []
        }
        
        # Check images
        for img in soup.find_all('img'):
            if not img.get('alt'):
                report['alt_text_missing'].append(img['src'])
        
        # Check heading hierarchy
        headings = [int(tag.name[1]) for tag in soup.find_all(re.compile('^h[1-6]$'))]
        if headings != sorted(headings):
            report['heading_errors'] = headings
            
        return report
    
    def generate_alt_text(self, figure):
        """Generate alt-text using VLM"""
        prompt = f"""Describe this figure for visually impaired users:
        Caption: {figure['caption']}
        Analysis: {figure['analysis']}"""
        return self.vlm.process(prompt)

    def add_aria_labels(self, slide_md):
        """Inject ARIA attributes for screen readers"""
        soup = BeautifulSoup(slide_md, 'html.parser')
        
        # Add aria-live regions for dynamic content
        for element in soup.find_all(class_='animate-pulse'):
            element['aria-live'] = 'polite'
        
        return str(soup) 