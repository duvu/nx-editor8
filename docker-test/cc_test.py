#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import sys
import os

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cc_test')

# Thêm đường dẫn cho import
sys.path.insert(0, os.path.abspath('/app'))

try:
    from src.utils.video_search import VideoSearch
    logger.info("Đã import thành công VideoSearch")
except ImportError as e:
    logger.error(f"Lỗi khi import: {e}")
    sys.exit(1)

def main():
    """Kiểm tra tìm kiếm video Creative Commons"""
    logger.info("Khởi tạo VideoSearch")
    searcher = VideoSearch()
    
    keywords = "nature documentary HD"
    logger.info(f"Tìm kiếm video với từ khóa: {keywords}")
    
    # Tìm video thông thường
    logger.info("Tìm kiếm video thông thường")
    std_results = searcher.search_videos(keywords, max_results=3)
    logger.info(f"Tìm thấy {len(std_results)} video thông thường")
    
    # Lưu kết quả
    with open('/app/data/std_videos.json', 'w') as f:
        json.dump(std_results, f, indent=2)
    
    # Video Creative Commons
    # Kiểm tra nếu phương thức get_alternative_video hỗ trợ tham số creative_commons_only
    logger.info("Tìm video thay thế Creative Commons")
    
    try:
        # Thử gọi phương thức với tham số creative_commons_only
        alt_video = searcher.get_alternative_video(keywords, creative_commons_only=True)
        has_cc_support = True
        logger.info("Module video_search.py hỗ trợ chức năng tìm kiếm Creative Commons")
    except TypeError as e:
        logger.warning(f"Module video_search.py không hỗ trợ tham số creative_commons_only: {e}")
        alt_video = searcher.get_alternative_video(keywords)
        has_cc_support = False
    
    if alt_video:
        logger.info(f"Tìm thấy video thay thế: {alt_video.get('title')}")
        logger.info(f"URL: {alt_video.get('url')}")
        if 'license' in alt_video:
            logger.info(f"Giấy phép: {alt_video.get('license')}")
        
        with open('/app/data/alternative_video.json', 'w') as f:
            json.dump(alt_video, f, indent=2)
    else:
        logger.warning("Không tìm thấy video thay thế")
    
    # Kiểm tra những video nào có giấy phép Creative Commons
    if std_results:
        cc_videos = []
        for video in std_results:
            # Kiểm tra thông tin giấy phép nếu có
            if 'license' in video and 'creative commons' in video['license'].lower():
                cc_videos.append(video)
                logger.info(f"Video có giấy phép Creative Commons: {video['title']}")
                logger.info(f"  - License: {video['license']}")
            
        if cc_videos:
            with open('/app/data/found_cc_videos.json', 'w') as f:
                json.dump(cc_videos, f, indent=2)
            logger.info(f"Tìm thấy {len(cc_videos)} video có giấy phép Creative Commons trong kết quả tìm kiếm")
        else:
            logger.info("Không tìm thấy video có giấy phép Creative Commons trong kết quả tìm kiếm")
    
    logger.info("Hoàn thành kiểm tra")

if __name__ == "__main__":
    main() 