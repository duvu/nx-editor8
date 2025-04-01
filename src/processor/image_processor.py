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
Phiên bản: 1.1
"""

import re
import time
from typing import Dict, Any, List, Tuple, Optional
from ..logger import logger
from ..utils.image_search import ImageSearch
from ..utils.keyword_utils import select_random_keywords

# Định nghĩa các hằng số
URL_PATTERN = r'^https?://'
IMAGE_EXTENSION_PATTERN = r'\.(jpg|jpeg|png|gif|bmp|webp|tiff|svg)(\?|$|#)'


def extract_keywords(lines: List[str], title: str) -> str:
    """
    Trích xuất từ khóa từ bài viết hoặc sử dụng tiêu đề làm từ khóa
    
    Args:
        lines: Danh sách các dòng trong bài viết
        title: Tiêu đề bài viết
        
    Returns:
        Từ khóa được trích xuất
    """
    # Tìm từ khóa trong các dòng bắt đầu bằng #
    for i, line in enumerate(lines):
        if line.startswith('#'):
            keywords = line.strip('#').strip()
            logger.debug(f"Found keywords at line {i+1}: '{keywords}'")
            return keywords
    
    # Nếu không tìm thấy từ khóa, sử dụng tiêu đề
    keywords = title if title else "generic images"
    logger.info(f"No keywords found in text, using title as keywords: '{keywords}'")
    return keywords


def is_image_url(url: str) -> bool:
    """
    Kiểm tra xem URL có phải là URL hình ảnh không dựa trên phần mở rộng
    
    Args:
        url: URL cần kiểm tra
        
    Returns:
        True nếu URL là hình ảnh, False nếu không phải
    """
    return bool(re.search(IMAGE_EXTENSION_PATTERN, url.lower()))


def process_image_url(
    url: str, 
    url_parts: List[str], 
    line_number: int, 
    image_searcher: ImageSearch, 
    keywords: str
) -> Tuple[str, bool]:
    """
    Xử lý URL hình ảnh: kiểm tra tính khả dụng và thay thế nếu cần
    
    Args:
        url: URL hình ảnh cần xử lý
        url_parts: Các phần của dòng URL (URL và tham số)
        line_number: Số dòng trong bài viết
        image_searcher: Đối tượng ImageSearch để tìm kiếm hình ảnh thay thế
        keywords: Từ khóa để tìm kiếm hình ảnh thay thế
        
    Returns:
        Tuple (dòng mới, đã thay thế hay không)
    """
    logger.debug(f"Checking image URL at line {line_number}: {url}")
    
    # Kiểm tra tính khả dụng của URL
    url_start_time = time.time()
    is_accessible = image_searcher.is_url_accessible(url)
    url_check_time = time.time() - url_start_time
    
    logger.debug(f"URL check took {url_check_time:.2f}s, accessible: {is_accessible}")
    
    # Nếu URL không khả dụng, tìm URL thay thế
    if not is_accessible:
        logger.warning(f"Image URL not accessible at line {line_number}: {url}")
        
        # Tìm hình ảnh thay thế
        search_start_time = time.time()
        new_url = image_searcher.get_alternative_image(keywords)
        search_time = time.time() - search_start_time
        
        if new_url:
            logger.info(f"Found replacement image in {search_time:.2f}s: {new_url}")
            
            # Tạo dòng mới với URL thay thế
            if len(url_parts) > 1:
                new_line = f"{new_url},{url_parts[1]}"
                logger.debug(f"Replaced URL with parameters: {new_line}")
            else:
                new_line = new_url
                logger.debug(f"Replaced URL: {new_line}")
            
            return new_line, True
        else:
            logger.warning(f"Failed to find alternative image for '{keywords}'")
    
    # Trả về dòng ban đầu nếu không cần thay thế
    return url if len(url_parts) == 1 else f"{url},{url_parts[1]}", False


def process_url_line(
    line: str, 
    line_number: int, 
    image_searcher: ImageSearch, 
    keywords: str
) -> Tuple[str, bool, bool]:
    """
    Xử lý dòng chứa URL
    
    Args:
        line: Dòng cần xử lý
        line_number: Số dòng trong bài viết
        image_searcher: Đối tượng ImageSearch
        keywords: Từ khóa tìm kiếm
        
    Returns:
        Tuple (dòng đã xử lý, có phải hình ảnh không, đã thay thế không)
    """
    # Tách URL và các tham số (nếu có)
    url_parts = line.split(',', 1)
    url = url_parts[0].strip()
    
    # Kiểm tra xem URL có phải là hình ảnh không
    if is_image_url(url):
        new_line, replaced = process_image_url(
            url, url_parts, line_number, image_searcher, keywords
        )
        return new_line, True, replaced
    else:
        logger.debug(f"Line {line_number} contains URL but not an image: {url}")
        return line, False, False


def process_article_lines(
    lines: List[str], 
    keywords: str, 
    image_searcher: ImageSearch
) -> Tuple[List[str], int, int]:
    """
    Xử lý tất cả các dòng trong bài viết để kiểm tra và thay thế hình ảnh
    
    Args:
        lines: Danh sách các dòng trong bài viết
        keywords: Từ khóa để tìm kiếm hình ảnh thay thế
        image_searcher: Đối tượng ImageSearch
        
    Returns:
        Tuple (dòng đã xử lý, số hình ảnh đã kiểm tra, số hình ảnh đã thay thế)
    """
    modified_lines = []
    checked_count = 0
    replaced_count = 0
    
    for i, line in enumerate(lines):
        # Kiểm tra xem dòng có phải là URL không
        if re.match(URL_PATTERN, line):
            processed_line, is_image, replaced = process_url_line(
                line, i+1, image_searcher, keywords
            )
            
            if is_image:
                checked_count += 1
                if replaced:
                    replaced_count += 1
                    
            modified_lines.append(processed_line)
        else:
            modified_lines.append(line)
    
    return modified_lines, checked_count, replaced_count


def validate_input(data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Kiểm tra và trích xuất dữ liệu đầu vào
    
    Args:
        data: Dữ liệu đầu vào
        
    Returns:
        Tuple (bài viết, tiêu đề) hoặc (None, None) nếu không hợp lệ
    """
    if not isinstance(data, dict):
        logger.error(f"Expected dict input but got {type(data)}")
        return None, None
    
    # Trích xuất bài viết và tiêu đề
    article = data.get("article", "")
    title = data.get("title", "")
    
    if not article:
        logger.warning("Empty article received in image processor")
        return None, None
    
    logger.debug(f"Processing article with {len(article)} chars and title: '{title}'")
    return article, title


def image_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Xử lý và xác thực hình ảnh trong bài viết
    
    Args:
        data (dict): Dữ liệu bài viết đã được trích xuất
        
    Returns:
        dict: Dữ liệu bài viết đã được xử lý hình ảnh hoặc dữ liệu gốc nếu không thành công
    """
    logger.info("Starting image processor")
    start_time = time.time()
    
    # Kiểm tra dữ liệu đầu vào
    article, title = validate_input(data)
    if article is None:
        return data
    
    # Khởi tạo đối tượng tìm kiếm hình ảnh
    image_searcher = ImageSearch()
    
    # Chia bài viết thành các dòng
    lines = article.strip().split('\n')
    logger.debug(f"Article split into {len(lines)} lines")
    
    # Trích xuất từ khóa từ bài viết
    full_keywords = extract_keywords(lines, title)
    
    # Select 1-2 random keywords from the full set
    keywords = select_random_keywords(full_keywords)
    logger.info(f"Using random keywords for image search: '{keywords}' (from full keywords: '{full_keywords}')")
    
    # Xử lý các dòng trong bài viết
    modified_lines, checked_count, replaced_count = process_article_lines(
        lines, keywords, image_searcher
    )
    
    # Nối các dòng lại thành bài viết
    data["article"] = '\n'.join(modified_lines)
    
    # Ghi log thông tin xử lý
    processing_time = time.time() - start_time
    logger.info(f"Image processing complete. Checked {checked_count} images, replaced {replaced_count} unreachable images in {processing_time:.2f}s")
    
    return data 