from paper_to_slides.pdf_processor import TextExtractionAgent, FigureExtractionAgent
import fitz

def test_text_extraction(sample_pdf):
    agent = TextExtractionAgent(sample_pdf)
    text_blocks = agent.extract_text()
    
    assert len(text_blocks) > 0
    assert any(block['section'] == 'Introduction' for block in text_blocks)
    assert 'References' not in [block['section'] for block in text_blocks]

def test_figure_extraction(sample_pdf):
    agent = FigureExtractionAgent(sample_pdf)
    figures = agent.extract_figures()
    
    assert len(figures) >= 2  # Sample PDF has 2 figures
    assert all('caption' in fig for fig in figures)
    assert all('analysis' in fig for fig in figures)

def test_metadata_extraction(sample_pdf):
    agent = TextExtractionAgent(sample_pdf)
    metadata = agent.extract_metadata()
    
    assert metadata['title'] == "Sample Paper Title"
    assert len(metadata['authors']) == 2
    assert "2024" in metadata['publication_date'] 