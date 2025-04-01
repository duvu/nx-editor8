#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module xử lý và tích hợp video từ Pexels vào bài viết

Module này cung cấp các chức năng để tìm kiếm, tải xuống và tích hợp video từ Pexels, bao gồm:
1. Tìm kiếm video chất lượng cao từ Pexels dựa trên từ khóa
2. Thêm video Pexels vào các bài viết không có hoặc thiếu video
3. Kiểm tra tính khả dụng của các URL video Pexels

Quy trình xử lý:
1. Phân tích bài viết để trích xuất từ khóa
2. Tìm kiếm video liên quan từ Pexels
3. Thêm video Pexels vào bài viết theo định dạng phù hợp

Cách sử dụng:
    from src.processor import pexels_video_processor
    
    # Dữ liệu đầu vào là một dict chứa bài viết và tiêu đề
    data = {
        "article": "Nội dung bài viết...", 
        "title": "Tiêu đề bài viết"
    }
    
    # Xử lý và thêm video Pexels
    processed_data = pexels_video_processor(data)

Tham số đầu vào:
    data (dict): Dict chứa bài viết ('article') và tiêu đề ('title')

Kết quả trả về:
    dict: Dict chứa bài viết đã được xử lý với các URL video Pexels đã được thêm vào

Phụ thuộc:
    - PexelsVideoSearch: Lớp hỗ trợ tìm kiếm và xử lý video từ Pexels
    - logger: Module ghi log
    - select_random_keywords: Function from keyword_utils

Tác giả: NX-Editor8 Team
Phiên bản: 1.0
"""

import os
import re
import time
import random
from typing import Dict, Any, List, Tuple, Optional
from ..logger import logger
from ..utils.pexels_video_search import PexelsVideoSearch
from ..utils.keyword_utils import select_random_keywords

# Định nghĩa các hằng số
MIN_VIDEOS = 2  # Số lượng video tối thiểu cần có trong bài viết
MAX_VIDEOS = 5  # Số lượng video tối đa sẽ thêm vào bài viết
MIN_VIDEO_DURATION = 10  # Thời lượng tối thiểu của video (giây)
MAX_VIDEO_DURATION = 60  # Thời lượng tối đa của video (giây)


def validate_input(data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Kiểm tra và trích xuất dữ liệu đầu vào
    
    Args:
        data: Dữ liệu đầu vào cần kiểm tra
        
    Returns:
        Tuple (nội dung bài viết, tiêu đề)
    """
    # Kiểm tra dữ liệu đầu vào
    if not isinstance(data, dict):
        logger.error(f"Expected dict input for pexels_video_processor but got {type(data)}")
        return None, None
    
    # Lấy nội dung bài viết và tiêu đề
    article = data.get("article", "")
    title = data.get("title", "")
    
    if not article:
        logger.warning("Empty article content received in pexels_video_processor")
        return None, None
    
    return article, title


def extract_keywords(lines: List[str], title: str) -> str:
    """
    Trích xuất từ khóa từ bài viết
    
    Args:
        lines: Danh sách các dòng trong bài viết
        title: Tiêu đề bài viết
        
    Returns:
        Từ khóa phù hợp để tìm kiếm video
    """
    # Ưu tiên lấy từ khóa từ dòng đầu tiên bắt đầu bằng '#'
    for line in lines:
        if line.startswith('#'):
            keywords = line.strip('#').strip()
            logger.info(f"Found keywords in article heading: '{keywords}'")
            return keywords
    
    # Nếu không tìm thấy từ khóa từ dòng bắt đầu bằng '#', sử dụng tiêu đề
    if title:
        logger.info(f"Using title as keywords: '{title}'")
        return title
    
    # Nếu không có tiêu đề, tìm kiếm từ khóa trong nội dung
    # Lấy tối đa 10 dòng đầu tiên và tìm kiếm từ khóa phổ biến
    text_content = ' '.join([line for line in lines[:10] if not line.startswith('http')])
    
    # Loại bỏ các ký tự đặc biệt và chuẩn hóa dữ liệu
    text_content = re.sub(r'[^\w\s]', ' ', text_content)
    words = text_content.split()
    
    if words:
        # Lấy tối đa 5 từ có ý nghĩa
        keywords = ' '.join(words[:5])
        logger.info(f"Extracted keywords from content: '{keywords}'")
        return keywords
    
    # Nếu không tìm thấy từ khóa, sử dụng từ khóa chung
    default_keywords = "nature landscape beautiful"
    logger.warning(f"No keywords found, using default: '{default_keywords}'")
    return default_keywords


def count_existing_videos(lines: List[str]) -> Tuple[int, List[int]]:
    """
    Đếm số lượng video đã có trong bài viết
    
    Args:
        lines: Danh sách các dòng trong bài viết
        
    Returns:
        Tuple (số lượng video, danh sách vị trí các dòng video)
    """
    video_count = 0
    video_line_indices = []
    
    # Đếm số lượng URL video trong bài viết
    video_platforms = ['youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com']
    
    for i, line in enumerate(lines):
        if line.startswith('http://') or line.startswith('https://'):
            for platform in video_platforms:
                if platform in line.lower():
                    video_count += 1
                    video_line_indices.append(i)
                    break
    
    logger.info(f"Found {video_count} existing videos in the article")
    return video_count, video_line_indices


def format_video_url(video: Dict[str, Any]) -> str:
    """
    Định dạng URL video để thêm vào bài viết
    
    Args:
        video: Thông tin video từ Pexels
        
    Returns:
        URL video đã được định dạng theo yêu cầu
    """
    url = video.get('url', '')
    duration = video.get('duration', 0)
    
    # Nếu thời lượng quá dài, tạo các phân đoạn
    if duration > 30:
        # Tạo 4 phân đoạn video, tránh 5 giây đầu tiên (thường có logo)
        segments = []
        segment_duration = (duration - 5) // 4
        
        start_time = 5  # Bắt đầu từ giây thứ 5
        for i in range(4):
            end_time = start_time + segment_duration
            segments.append(f"{start_time}-{end_time}")
            start_time = end_time + 1
        
        # Tạo phần excludes để loại bỏ các phần không sử dụng
        excludes = []
        current_pos = 0
        
        for i, segment in enumerate(segments):
            start, end = map(int, segment.split('-'))
            if i % 2 == 1:  # Chỉ sử dụng phân đoạn 0, 2 - loại bỏ phân đoạn 1, 3
                excludes.append(f"{start}-{end}")
            
        # Thêm phần loại trừ cho 5 giây đầu và phần còn lại nếu có
        if duration > segments[-1].split('-')[1]:
            excludes.append(f"0-5")
            excludes.append(f"{int(segments[-1].split('-')[1]) + 1}-{duration}")
        
        # Định dạng URL với crop và excludes
        formatted_url = f"{url},crop:300-0-1920-820,excludes={';'.join(excludes)}"
    else:
        # Nếu video ngắn, sử dụng toàn bộ video
        formatted_url = f"{url},crop:300-0-1920-820"
    
    return formatted_url


def add_pexels_videos(lines: List[str], keywords: str, pexels_searcher: PexelsVideoSearch, min_videos: int = MIN_VIDEOS) -> List[str]:
    """
    Thêm video Pexels vào bài viết
    
    Args:
        lines: Danh sách các dòng trong bài viết
        keywords: Từ khóa để tìm kiếm video
        pexels_searcher: Đối tượng PexelsVideoSearch để tìm kiếm video
        min_videos: Số lượng video tối thiểu cần có
        
    Returns:
        Danh sách các dòng sau khi đã thêm video
    """
    # Đếm số lượng video hiện có
    video_count, video_line_indices = count_existing_videos(lines)
    
    # Nếu đã đủ số lượng video tối thiểu, không cần thêm
    if video_count >= min_videos:
        logger.info(f"Article already has {video_count} videos (≥{min_videos}). No need to add more.")
        return lines
    
    # Tính số lượng video cần thêm
    videos_to_add = min(min_videos - video_count, MAX_VIDEOS)
    logger.info(f"Need to add {videos_to_add} more videos")
    
    # Tìm kiếm video từ Pexels
    videos = pexels_searcher.search_videos(
        keywords, 
        max_results=videos_to_add * 2,  # Tìm gấp đôi để có nhiều lựa chọn
        min_duration=MIN_VIDEO_DURATION,
        max_duration=MAX_VIDEO_DURATION
    )
    
    if not videos:
        logger.warning(f"No videos found for keywords: '{keywords}'")
        return lines
    
    # Chọn ngẫu nhiên các video để thêm vào
    # Đảm bảo không trùng lặp bằng cách sử dụng set
    existing_urls = {line for line in lines if line.startswith('http')}
    
    # Lọc video không trùng với các URL đã có
    new_videos = [v for v in videos if v.get('url') not in existing_urls]
    
    # Chọn ngẫu nhiên số lượng video cần thêm
    if len(new_videos) > videos_to_add:
        selected_videos = random.sample(new_videos, videos_to_add)
    else:
        selected_videos = new_videos[:videos_to_add]
    
    if not selected_videos:
        logger.warning("No suitable videos found to add")
        return lines
    
    logger.info(f"Adding {len(selected_videos)} Pexels videos to the article")
    
    # Định dạng URL video và thêm vào bài viết
    formatted_video_urls = [format_video_url(video) for video in selected_videos]
    
    # Xác định vị trí thêm video
    if video_line_indices:
        # Thêm video sau video cuối cùng hiện có
        last_video_pos = video_line_indices[-1]
        
        for i, url in enumerate(formatted_video_urls):
            insert_pos = last_video_pos + 1 + i
            lines.insert(insert_pos, url)
            logger.debug(f"Added Pexels video at position {insert_pos}: {url[:60]}...")
    else:
        # Nếu không có video nào, thêm vào đầu bài viết sau dòng tiêu đề (nếu có)
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith('#'):
                insert_pos = i + 1
                break
        
        # Thêm một dòng trống trước video đầu tiên
        lines.insert(insert_pos, "")
        insert_pos += 1
        
        # Thêm comment giải thích
        lines.insert(insert_pos, "# Video từ Pexels:")
        insert_pos += 1
        
        # Thêm các video
        for i, url in enumerate(formatted_video_urls):
            lines.insert(insert_pos + i, url)
            logger.debug(f"Added Pexels video at position {insert_pos + i}: {url[:60]}...")
        
        # Thêm một dòng trống sau video cuối cùng
        lines.insert(insert_pos + len(formatted_video_urls), "")
    
    return lines


def pexels_video_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Xử lý và thêm video Pexels vào bài viết
    
    Args:
        data: Dữ liệu bài viết đầu vào
        
    Returns:
        Dữ liệu bài viết đã được xử lý
    """
    logger.info("Starting Pexels video processor")
    start_time = time.time()
    
    # Kiểm tra dữ liệu đầu vào
    article, title = validate_input(data)
    if article is None:
        return data
    
    # Chia bài viết thành các dòng
    lines = article.strip().split('\n')
    logger.debug(f"Article split into {len(lines)} lines")
    
    # Trích xuất từ khóa từ bài viết
    full_keywords = extract_keywords(lines, title)
    
    # Select 1-2 random keywords from the full set
    keywords = select_random_keywords(full_keywords)
    logger.info(f"Using random keywords for Pexels video search: '{keywords}' (from full keywords: '{full_keywords}')")
    
    # Khởi tạo đối tượng tìm kiếm video Pexels
    api_key = os.environ.get('PEXELS_API_KEY', '')
    if not api_key:
        logger.error("No Pexels API key found. Set PEXELS_API_KEY environment variable.")
        return data
        
    pexels_searcher = PexelsVideoSearch(api_key=api_key)
    
    # Thêm video Pexels vào bài viết
    modified_lines = add_pexels_videos(lines, keywords, pexels_searcher, MIN_VIDEOS)
    
    # Nối các dòng lại thành bài viết
    data["article"] = '\n'.join(modified_lines)
    
    # Ghi log thông tin xử lý
    processing_time = time.time() - start_time
    logger.info(f"Pexels video processing completed in {processing_time:.2f}s")
    
    return data 