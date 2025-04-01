#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for random keyword selection functionality.
This script tests how random keywords are selected for video and image searches.
"""

import os
import sys
import json
import logging
import argparse
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the required modules
try:
    from src.utils.video_search import VideoSearch
    from src.utils.image_search import ImageSearch
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

# Define select_random_keywords function directly to avoid circular imports
def select_random_keywords(keywords: str, min_keywords: int = 1, max_keywords: int = 2) -> str:
    """Select 1-2 random keywords from the full keywords string.
    
    Args:
        keywords: Full keywords string
        min_keywords: Minimum number of keywords to select
        max_keywords: Maximum number of keywords to select
        
    Returns:
        String with 1-2 randomly selected keywords
    """
    if not keywords:
        return ""
        
    # Split keywords into a list and remove empty strings
    keyword_list = [kw.strip() for kw in keywords.split() if kw.strip()]
    
    if not keyword_list:
        return ""
        
    # If we have very few keywords, just return them all
    if len(keyword_list) <= min_keywords:
        return " ".join(keyword_list)
        
    # Determine how many keywords to select (between min and max)
    num_to_select = min(random.randint(min_keywords, max_keywords), len(keyword_list))
    
    # Select random keywords
    selected_keywords = random.sample(keyword_list, num_to_select)
    
    logger.info(f"Selected {num_to_select} random keywords from '{keywords}': '{' '.join(selected_keywords)}'")
    return " ".join(selected_keywords)

def test_random_keywords():
    """Test the random keyword selection functionality"""
    # Test cases with different numbers of keywords
    test_cases = [
        "nature",
        "beautiful landscape",
        "amazing wildlife documentary national geographic",
        "underwater ocean life coral reef fish sharks",
        "space planets stars galaxies nebulae black holes astronomy universe"
    ]
    
    logger.info("Testing random keyword selection")
    logger.info("-" * 50)
    
    for i, keywords in enumerate(test_cases):
        logger.info(f"Test case {i+1}: '{keywords}'")
        for j in range(3):  # Run multiple times to see different selections
            selected = select_random_keywords(keywords)
            logger.info(f"  Run {j+1}: Selected '{selected}'")
        logger.info("-" * 50)

def test_video_search_with_random_keywords():
    """Test video search with random keyword selection"""
    # Test with a complex set of keywords
    full_keywords = "wildlife documentary animals nature africa savanna"
    
    logger.info(f"Full keywords: '{full_keywords}'")
    selected_keywords = select_random_keywords(full_keywords)
    logger.info(f"Selected random keywords: '{selected_keywords}'")
    
    # Search for videos with the selected keywords
    logger.info(f"Searching for videos with selected keywords: '{selected_keywords}'")
    video_searcher = VideoSearch()
    videos = video_searcher.search_videos(selected_keywords, max_results=3, creative_commons_only=True)
    
    if videos:
        logger.info(f"Found {len(videos)} videos")
        # Save results to JSON for inspection
        with open("random_keywords_video_results.json", "w") as f:
            json.dump(videos, f, indent=2)
        logger.info("Results saved to random_keywords_video_results.json")
    else:
        logger.warning("No videos found")

def test_image_search_with_random_keywords():
    """Test image search with random keyword selection"""
    # Test with a complex set of keywords
    full_keywords = "mountain landscape scenic beautiful sunrise fog"
    
    logger.info(f"Full keywords: '{full_keywords}'")
    selected_keywords = select_random_keywords(full_keywords)
    logger.info(f"Selected random keywords: '{selected_keywords}'")
    
    # Search for images with the selected keywords
    logger.info(f"Searching for images with selected keywords: '{selected_keywords}'")
    image_searcher = ImageSearch()
    images = image_searcher.search_duckduckgo(selected_keywords, max_results=3)
    
    if images:
        logger.info(f"Found {len(images)} images")
        # Save results to JSON for inspection
        with open("random_keywords_image_results.json", "w") as f:
            json.dump(images, f, indent=2)
        logger.info("Results saved to random_keywords_image_results.json")
    else:
        logger.warning("No images found")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Test random keyword selection')
    parser.add_argument('--selection-only', action='store_true', help='Only test keyword selection (no API calls)')
    args = parser.parse_args()
    
    # Always test the selection functionality
    test_random_keywords()
    
    # Only test the search functionality if not in selection-only mode
    if not args.selection_only:
        logger.info("\nTesting video search with random keywords")
        test_video_search_with_random_keywords()
        
        logger.info("\nTesting image search with random keywords")
        test_image_search_with_random_keywords()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 