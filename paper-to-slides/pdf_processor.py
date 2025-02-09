import fitz  # PyMuPDF
import pdfplumber
import re
import json
from PIL import Image
import io
import cv2
import numpy as np

class TextExtractionAgent:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.metadata = {}
        
    def extract_text(self):
        """Extract structured text with self-correction mechanism"""
        text_blocks = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # Extract text with layout preservation
                text = page.extract_text(x_tolerance=1, y_tolerance=3)
                if not text:
                    # Fallback to PyMuPDF for problematic pages
                    text = self.doc.load_page(i).get_text("text")
                
                # Basic section detection
                cleaned = self._clean_text(text)
                text_blocks.append({
                    "page": i+1,
                    "content": cleaned,
                    "section": self._detect_section(cleaned)
                })
                
        return self._post_process(text_blocks)
    
    def _clean_text(self, text):
        """Remove header/footer and fix line breaks"""
        # Remove common header/footer patterns
        text = re.sub(r'(\n\d+\s+\n)|(\n\s*-\s+\d+\s+-\s*\n)', '\n', text)  # Page numbers
        text = re.sub(r'Received: .+?\n', '', text)  # Submission metadata
        text = re.sub(r'arXiv:.+?\n', '', text)  # arXiv headers
        
        # Fix line breaks within sentences
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)  # Single newlines to spaces
        text = re.sub(r'\n{3,}', '\n\n', text)  # Limit consecutive newlines
        
        return text.strip()
    
    def _detect_section(self, text):
        """Identify section headers using hybrid approach"""
        # First check for explicit section markers
        section_map = {
            r'introduction\b': 'Introduction',
            r'method(ology)?\b': 'Methodology',
            r'experiment(s|al)?\b': 'Experiments',
            r'result(s)?\b': 'Results',
            r'discussion\b': 'Discussion',
            r'conclusion\b': 'Conclusion'
        }
        
        for pattern, section in section_map.items():
            if re.search(f'^#?\s*{pattern}', text, re.IGNORECASE):
                return section
        
        # Fallback to LLM classification if no pattern match
        return self._classify_section_with_llm(text)
    
    def _post_process(self, blocks):
        """Self-correction and validation using LLM"""
        llm_prompt = f"""Validate and correct these text blocks from an academic paper:
        
        {json.dumps(blocks, indent=2)}
        
        1. Remove any remaining header/footer content
        2. Merge consecutive blocks from same section
        3. Split blocks containing multiple sections
        4. Return corrected JSON structure"""
        
        # Call to LLM service (pseudo-code)
        validated_blocks = self.llm_client.process(llm_prompt)
        return json.loads(validated_blocks)
    
    def extract_metadata(self):
        """Extract title, authors, affiliations using hybrid approach"""
        # First try PDF metadata
        meta = self.doc.metadata
        if meta.get('title'):
            return {
                'title': meta['title'],
                'authors': meta.get('author', '').split('; '),
                'venue': meta.get('subject', '')
            }
        
        # Fallback to first page analysis
        first_page = self.doc.load_page(0).get_text("text")
        return self._llm_metadata_extraction(first_page)
    
    def _llm_metadata_extraction(self, text):
        """Use LLM to extract metadata from first page"""
        prompt = f"""Extract paper metadata from this text:
        
        {text[:2000]}
        
        Return JSON with:
        - title
        - authors (array)
        - affiliations (array)
        - venue
        - publication_date (YYYY-MM)
        """
        response = self.llm_client.process(prompt)
        return json.loads(response)

class FigureExtractionAgent:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        
    def extract_figures(self):
        """Extract figures with captions using VLM assistance"""
        figures = []
        
        for page_num in range(len(self.doc)):
            page = self.doc.load_page(page_num)
            images = page.get_images()
            
            for img_index, img in enumerate(images):
                # Extract image
                base_image = self.doc.extract_image(img[0])
                image_bytes = base_image["image"]
                
                # Find associated caption
                caption = self._find_caption(page, img)
                
                figures.append({
                    "page": page_num+1,
                    "image": image_bytes,
                    "caption": caption,
                    "analysis": self.analyze_figure(image_bytes, caption)
                })
                
        return figures
    
    def _find_caption(self, page, img):
        """Find caption text near the image using spatial analysis"""
        img_rect = fitz.Rect(img[1:5])  # Image coordinates
        caption_margin = 10  # Pixels below image to search
        
        # Search area below the image
        search_rect = fitz.Rect(
            img_rect.x0, img_rect.y1 + caption_margin,
            img_rect.x1, img_rect.y1 + 200
        )
        
        # Extract text in caption area
        caption = page.get_text("text", clip=search_rect)
        
        # Clean and validate caption
        caption = re.sub(r'^(Figure\s*\d+[:.]?)\s*', '', caption.strip())
        return caption if len(caption) > 10 else ""
    
    def analyze_figure(self, image, caption):
        """Enhanced figure analysis with error recovery"""
        try:
            return self._call_vlm_api(image, caption)
        except Exception as e:
            return self._fallback_analysis(image, caption)
    
    def _call_vlm_api(self, image, caption):
        """Actual VLM API call with retries"""
        return self.vlm_client.analyze_image(
            image, 
            self._build_vlm_prompt(caption)
        )
    
    def _fallback_analysis(self, image, caption):
        """Fallback when VLM service fails"""
        return {
            "description": f"Figure: {caption}",
            "key_elements": re.findall(r'\b[A-Z][a-z]+\b', caption),
            "summary": caption,
            "alt_text": f"Diagram showing {caption}"
        }
    
    def optimize_figure(self, image_bytes):
        """Enhance figure quality and accessibility"""
        # Convert to high-res PNG
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert('RGB')
        img = self._enhance_resolution(img)
        
        # Create accessible versions
        return {
            'original': image_bytes,
            'high_res': self._convert_to_png(img),
            'accessible': self._create_accessible_version(img)
        }
    
    def _enhance_resolution(self, img):
        """Upscale image using super-resolution"""
        # Placeholder for actual SR implementation
        return img.resize((img.width*2, img.height*2), Image.BICUBIC)
    
    def _create_accessible_version(self, img):
        """Create high-contrast version with annotations"""
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        _, high_contrast = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        return cv2.imencode('.png', high_contrast)[1].tobytes()
    
    def recreate_svg(self, image_bytes):
        """Convert bitmap figures to SVG using vectorization"""
        # Convert image to vector paths
        vector_data = self._vectorize_image(image_bytes)
        
        # Build SVG XML structure
        svg_content = f"""
        <svg width="{vector_data['width']}" height="{vector_data['height']}">
            {''.join(vector_data['paths'])}
        </svg>
        """
        return svg_content.encode()
    
    def _vectorize_image(self, image_bytes):
        """Placeholder for actual vectorization logic"""
        return {
            "width": 800,
            "height": 600,
            "paths": ['<path d="M0 0 L100 100" stroke="black"/>']
        } 