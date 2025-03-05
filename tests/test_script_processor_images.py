import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import re

# Add the parent directory to sys.path to import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mainZ import script_processor

@patch('mainZ.ImageSearch')
def test_script_processor_with_exactly_four_images(mock_image_search):
    """Test when article has exactly 4 images (needs 1 more)"""
    # Setup mock
    mock_instance = mock_image_search.return_value
    mock_instance.get_alternative_image.return_value = "https://new1.com/image.jpg"
    
    # Article with 4 images
    article = """# Test article
This is a test article with four images
https://example.com/image1.jpg
https://example.com/image2.jpg
https://example.com/image3.jpg
https://example.com/image4.jpg"""
    
    result = script_processor(article)
    
    # Count the number of URLs in the result
    url_count = result.count('http')
    assert url_count == 5  # Should have exactly 5 images now
    
    # New image should be added with the appropriate comment
    assert "# Auto-generated additional images:" in result
    assert "https://new1.com/image.jpg" in result
    
    # Verify get_alternative_image was called exactly once
    assert mock_instance.get_alternative_image.call_count == 1

@patch('mainZ.ImageSearch')
def test_script_processor_with_different_image_formats(mock_image_search):
    """Test that the processor recognizes different image formats as images"""
    mock_instance = mock_image_search.return_value
    mock_instance.get_alternative_image.return_value = "https://new.com/image.jpg"
    
    # Article with 3 images in different formats
    article = """# Test article
Testing different image formats
https://example.com/image1.jpg
https://example.com/image2.png
https://example.com/image3.gif"""
    
    result = script_processor(article)
    
    # Should recognize all three as images and add two more
    assert mock_instance.get_alternative_image.call_count == 2
    url_count = result.count('http')
    assert url_count == 5

@patch('mainZ.ImageSearch')
def test_script_processor_correct_image_placement(mock_image_search):
    """Test that new images are inserted after the last existing image"""
    # Setup mock
    mock_instance = mock_image_search.return_value
    mock_instance.get_alternative_image.side_effect = [
        "https://new1.com/image.jpg",
        "https://new2.com/image.jpg",
        "https://new3.com/image.jpg"
    ]
    
    # Article with 2 images interspersed in content
    article = """# Test article
This is a test article.
https://example.com/image1.jpg
Some text between images.
https://example.com/image2.jpg
More text after all images."""
    
    result = script_processor(article)
    
    # Convert result to lines for easier analysis
    result_lines = result.split('\n')
    
    # Find where the last original image appears
    last_original_image_index = -1
    for i, line in enumerate(result_lines):
        if "https://example.com/image2.jpg" in line:
            last_original_image_index = i
    
    assert last_original_image_index > 0
    
    # The next line should be our comment about auto-generated images
    assert "# Auto-generated additional images:" in result_lines[last_original_image_index + 1]
    
    # The following lines should be our new images
    assert "https://new1.com/image.jpg" in result_lines[last_original_image_index + 2]
    assert "https://new2.com/image.jpg" in result_lines[last_original_image_index + 3]
    assert "https://new3.com/image.jpg" in result_lines[last_original_image_index + 4]
    
    # The final line should be our "More text after all images."
    assert "More text after all images." in result_lines[last_original_image_index + 5]

@patch('mainZ.ImageSearch')
def test_script_processor_keyword_extraction(mock_image_search):
    """Test that keywords are properly extracted from the article title"""
    mock_instance = mock_image_search.return_value
    mock_instance.get_alternative_image.return_value = "https://new.com/image.jpg"
    
    # Article with a clear title containing keywords
    article = """# Artificial Intelligence and Machine Learning
This is an article about AI and ML technologies.
https://example.com/image1.jpg"""
    
    script_processor(article)
    
    # Check that the image search used the keywords from the title
    calls = mock_instance.get_alternative_image.call_args_list
    assert len(calls) == 4  # Should be called 4 times to add 4 more images
    
    # Each call should use the keywords from the title
    for call in calls:
        args, _ = call
        assert args[0] == "Artificial Intelligence and Machine Learning"

@patch('mainZ.ImageSearch')
def test_script_processor_with_no_title(mock_image_search):
    """Test when article has no title/keywords, should use default"""
    mock_instance = mock_image_search.return_value
    mock_instance.get_alternative_image.return_value = "https://new.com/image.jpg"
    
    # Article with no title line starting with #
    article = """This is an article with no title.
https://example.com/image1.jpg"""
    
    script_processor(article)
    
    # Check that the image search used the default keywords
    calls = mock_instance.get_alternative_image.call_args_list
    assert len(calls) == 4
    
    # Each call should use the default keywords
    for call in calls:
        args, _ = call
        assert args[0] == "generic images"

@patch('mainZ.ImageSearch')
def test_script_processor_with_partially_failed_image_search(mock_image_search):
    """Test when some image searches return None"""
    mock_instance = mock_image_search.return_value
    # Simulate some image searches failing (returning None)
    mock_instance.get_alternative_image.side_effect = [
        "https://new1.com/image.jpg",
        None,
        "https://new3.com/image.jpg"
    ]
    
    # Article with 2 images
    article = """# Test article
https://example.com/image1.jpg
https://example.com/image2.jpg"""
    
    result = script_processor(article)
    
    # Should only add the successful image searches
    url_count = result.count('http')
    assert url_count == 4  # 2 original + 2 successful new ones
    assert result.count("new1.com") == 1
    assert result.count("new3.com") == 1
