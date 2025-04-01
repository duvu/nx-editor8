#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for Pexels video search functionality
"""

import os
import sys
import json
import argparse
from src.utils.pexels_video_search import PexelsVideoSearch
from src.logger import logger

def save_json(data, filename):
    """Save data to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved JSON data to {filename}")

def main():
    """Main function to test Pexels video search"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test Pexels video search')
    parser.add_argument('--api-key', type=str, help='Pexels API key (or set PEXELS_API_KEY env var)')
    parser.add_argument('--keywords', type=str, default='nature beautiful landscape', help='Search keywords')
    parser.add_argument('--download', action='store_true', help='Download the first found video')
    parser.add_argument('--output-dir', type=str, default='pexels_videos', help='Output directory for downloaded videos')
    args = parser.parse_args()

    # Get API key from arguments or environment
    api_key = args.api_key or os.environ.get('PEXELS_API_KEY', '')
    if not api_key:
        logger.error("No Pexels API key provided. Use --api-key or set PEXELS_API_KEY environment variable.")
        return 1

    # Initialize PexelsVideoSearch
    logger.info("Initializing PexelsVideoSearch...")
    pexels = PexelsVideoSearch(api_key=api_key)

    # Search for videos
    logger.info(f"Searching for videos with keywords: '{args.keywords}'")
    videos = pexels.search_videos(args.keywords, max_results=5)

    # Print results
    if videos:
        logger.info(f"Found {len(videos)} videos")
        for i, video in enumerate(videos):
            logger.info(f"Video {i+1}: {video.get('title')} - {video.get('duration')}s - {video.get('resolution')}")
        
        # Save results to JSON
        save_json(videos, "pexels_search_results.json")
        
        # Test get_alternative_video
        logger.info("Testing get_alternative_video()...")
        alt_video = pexels.get_alternative_video(args.keywords)
        if alt_video:
            logger.info(f"Alternative video: {alt_video.get('title')} - {alt_video.get('duration')}s")
            save_json(alt_video, "pexels_alternative_video.json")
            
            # Test download if requested
            if args.download and alt_video.get('url'):
                logger.info(f"Downloading video: {alt_video.get('url')}")
                os.makedirs(args.output_dir, exist_ok=True)
                output_path = os.path.join(args.output_dir, f"pexels_video_{alt_video.get('id')}.mp4")
                downloaded_path = pexels.download_video(alt_video.get('url'), output_path)
                if downloaded_path:
                    logger.info(f"Successfully downloaded video to: {downloaded_path}")
                else:
                    logger.error("Failed to download video")
        else:
            logger.warning("No alternative video found")
    else:
        logger.warning("No videos found")

    return 0

if __name__ == "__main__":
    sys.exit(main()) 