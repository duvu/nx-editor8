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
import random
import os
from typing import Dict, Any, List, Tuple, Optional
from ..logger import logger
from ..utils.video_search import VideoSearch
from ..utils.keyword_utils import select_random_keywords

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
    keywords: str,
    creative_commons_only: bool = True
) -> Optional[str]:
    """
    Xử lý URL video: kiểm tra tính khả dụng và thay thế nếu cần.
    Returns None if the video is inaccessible and no suitable CC alternative is found.

    Args:
        url: URL video cần xử lý
        url_parts: Các phần của dòng URL (URL và tham số)
        line_number: Số dòng trong bài viết
        video_searcher: Đối tượng VideoSearch để tìm kiếm video thay thế
        keywords: Từ khóa để tìm kiếm video thay thế
        creative_commons_only: Chỉ sử dụng video có giấy phép Creative Commons

    Returns:
        Optional[str]: Dòng mới với URL hợp lệ hoặc None nếu nên bỏ qua dòng này
    """
    logger.debug(f"Checking video URL at line {line_number}: {url}")

    # Kiểm tra tính khả dụng của URL
    url_start_time = time.time()
    is_accessible = video_searcher.is_video_url_accessible(url)
    url_check_time = time.time() - url_start_time

    logger.debug(f"URL check took {url_check_time:.2f}s, accessible: {is_accessible}")

    # Nếu URL khả dụng, kiểm tra giấy phép CC nếu cần
    if is_accessible and creative_commons_only:
        logger.debug(f"URL {url} is accessible, checking CC license.")
        video_info = video_searcher.get_video_info(url)
        if not video_info or not video_searcher._is_creative_commons(video_info):
            logger.warning(f"Video at line {line_number} ({url}) is accessible but not Creative Commons. Skipping.")
            is_accessible = False # Treat as inaccessible for replacement logic
        else:
             logger.debug(f"Video {url} confirmed as Creative Commons.")


    # Nếu URL không khả dụng (hoặc không phải CC), tìm URL thay thế
    if not is_accessible:
        logger.warning(f"Video URL at line {line_number} ({url}) is not suitable (inaccessible or not CC).")

        # Tìm video thay thế CC
        search_start_time = time.time()
        # Ensure creative_commons_only=True is passed here explicitly
        alt_video = video_searcher.get_alternative_video(keywords, creative_commons_only=True)
        search_time = time.time() - search_start_time

        if alt_video and 'url' in alt_video:
            new_url = alt_video['url']
            license_info = alt_video.get('license', 'creative_commons') # Assume CC
            logger.info(f"Found replacement Creative Commons video in {search_time:.2f}s: {new_url} (License: {license_info})")

            # Tạo dòng mới với URL thay thế và tham số ban đầu hoặc mặc định
            if len(url_parts) > 1:
                new_line = f"{new_url},{url_parts[1]}"
                logger.debug(f"Replaced URL with parameters: {new_line}")
            else:
                # Tạo cài đặt mặc định nếu không có tham số
                duration = alt_video.get('duration', 60)
                if duration > 60:
                    start = max(10, int(duration * 0.2))
                    end = min(start + 20, int(duration * 0.8))
                    excludes = f"0-{start};{end}-{duration}"
                    # Ensure crop parameters are reasonable or omitted if info unavailable
                    crop_param = "crop:300-0-1920-820" # Keep default for now
                    new_line = f"{new_url},{start}-{end},{crop_param},excludes={excludes}"
                else:
                    crop_param = "crop:300-0-1920-820" # Keep default for now
                    new_line = f"{new_url},{crop_param}"

                logger.debug(f"Replaced URL with default parameters: {new_line}")

            return new_line # Return the new line with the replacement video
        else:
            logger.warning(f"Failed to find suitable alternative Creative Commons video for '{keywords}' to replace {url}. Skipping this line.")
            return None # Signal to omit this line entirely

    # Trả về dòng ban đầu nếu URL khả dụng và là CC (hoặc CC không bắt buộc)
    original_line = url if len(url_parts) == 1 else f"{url},{url_parts[1]}"
    logger.debug(f"Keeping original valid video line: {original_line}")
    return original_line


def process_url_line(
    line: str,
    line_number: int,
    video_searcher: VideoSearch,
    keywords: str,
    creative_commons_only: bool = True
) -> Tuple[Optional[str], bool, bool]:
    """
    Xử lý dòng chứa URL. Returns None for the line if it should be omitted.

    Args:
        line: Dòng cần xử lý
        line_number: Số dòng trong bài viết
        video_searcher: Đối tượng VideoSearch
        keywords: Từ khóa tìm kiếm
        creative_commons_only: Chỉ sử dụng video có giấy phép Creative Commons

    Returns:
        Tuple (dòng đã xử lý or None, có phải video không, đã thay thế không)
    """
    # Bỏ qua các dòng embed
    if line.startswith('EMBED:'):
        return line, False, False

    # Tách URL và các tham số (nếu có)
    url_parts = line.split(',', 1)
    url = url_parts[0].strip()

    # Kiểm tra xem URL có phải là video không
    if is_video_url(url):
        processed_line = process_video_url(
            url, url_parts, line_number, video_searcher, keywords, creative_commons_only
        )
        # If processed_line is None, it means replacement failed and line should be skipped
        replaced = (processed_line is not None) and (processed_line != line)
        return processed_line, True, replaced
    else:
        # Not a video URL line
        return line, False, False


def process_article_lines(
    lines: List[str],
    keywords: str,
    video_searcher: VideoSearch,
    creative_commons_only: bool = True
) -> Tuple[List[str], int, int, int]:
    """
    Xử lý từng dòng trong bài viết, omitting lines where video processing fails.

    Args:
        lines: Danh sách các dòng trong bài viết
        keywords: Từ khóa tìm kiếm
        video_searcher: Đối tượng VideoSearch
        creative_commons_only: Chỉ sử dụng video có giấy phép Creative Commons

    Returns:
        Tuple (danh sách dòng mới, số lượng video đã kiểm tra, số lượng video đã thay thế, tổng số video)
    """
    new_lines = []
    checked_count = 0
    replaced_count = 0
    video_line_count = 0 # Count lines identified as video URLs initially

    for i, line in enumerate(lines):
        # Bỏ qua các dòng trống hoặc chỉ chứa khoảng trắng
        if not line.strip():
            new_lines.append(line)
            continue

        # Xử lý dòng nếu là URL (hoặc tiềm năng là URL)
        # Check if line looks like a URL pattern before processing fully
        if re.match(URL_PATTERN, line.split(',')[0].strip()):
            processed_line, is_video, replaced = process_url_line(
                line, i + 1, video_searcher, keywords, creative_commons_only
            )

            if is_video:
                video_line_count += 1
                checked_count += 1
                if replaced:
                    replaced_count += 1
                # Only add the line back if processing didn't result in None
                if processed_line is not None:
                    new_lines.append(processed_line)
                # Else: line is omitted because processing failed
            else:
                # Not a video URL line, keep it
                new_lines.append(line)
        else:
            # Not a URL line, keep it
            new_lines.append(line)

    final_video_count = sum(1 for ln in new_lines if is_video_url(ln.split(',')[0].strip()))
    logger.info(f"Processed {video_line_count} initial video lines. Checked: {checked_count}, Replaced: {replaced_count}. Final video lines: {final_video_count}")
    return new_lines, checked_count, replaced_count, final_video_count


def add_additional_videos(
    lines: List[str],
    keywords: str,
    video_searcher: VideoSearch,
    min_videos: int = 3,
    creative_commons_only: bool = True
) -> List[str]:
    """
    Thêm video bổ sung nếu bài viết chưa đủ số lượng video yêu cầu.
    Skips adding if no suitable Creative Commons video is found.

    Args:
        lines: Danh sách các dòng hiện tại
        keywords: Từ khóa tìm kiếm
        video_searcher: Đối tượng VideoSearch
        min_videos: Số lượng video tối thiểu cần có
        creative_commons_only: Chỉ tìm video Creative Commons

    Returns:
        Danh sách dòng mới với video bổ sung (nếu có)
    """
    # Đếm số lượng video hiện có
    current_video_count = sum(1 for line in lines if is_video_url(line.split(',')[0].strip()))
    logger.info(f"Current video count: {current_video_count}. Minimum required: {min_videos}")

    videos_to_add = min_videos - current_video_count

    if videos_to_add <= 0:
        logger.info("Article already meets or exceeds minimum video count.")
        return lines

    logger.info(f"Attempting to add {videos_to_add} additional Creative Commons video(s).")

    added_count = 0
    # Avoid infinite loops, limit attempts
    max_attempts = videos_to_add * 3 # Try up to 3 times per needed video

    for attempt in range(max_attempts):
        if added_count >= videos_to_add:
            break # Added enough videos

        logger.debug(f"Attempt {attempt + 1} to find additional video using keywords: '{keywords}'")

        # Tìm video thay thế CC
        search_start_time = time.time()
        # Ensure creative_commons_only=True is passed here explicitly
        alt_video = video_searcher.get_alternative_video(keywords, creative_commons_only=True)
        search_time = time.time() - search_start_time

        if alt_video and 'url' in alt_video:
            new_url = alt_video['url']
            license_info = alt_video.get('license', 'creative_commons') # Assume CC
            logger.info(f"Found additional Creative Commons video in {search_time:.2f}s: {new_url} (License: {license_info})")

            # Check if this video URL is already in the article
            if any(new_url in line for line in lines):
                logger.debug(f"Video {new_url} already exists in the article, skipping.")
                continue

            # Tạo dòng mới với URL và tham số mặc định
            duration = alt_video.get('duration', 60)
            if duration > 60:
                start = max(10, int(duration * 0.2))
                end = min(start + 20, int(duration * 0.8))
                excludes = f"0-{start};{end}-{duration}"
                crop_param = "crop:300-0-1920-820" # Keep default for now
                new_line = f"{new_url},{start}-{end},{crop_param},excludes={excludes}"
            else:
                crop_param = "crop:300-0-1920-820" # Keep default for now
                new_line = f"{new_url},{crop_param}"

            logger.debug(f"Adding new video line: {new_line}")
            lines.append(new_line)
            added_count += 1
        else:
            # Failed to find an alternative video this time
            logger.warning(f"Could not find suitable additional Creative Commons video (Attempt {attempt + 1}).")
            # No fallback, just continue trying if attempts remain

    if added_count < videos_to_add:
        logger.warning(f"Could only add {added_count} out of {videos_to_add} requested additional videos.")

    return lines


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


def video_processor(data: Dict[str, Any], creative_commons_only: bool = True) -> Dict[str, Any]:
    """
    Xử lý và xác thực video trong bài viết
    
    Args:
        data (dict): Dữ liệu bài viết đã được trích xuất
        creative_commons_only: Chỉ sử dụng video có giấy phép Creative Commons
        
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
    full_keywords = extract_keywords(lines, title)
    
    # Select 1-2 random keywords from the full set
    keywords = select_random_keywords(full_keywords)
    license_text = "Creative Commons" if creative_commons_only else "Standard"
    logger.info(f"Using random keywords for video search: '{keywords}' (from full keywords: '{full_keywords}', License: {license_text})")
    
    # Xử lý các dòng trong bài viết
    modified_lines, checked_count, replaced_count, video_count = process_article_lines(
        lines, keywords, video_searcher, creative_commons_only
    )
    
    # Kiểm tra xem có đủ số lượng video tối thiểu không (ít nhất 3 video)
    MIN_VIDEOS = 3
    logger.info(f"Article has {video_count} videos, minimum required: {MIN_VIDEOS}")
    
    if video_count < MIN_VIDEOS:
        # Thêm video cho đến khi đạt số lượng tối thiểu
        logger.info(f"Adding {MIN_VIDEOS - video_count} more videos to reach minimum")
        modified_lines = add_additional_videos(modified_lines, keywords, video_searcher, MIN_VIDEOS, creative_commons_only)
    
    # Nối các dòng lại thành bài viết
    data["article"] = '\n'.join(modified_lines)
    
    # Ghi log thông tin xử lý
    processing_time = time.time() - start_time
    logger.info(f"Video processing complete in {processing_time:.2f}s")
    
    return data 