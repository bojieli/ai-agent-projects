from paper_to_slides.slide_generator import SlideGenerator

def test_slide_generation(sample_content):
    generator = SlideGenerator()
    slides = generator.generate_slides(sample_content, [])
    
    assert "---\ntheme: seriph" in slides
    assert "Sample Paper" in slides
    assert "::left::" in slides  # Verify two-column layout

def test_speaker_notes():
    generator = SlideGenerator()
    slide = "# Test Slide"
    notes = "Sample speaker notes"
    result = generator.add_speaker_notes(slide, notes)
    
    assert "<!--\nSPEAKER:" in result
    assert notes in result 