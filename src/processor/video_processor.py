#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module xử lý và xác thực video trong bài viết

Module này cung cấp các chức năng để xử lý video trong bài viết, bao gồm:
1. Kiểm tra tính khả dụng của các URL video trong bài viết
2. Thay thế các URL video không khả dụng bằng video thay thế
3. Tự động nhúng mã HTML cho các URL video
4. Tìm kiếm video thay thế dựa trên từ khóa hoặc tiêu đề bài viết

Quy trình xử lý:
1. Phân tích bài viết để tìm các URL video
2. Kiểm tra tính khả dụng của từng URL bằng cách gửi HTTP request
3. Đối với các URL không khả dụng, tìm kiếm video thay thế
4. Thay thế URL trong bài viết với URL mới và mã nhúng HTML

Cách sử dụng:
    from src.processor import video_processor
    
    # Dữ liệu đầu vào là một dict chứa bài viết và tiêu đề
    data = {
        "article": "Nội dung bài viết với các URL video...", 
        "title": "Tiêu đề bài viết"
    }
    
    # Xử lý video
    processed_data = video_processor(data)

Tham số đầu vào:
    data (dict): Dict chứa bài viết ('article') và tiêu đề ('title')

Kết quả trả về:
    dict: Dict chứa bài viết đã được xử lý với các URL video đã được kiểm tra/thay thế

Phụ thuộc:
    - VideoSearch: Lớp hỗ trợ tìm kiếm và xử lý video
    - logger: Module ghi log

Tác giả: NX-Editor8 Team
Phiên bản: 1.0
"""

import re
import time
from typing import Dict, Any, List, Tuple, Optional
from ..logger import logger
from ..video_search import VideoSearch

# Định nghĩa các hằng số
URL_PATTERN = r'^https?://'
VIDEO_PLATFORMS = [
    'youtube.com', 'youtu.be',
    'vimeo.com',
    'dailymotion.com',
    'facebook.com/watch',
    'twitter.com/video',
    'instagram.com/tv',
    'tiktok.com',
    'twitch.tv'
]

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
    keywords = title if title else "generic video"
    logger.info(f"No keywords found in text, using title as keywords: '{keywords}'")
    return keywords


def is_video_url(url: str) -> bool:
    """
    Kiểm tra xem URL có phải là URL video không
    
    Args:
        url: URL cần kiểm tra
        
    Returns:
        True nếu URL có vẻ là URL video, False nếu không phải
    """
    # Kiểm tra xem URL có chứa tên miền của các nền tảng video phổ biến không
    for platform in VIDEO_PLATFORMS:
        if platform in url.lower():
            return True
            
    # Kiểm tra xem URL có chứa các từ khóa liên quan đến video không
    video_keywords = ['video', 'watch', 'embed', 'player']
    for keyword in video_keywords:
        if keyword in url.lower():
            return True
    
    return False


def process_video_url(
    url: str, 
    url_parts: List[str], 
    line_number: int, 
    video_searcher: VideoSearch, 
    keywords: str
) -> Tuple[str, bool]:
    """
    Xử lý URL video: kiểm tra tính khả dụng và thay thế nếu cần
    
    Args:
        url: URL video cần xử lý
        url_parts: Các phần của dòng URL (URL và tham số)
        line_number: Số dòng trong bài viết
        video_searcher: Đối tượng VideoSearch để tìm kiếm video thay thế
        keywords: Từ khóa để tìm kiếm video thay thế
        
    Returns:
        Tuple (dòng mới, đã thay thế hay không)
    """
    logger.debug(f"Checking video URL at line {line_number}: {url}")
    
    # Kiểm tra tính khả dụng của URL
    url_start_time = time.time()
    is_accessible = video_searcher.is_video_url_accessible(url)
    url_check_time = time.time() - url_start_time
    
    logger.debug(f"URL check took {url_check_time:.2f}s, accessible: {is_accessible}")
    
    # Nếu URL không khả dụng, tìm URL thay thế
    if not is_accessible:
        logger.warning(f"Video URL not accessible at line {line_number}: {url}")
        
        # Tìm video thay thế
        search_start_time = time.time()
        alt_video = video_searcher.get_alternative_video(keywords)
        search_time = time.time() - search_start_time
        
        if alt_video and 'url' in alt_video:
            new_url = alt_video['url']
            logger.info(f"Found replacement video in {search_time:.2f}s: {new_url}")
            
            # Tạo dòng mới với URL thay thế
            if len(url_parts) > 1:
                new_line = f"{new_url},{url_parts[1]}"
                logger.debug(f"Replaced URL with parameters: {new_line}")
            else:
                new_line = new_url
                logger.debug(f"Replaced URL: {new_line}")
            
            # Thêm mã nhúng HTML
            if 'embed_html' in alt_video:
                embed_line = f"EMBED:{alt_video['embed_html']}"
                logger.debug(f"Added embed HTML after video URL")
                return f"{new_line}\n{embed_line}", True
            
            return new_line, True
        else:
            logger.warning(f"Failed to find alternative video for '{keywords}'")
    
    # Nếu URL khả dụng, thêm mã nhúng HTML
    elif url:
        try:
            # Lấy thông tin video
            video_info = video_searcher.get_video_info(url)
            
            # Nếu có thông tin video, thêm mã nhúng
            if video_info:
                embed_html = video_searcher.get_embed_html(video_info)
                if embed_html:
                    embed_line = f"EMBED:{embed_html}"
                    logger.debug(f"Added embed HTML for existing video URL")
                    return f"{url}\n{embed_line}", False
        except Exception as e:
            logger.warning(f"Error generating embed code for {url}: {str(e)}")
    
    # Trả về dòng ban đầu nếu không cần thay thế
    return url if len(url_parts) == 1 else f"{url},{url_parts[1]}", False


def process_url_line(
    line: str, 
    line_number: int, 
    video_searcher: VideoSearch, 
    keywords: str
) -> Tuple[str, bool, bool]:
    """
    Xử lý dòng chứa URL
    
    Args:
        line: Dòng cần xử lý
        line_number: Số dòng trong bài viết
        video_searcher: Đối tượng VideoSearch
        keywords: Từ khóa tìm kiếm
        
    Returns:
        Tuple (dòng đã xử lý, có phải video không, đã thay thế không)
    """
    # Bỏ qua các dòng embed
    if line.startswith('EMBED:'):
        return line, False, False
        
    # Tách URL và các tham số (nếu có)
    url_parts = line.split(',', 1)
    url = url_parts[0].strip()
    
    # Kiểm tra xem URL có phải là video không
    if is_video_url(url):
        new_line, replaced = process_video_url(
            url, url_parts, line_number, video_searcher, keywords
        )
        return new_line, True, replaced
    else:
        return line, False, False


def process_article_lines(
    lines: List[str], 
    keywords: str, 
    video_searcher: VideoSearch
) -> Tuple[List[str], int, int]:
    """
    Xử lý tất cả các dòng trong bài viết để kiểm tra và thay thế video
    
    Args:
        lines: Danh sách các dòng trong bài viết
        keywords: Từ khóa để tìm kiếm video thay thế
        video_searcher: Đối tượng VideoSearch
        
    Returns:
        Tuple (dòng đã xử lý, số video đã kiểm tra, số video đã thay thế)
    """
    modified_lines = []
    checked_count = 0
    replaced_count = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Kiểm tra xem dòng có phải là URL không
        if re.match(URL_PATTERN, line) and not line.startswith('EMBED:'):
            processed_line, is_video, replaced = process_url_line(
                line, i+1, video_searcher, keywords
            )
            
            if is_video:
                checked_count += 1
                if replaced:
                    replaced_count += 1
            
            # Xử lý trường hợp khi processed_line chứa nhiều dòng (URL + embed)
            if '\n' in processed_line:
                new_lines = processed_line.split('\n')
                modified_lines.extend(new_lines)
            else:
                modified_lines.append(processed_line)
        else:
            modified_lines.append(line)
            
        i += 1
    
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
        logger.warning("Empty article received in video processor")
        return None, None
    
    logger.debug(f"Processing article with {len(article)} chars and title: '{title}'")
    return article, title


def video_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Xử lý và xác thực video trong bài viết
    
    Args:
        data (dict): Dữ liệu bài viết đã được trích xuất
        
    Returns:
        dict: Dữ liệu bài viết đã được xử lý video hoặc dữ liệu gốc nếu không thành công
    """
    logger.info("Starting video processor")
    start_time = time.time()
    
    # Kiểm tra dữ liệu đầu vào
    article, title = validate_input(data)
    if article is None:
        return data
    
    # Khởi tạo đối tượng tìm kiếm video
    video_searcher = VideoSearch()
    
    # Chia bài viết thành các dòng
    lines = article.strip().split('\n')
    logger.debug(f"Article split into {len(lines)} lines")
    
    # Trích xuất từ khóa từ bài viết
    keywords = extract_keywords(lines, title)
    logger.info(f"Using keywords for video search: '{keywords}'")
    
    # Xử lý các dòng trong bài viết
    modified_lines, checked_count, replaced_count = process_article_lines(
        lines, keywords, video_searcher
    )
    
    # Nối các dòng lại thành bài viết
    data["article"] = '\n'.join(modified_lines)
    
    # Ghi log thông tin xử lý
    processing_time = time.time() - start_time
    logger.info(f"Video processing complete. Checked {checked_count} videos, replaced {replaced_count} unreachable videos in {processing_time:.2f}s")
    
    return data 