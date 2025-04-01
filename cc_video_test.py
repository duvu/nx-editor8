#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.video_search import VideoSearch

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cc_video_test')

def test_creative_commons_search():
    """Test tìm kiếm video Creative Commons"""
    logger.info("Khởi tạo VideoSearch")
    searcher = VideoSearch()
    
    keywords = "nature documentary wildlife"
    logger.info(f"Tìm kiếm video với từ khóa: {keywords}")
    
    # Test 1: Tìm kiếm video không có yêu cầu Creative Commons
    logger.info("TEST 1: Tìm kiếm video thông thường (không yêu cầu Creative Commons)")
    standard_results = searcher.search_videos(keywords, max_results=5, creative_commons_only=False)
    
    logger.info(f"Tìm thấy {len(standard_results)} video thông thường")
    if standard_results:
        with open('data/standard_videos.json', 'w') as f:
            json.dump(standard_results, f, indent=2)
    
    # Test 2: Tìm kiếm video với yêu cầu Creative Commons
    logger.info("TEST 2: Tìm kiếm video Creative Commons")
    cc_results = searcher.search_videos(keywords, max_results=5, creative_commons_only=True)
    
    logger.info(f"Tìm thấy {len(cc_results)} video Creative Commons")
    if cc_results:
        with open('data/cc_videos.json', 'w') as f:
            json.dump(cc_results, f, indent=2)
    
    # Test 3: Tìm video thay thế với yêu cầu Creative Commons
    logger.info("TEST 3: Tìm video thay thế với yêu cầu Creative Commons")
    alt_video = searcher.get_alternative_video(keywords, creative_commons_only=True)
    
    if alt_video:
        logger.info(f"Tìm thấy video thay thế: {alt_video.get('title', 'Unknown')}")
        logger.info(f"URL: {alt_video.get('url', 'Unknown')}")
        logger.info(f"Giấy phép: {alt_video.get('license', 'Unknown')}")
        
        with open('data/cc_alternative_video.json', 'w') as f:
            json.dump(alt_video, f, indent=2)
    else:
        logger.warning("Không tìm thấy video thay thế với giấy phép Creative Commons")
    
    # Test 4: So sánh video thông thường với video Creative Commons
    logger.info("TEST 4: So sánh kết quả tìm kiếm")
    
    if standard_results and cc_results:
        # Kiểm tra xem có video nào xuất hiện trong cả hai kết quả không
        standard_ids = [video.get('id') for video in standard_results]
        cc_ids = [video.get('id') for video in cc_results]
        
        common_videos = set(standard_ids).intersection(set(cc_ids))
        
        logger.info(f"Số video chung trong cả hai kết quả: {len(common_videos)}")
        
        # Kiểm tra thông tin giấy phép
        if cc_results:
            cc_licenses = [video.get('license') for video in cc_results]
            logger.info(f"Các giấy phép trong kết quả Creative Commons: {set(cc_licenses)}")
    
    logger.info("Kết thúc kiểm tra tìm kiếm video Creative Commons")

if __name__ == "__main__":
    logger.info("Bắt đầu kiểm tra tính năng tìm kiếm video Creative Commons")
    test_creative_commons_search()
    logger.info("Hoàn thành kiểm tra") 