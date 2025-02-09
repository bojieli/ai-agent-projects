import pytest
from paper_to_slides import PaperToSlides, Config
import os

@pytest.fixture
def sample_pdf():
    return "tests/data/sample_paper.pdf"

@pytest.fixture
def config():
    return Config()

@pytest.fixture
def processor(config):
    return PaperToSlides(config)

@pytest.fixture
def sample_content():
    return {
        "metadata": {
            "title": "Test Paper",
            "authors": ["Author 1", "Author 2"],
            "venue": "Test Conference 2024"
        },
        "sections": [
            {"type": "introduction", "content": "Sample intro text..."},
            {"type": "methodology", "content": "Sample methods..."}
        ]
    } 