from paper_to_slides.accessibility import AccessibilityChecker

def test_accessibility_check():
    checker = AccessibilityChecker()
    slide_md = """
    # Slide 1
    <img src="figure1.png">
    <h3>Subsection</h3>
    """
    
    report = checker.check_slide(slide_md)
    assert len(report['alt_text_missing']) == 1
    assert report['heading_errors'] == [3, 1]

def test_alt_text_generation():
    checker = AccessibilityChecker()
    figure = {
        "caption": "Test figure",
        "analysis": {"summary": "Sample analysis"}
    }
    alt_text = checker.generate_alt_text(figure)
    
    assert figure['caption'] in alt_text
    assert figure['analysis']['summary'] in alt_text 