import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path to import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.script2json import script2json  # We'll mock this
from mainZ import (
    extract_article,
    image_validator_processor,
    script_processor,
    s2j_processor,
    error_handler
)

# Tests for extract_article
def test_extract_article_with_valid_message():
    message = {"article": "Sample article content"}
    result = extract_article(message)
    assert result == "Sample article content"

def test_extract_article_with_empty_message():
    message = {"article": ""}
    result = extract_article(message)
    assert result is None

def test_extract_article_with_missing_article():
    message = {"something_else": "data"}
    result = extract_article(message)
    assert result is None

# Tests for image_validator_processor
@patch('mainZ.ImageSearch')
def test_image_validator_processor_with_valid_article(mock_image_search):
    # Setup mock
    mock_instance = mock_image_search.return_value
    mock_instance.is_url_accessible.return_value = True
    
    article = """# Test article
This is a test
https://example.com/image.jpg, caption here
Another line
https://example.com/image2.png"""
    
    result = image_validator_processor(article)
    
    # URLs should remain unchanged
    assert "https://example.com/image.jpg, caption here" in result
    assert "https://example.com/image2.png" in result
    
    # Check if validation was called for image URLs
    assert mock_instance.is_url_accessible.call_count == 2

@patch('mainZ.ImageSearch')
def test_image_validator_processor_with_unreachable_images(mock_image_search):
    # Setup mock
    mock_instance = mock_image_search.return_value
    mock_instance.is_url_accessible.return_value = False
    mock_instance.get_alternative_image.return_value = "https://alternative.com/image.jpg"
    
    article = """# Test article
This is a test
https://example.com/image.jpg, caption here
Another line
https://example.com/image2.png"""
    
    result = image_validator_processor(article)
    
    # Original URLs should be replaced with alternative ones
    assert "https://alternative.com/image.jpg, caption here" in result
    assert "# Original unreachable image: https://example.com/image.jpg" in result
    assert "# Original unreachable image: https://example.com/image2.png" in result

@patch('mainZ.ImageSearch')
def test_image_validator_processor_non_image_urls(mock_image_search):
    mock_instance = mock_image_search.return_value
    
    article = """# Test article
This is a test
https://example.com/page.html
Another line"""
    
    result = image_validator_processor(article)
    
    # Non-image URLs should remain unchanged
    assert "https://example.com/page.html" in result
    # Validation shouldn't be called for non-image URLs
    mock_instance.is_url_accessible.assert_not_called()

# Tests for script_processor
@patch('mainZ.ImageSearch')
def test_script_processor_with_sufficient_images(mock_image_search):
    # Setup - article with 5 images already
    article = """# Test article
This is a test
https://example.com/image1.jpg
https://example.com/image2.jpg
https://example.com/image3.jpg
https://example.com/image4.jpg
https://example.com/image5.jpg"""
    
    result = script_processor(article)
    
    # Count the number of URLs in the result
    url_count = result.count('http')
    assert url_count == 5  # No new images should be added

@patch('mainZ.ImageSearch')
def test_script_processor_with_insufficient_images(mock_image_search):
    # Setup mock
    mock_instance = mock_image_search.return_value
    mock_instance.get_alternative_image.side_effect = [
        "https://new1.com/image.jpg",
        "https://new2.com/image.jpg",
        "https://new3.com/image.jpg"
    ]
    
    # Article with only 2 images
    article = """# Test article
This is a test
https://example.com/image1.jpg
https://example.com/image2.jpg"""
    
    result = script_processor(article)
    
    # Count the number of URLs in the result
    url_count = result.count('http')
    assert url_count == 5  # Should have 5 images now
    
    # Check for "Auto-generated additional images:" comment
    assert "# Auto-generated additional images:" in result
    
    # Verify that the generated images are added
    assert "https://new1.com/image.jpg" in result
    assert "https://new2.com/image.jpg" in result
    assert "https://new3.com/image.jpg" in result
    
    # Verify original content is preserved
    assert "# Test article" in result
    assert "This is a test" in result
    assert "https://example.com/image1.jpg" in result
    assert "https://example.com/image2.jpg" in result
    
    # Verify the mock was called exactly 3 times
    assert mock_instance.get_alternative_image.call_count == 3

@patch('mainZ.ImageSearch')
def test_script_processor_with_no_images(mock_image_search):
    # Setup mock
    mock_instance = mock_image_search.return_value
    mock_instance.get_alternative_image.side_effect = [
        "https://new1.com/image.jpg",
        "https://new2.com/image.jpg",
        "https://new3.com/image.jpg",
        "https://new4.com/image.jpg",
        "https://new5.com/image.jpg"
    ]
    
    # Article with no images
    article = """# Test article
This is a test article with no images"""
    
    result = script_processor(article)
    
    # Count the number of URLs in the result
    url_count = result.count('http')
    assert url_count == 5  # Should have 5 images now
    assert "# Auto-generated images:" in result

# Tests for s2j_processor
@patch('mainZ.script2json')
def test_s2j_processor(mock_script2json):
    expected_json = {"title": "Test", "content": "test content"}
    mock_script2json.return_value = expected_json
    
    script = "This is a test script"
    result = s2j_processor(script)
    
    assert result == expected_json
    mock_script2json.assert_called_once_with(script)

# Tests for error_handler
def test_error_handler_with_dict_message():
    message = {"data": "test"}
    error = ValueError("Test error")
    result = error_handler(message, error, "test_processor")
    
    assert "processing_error" in result
    assert result["processing_error"]["processor"] == "test_processor"
    assert result["processing_error"]["error"] == "Test error"
    assert "timestamp" in result["processing_error"]

def test_error_handler_with_non_dict_message():
    message = "not a dict"
    error = ValueError("Test error")
    result = error_handler(message, error, "test_processor")
    
    assert result is None  # Should drop non-dict messages

# Test the full processor chain
@patch('mainZ.s2j_processor')
@patch('mainZ.script_processor')
@patch('mainZ.image_validator_processor')
def test_complete_pipeline(mock_image_validator, mock_script_processor, mock_s2j):
    # Setup mocks for each processor
    mock_image_validator.return_value = "validated script"
    mock_script_processor.return_value = "processed script"
    mock_s2j.return_value = {"output": "final json"}
    
    # Create and execute the chain
    from mainZ import create_complete_pipeline
    chain = create_complete_pipeline()
    
    # Test with a valid input
    result = chain.process({"article": "test article"})
    
    # Verify the pipeline executed correctly
    mock_image_validator.assert_called_once_with("test article")
    mock_script_processor.assert_called_once_with("validated script")
    mock_s2j.assert_called_once_with("processed script")
    assert result == {"output": "final json"}
