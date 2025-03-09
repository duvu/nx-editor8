#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module xử lý và xác thực hình ảnh trong bài viết

Module này cung cấp các chức năng để xử lý hình ảnh trong bài viết, bao gồm:
1. Kiểm tra tính khả dụng của các URL hình ảnh trong bài viết
2. Thay thế các URL hình ảnh không khả dụng bằng hình ảnh thay thế
3. Tìm kiếm hình ảnh thay thế dựa trên từ khóa hoặc tiêu đề bài viết

Quy trình xử lý:
1. Phân tích bài viết để tìm các URL hình ảnh
2. Kiểm tra tính khả dụng của từng URL bằng cách gửi HTTP request
3. Đối với các URL không khả dụng, tìm kiếm hình ảnh thay thế
4. Thay thế URL trong bài viết với URL mới

Cách sử dụng:
    from src.processor import image_processor
    
    # Dữ liệu đầu vào là một dict chứa bài viết và tiêu đề
    data = {
        "article": "Nội dung bài viết với các URL hình ảnh...", 
        "title": "Tiêu đề bài viết"
    }
    
    # Xử lý hình ảnh
    processed_data = image_processor(data)

Tham số đầu vào:
    data (dict): Dict chứa bài viết ('article') và tiêu đề ('title')

Kết quả trả về:
    dict: Dict chứa bài viết đã được xử lý với các URL hình ảnh đã được kiểm tra/thay thế

Phụ thuộc:
    - ImageSearch: Lớp hỗ trợ tìm kiếm và kiểm tra hình ảnh
    - logger: Module ghi log

Tác giả: NX-Editor8 Team
Phiên bản: 1.0
"""

import re
import time
from ..logger import logger
from ..image_search import ImageSearch

def image_processor(data):
    """
    Xử lý và xác thực hình ảnh trong bài viết
    
    Args:
        data (dict): Dữ liệu bài viết đã được trích xuất
        
    Returns:
        dict: Dữ liệu bài viết đã được xử lý hình ảnh hoặc dữ liệu gốc nếu không thành công
    """
    logger.info("Starting image processor")
    start_time = time.time()
    
    # Validate input
    if not isinstance(data, dict):
        logger.error(f"Expected dict input but got {type(data)}")
        return None
    
    # Extract article and title from the input data
    article = data.get("article", "")
    title = data.get("title", "")
    
    if not article:
        logger.warning("Empty article received in image processor")
        return data
    
    logger.debug(f"Processing article with {len(article)} chars and title: '{title}'")
    
    # Initialize image search helper
    image_searcher = ImageSearch()
    
    # Extract keywords from the script (lines starting with #)
    keywords = ""
    lines = article.strip().split('\n')
    logger.debug(f"Article split into {len(lines)} lines")
    
    for i, line in enumerate(lines):
        if line.startswith('#'):
            keywords = line.strip('#').strip()
            logger.debug(f"Found keywords at line {i+1}: '{keywords}'")
            break
    
    # If no keywords found, use title instead of default
    if not keywords:
        keywords = title if title else "generic images"
        logger.info(f"No keywords found in text, using title as keywords: '{keywords}'")
    
    logger.info(f"Using keywords for image search: '{keywords}'")
    
    # Process each line and replace unreachable image URLs
    modified_lines = []
    replaced_count = 0
    checked_count = 0
    
    for i, line in enumerate(lines):
        if line.startswith('http://') or line.startswith('https://'):
            # Extract the URL part (before any comma)
            url_parts = line.split(',', 1)
            url = url_parts[0].strip()
            
            # Check if this URL is an image (not a video)
            is_image = bool(re.search(r'\.(jpg|jpeg|png|gif|bmp|webp|tiff|svg)(\?|$|#)', url.lower()))
            
            if is_image:
                logger.debug(f"Checking image URL at line {i+1}: {url}")
                checked_count += 1
                
                # For images, check if URL is accessible
                url_start_time = time.time()
                is_accessible = image_searcher.is_url_accessible(url)
                url_check_time = time.time() - url_start_time
                
                logger.debug(f"URL check took {url_check_time:.2f}s, accessible: {is_accessible}")
                
                if not is_accessible:
                    logger.warning(f"Image URL not accessible at line {i+1}: {url}")
                    
                    # Get alternative image based on keywords
                    search_start_time = time.time()
                    new_url = image_searcher.get_alternative_image(keywords)
                    search_time = time.time() - search_start_time
                    
                    if new_url:
                        logger.info(f"Found replacement image in {search_time:.2f}s: {new_url}")
                        replaced_count += 1
                        
                        # Replace the URL in the original line
                        if len(url_parts) > 1:
                            line = f"{new_url},{url_parts[1]}"
                            logger.debug(f"Replaced URL with parameters: {line}")
                        else:
                            line = new_url
                            logger.debug(f"Replaced URL: {line}")
                    else:
                        logger.warning(f"Failed to find alternative image for '{keywords}'")
            else:
                logger.debug(f"Line {i+1} contains URL but not an image: {url}")
            
        modified_lines.append(line)
    
    # Join lines back into a single string
    data["article"] = '\n'.join(modified_lines)
    
    processing_time = time.time() - start_time
    logger.info(f"Image processing complete. Checked {checked_count} images, replaced {replaced_count} unreachable images in {processing_time:.2f}s")
    
    return data 