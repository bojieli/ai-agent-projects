from paper_to_slides.content_analyzer import ContentAnalyzer
from unittest.mock import Mock

def test_paper_structure_analysis():
    llm_mock = Mock()
    llm_mock.process.return_value = '{"sections": []}'
    analyzer = ContentAnalyzer(llm_mock, Mock())
    
    result = analyzer.analyze_paper_structure("Sample paper text")
    assert isinstance(result, dict)
    assert 'sections' in result

def test_narrative_flow_creation():
    llm_mock = Mock()
    llm_mock.process.return_value = '{"slide_sequence": []}'
    analyzer = ContentAnalyzer(llm_mock, Mock())
    
    analysis = {"sections": []}
    result = analyzer.create_narrative_flow(analysis)
    assert 'slide_sequence' in result 