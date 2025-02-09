def test_config_loading():
    from paper_to_slides.config import Config
    config = Config()
    
    assert config.max_slides == 20
    assert config.tts_enabled is True
    assert config.figure_quality == "high"

def test_config_overrides(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("max_slides: 15\ntts_enabled: false")
    
    from paper_to_slides.config import Config
    config = Config()
    config.path = config_file
    
    assert config.max_slides == 15
    assert config.tts_enabled is False 