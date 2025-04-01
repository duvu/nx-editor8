#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os

# Ensure the src directory is in the path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'src'))

from utils.video_search import VideoSearch
from logger import logger

if __name__ == "__main__":
    # Set log level to DEBUG to see detailed search process
    logger.set_level('DEBUG')
    logger.info("Starting Creative Commons video search test...")
    
    # Instantiate the searcher
    video_searcher = VideoSearch()
    
    # Define keywords likely to have CC results
    keywords = "NASA space footage"
    max_results = 3
    
    logger.info(f"Searching for {max_results} Creative Commons videos with keywords: '{keywords}'")
    
    # Call the specific function
    cc_videos = video_searcher.search_creative_commons_videos(
        keywords=keywords, 
        max_results=max_results
    )
    
    if cc_videos:
        logger.info(f"Found {len(cc_videos)} Creative Commons videos:")
        # Pretty print the results
        print(json.dumps(cc_videos, indent=2, ensure_ascii=False))
    else:
        logger.info("No Creative Commons videos found for the given keywords.")

    logger.info("Creative Commons video search test finished.") 