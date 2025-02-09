def test_full_workflow(processor, sample_pdf):
    slides = processor.process(sample_pdf)
    
    # Verify basic structure
    assert "---\ntheme: seriph" in slides
    assert "<audio src=" in slides  # TTS integration
    assert "transition: slide-up" in slides
    
    # Verify content from sample PDF
    assert "Key Results" in slides
    assert "Methodology" in slides
    assert "References" not in slides  # Should be filtered

def test_error_handling():
    from paper_to_slides.error_handling import retry
    mock_func = Mock(side_effect=Exception("Test error"))
    
    @retry(max_retries=3)
    def test_fn():
        return mock_func()
    
    with pytest.raises(Exception):
        test_fn()
    
    assert mock_func.call_count == 3 