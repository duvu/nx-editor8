#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for VideoSearch in Docker environment
"""

import os
import json
import sys
from src.utils.video_search import VideoSearch
from src.logger import logger

def main():
    """
    Test VideoSearch functionality
    """
    logger.info("Testing VideoSearch in Docker environment")
    
    # Initialize VideoSearch
    vs = VideoSearch()
    logger.info("VideoSearch initialized")
    
    # Test search functionality
    keywords = "nature documentary HD wildlife"
    logger.info(f"Searching for videos with keywords: {keywords}")
    
    results = vs.search_videos(keywords, max_results=2)
    
    if results:
        logger.info(f"Found {len(results)} videos")
        
        # Save results to file
        output_dir = "data"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(os.path.join(output_dir, "video_search_results.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        
        # Print first result
        if results:
            video = results[0]
            logger.info(f"First video: {video.get('title')}")
            logger.info(f"URL: {video.get('url')}")
            logger.info(f"Thumbnail: {video.get('thumbnail')}")
            logger.info(f"Embed URL: {video.get('embed_url')}")
    else:
        logger.error("No videos found!")
    
    # Test alternative video
    logger.info("Testing get_alternative_video")
    alt_video = vs.get_alternative_video("beautiful nature scenes")
    
    if alt_video:
        logger.info(f"Alternative video: {alt_video.get('title')}")
        logger.info(f"URL: {alt_video.get('url')}")
        logger.info(f"Embed URL: {alt_video.get('embed_url')}")
        
        with open(os.path.join(output_dir, "alternative_video.json"), "w", encoding="utf-8") as f:
            json.dump(alt_video, f, indent=2)
    else:
        logger.error("Failed to get alternative video!")
    
    logger.info("VideoSearch test completed")

if __name__ == "__main__":
    main() 