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
from typing import Dict, Any, List, Tuple, Optional
from ..logger import logger
from ..utils.video_search import VideoSearch

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
            
            # Bỏ phần thêm mã nhúng HTML
            return new_line, True
        else:
            logger.warning(f"Failed to find alternative video for '{keywords}'")
    
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
) -> Tuple[List[str], int, int, int]:
    """
    Xử lý tất cả các dòng trong bài viết để kiểm tra và thay thế video
    
    Args:
        lines: Danh sách các dòng trong bài viết
        keywords: Từ khóa để tìm kiếm video thay thế
        video_searcher: Đối tượng VideoSearch
        
    Returns:
        Tuple (dòng đã xử lý, số video đã kiểm tra, số video đã thay thế, số video có trong bài viết)
    """
    modified_lines = []
    checked_count = 0
    replaced_count = 0
    video_count = 0
    
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
                video_count += 1
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
    
    return modified_lines, checked_count, replaced_count, video_count


def add_additional_videos(
    lines: List[str],
    keywords: str,
    video_searcher: VideoSearch,
    min_videos: int = 3
) -> List[str]:
    """
    Thêm video bổ sung vào bài viết cho đến khi đạt số lượng tối thiểu
    
    Args:
        lines: Danh sách các dòng trong bài viết đã xử lý
        keywords: Từ khóa để tìm kiếm video
        video_searcher: Đối tượng VideoSearch
        min_videos: Số lượng video tối thiểu cần có trong bài viết
        
    Returns:
        Danh sách các dòng sau khi thêm video
    """
    logger.info(f"Adding additional videos to reach minimum of {min_videos} videos")
    
    # Tìm vị trí thích hợp để thêm video
    # Thêm video vào trước phần nội dung chính
    # Tìm các đặc điểm của phần nội dung như dòng trống, dòng đếm từ, hoặc dòng bắt đầu đoạn văn
    insert_position = 0
    
    # Tìm vị trí của các URL video hiện có
    existing_video_positions = []
    for i, line in enumerate(lines):
        if line.startswith('http') and is_video_url(line.split(',')[0].strip()):
            existing_video_positions.append(i)
    
    if existing_video_positions:
        # Nếu đã có video, chèn vào sau video cuối cùng hiện có
        insert_position = existing_video_positions[-1] + 1
        
        # Điều chỉnh vị trí nếu ngay sau video là hình ảnh
        while insert_position < len(lines) and lines[insert_position].startswith('http'):
            insert_position += 1
            
        # Thêm một dòng trống nếu không có
        if insert_position < len(lines) and lines[insert_position] != "":
            lines.insert(insert_position, "")
            insert_position += 1
    else:
        # Nếu không có video nào, tìm vị trí sau phần metadata và thumbnail
        for i, line in enumerate(lines):
            if line.startswith('-') and 'từ' in line:  # Dòng đếm từ
                insert_position = i
                break
            elif i > 5 and line == "" and i+1 < len(lines) and lines[i+1] != "" and not lines[i+1].startswith(('http', '+', '#')):
                # Dòng trống trước nội dung chính
                insert_position = i
                break
    
    # Nếu không tìm thấy vị trí thích hợp, thêm vào đầu bài viết sau phần metadata
    if insert_position == 0:
        for i, line in enumerate(lines):
            if i > 3 and line == "" and i+1 < len(lines) and lines[i+1].startswith('+'):
                insert_position = i
                break
    
    # Số lượng video cần thêm
    videos_to_add = min_videos - len([l for l in lines if is_video_url(l.split(',')[0].strip()) and not l.startswith('EMBED:')])
    
    if videos_to_add <= 0:
        logger.info("No additional videos needed")
        return lines
    
    logger.info(f"Need to add {videos_to_add} more videos at position {insert_position}")
    
    # Thêm mỗi video
    videos_added = 0
    attempts = 0
    max_attempts = videos_to_add * 3  # Giới hạn số lần thử để tránh vòng lặp vô hạn
    
    while videos_added < videos_to_add and attempts < max_attempts:
        attempts += 1
        
        # Tìm video mới
        logger.debug(f"Searching for additional video {videos_added + 1}/{videos_to_add}")
        alt_video = video_searcher.get_alternative_video(keywords)
        
        if alt_video and 'url' in alt_video:
            new_url = alt_video['url']
            
            # Kiểm tra xem URL này đã có trong bài viết chưa
            if new_url in '\n'.join(lines):
                logger.debug(f"Video URL already exists in article, skipping: {new_url}")
                continue
                
            logger.info(f"Adding new video: {new_url}")
            
            # Tạo dòng mới với cấu trúc phù hợp (URL + tham số)
            # Format: URL,10-16;25-31;40-46,crop:300-0-1920-820,excludes=0-10;16-25;31-40;46-60
            
            # Lấy thời lượng thực tế từ video nếu có, nếu không thì sử dụng giá trị mặc định là 60s
            video_duration = alt_video.get('duration', 60)
            logger.debug(f"Video duration: {video_duration} seconds")
            
            # Đảm bảo video_duration là một số hợp lệ và > 20 giây
            try:
                video_duration = int(video_duration)
                if video_duration < 20:
                    video_duration = 60  # Nếu video quá ngắn, sử dụng giá trị mặc định
            except (ValueError, TypeError):
                video_duration = 60  # Nếu không chuyển đổi được, sử dụng giá trị mặc định
                
            logger.debug(f"Using video duration: {video_duration} seconds for segment calculation")
            
            # Giới hạn thời lượng tối đa để tránh vùng outro (thường ở cuối video)
            max_end_time = min(video_duration - 5, 120)  # Giới hạn tối đa 120s hoặc trước outro 5s
            
            # Tạo 3 đoạn thời gian ngẫu nhiên, mỗi đoạn 6 giây
            segments = []
            
            # Đảm bảo các đoạn không vượt quá thời lượng video
            # Đoạn đầu tiên bắt đầu từ giây thứ 5 trở đi để tránh phần intro
            max_start1 = min(video_duration // 4, 15)  # 1/4 đầu video hoặc tối đa 15s
            start1 = random.randint(5, max_start1)
            end1 = min(start1 + 6, max_end_time)
            segments.append((start1, end1))
            
            # Đoạn thứ hai bắt đầu từ giữa video
            max_start2 = min(video_duration // 2, 45)  # Nửa video hoặc tối đa 45s
            start2 = random.randint(end1 + 5, max_start2)
            end2 = min(start2 + 6, max_end_time)
            segments.append((start2, end2))
            
            # Đoạn thứ ba bắt đầu gần cuối nhưng tránh outro
            max_start3 = min(video_duration * 3 // 4, 90)  # 3/4 video hoặc tối đa 90s
            start3 = random.randint(end2 + 5, max_start3)
            end3 = min(start3 + 6, max_end_time)
            segments.append((start3, end3))
            
            # Loại bỏ các segment không hợp lệ (nếu video quá ngắn)
            segments = [(start, end) for start, end in segments if start < end and end <= max_end_time]
            
            # Nếu không có segment nào hợp lệ, tạo một segment mặc định
            if not segments:
                segments = [(5, 11)]
            
            # Sắp xếp các đoạn theo thứ tự thời gian
            segments.sort()
            
            # Tạo chuỗi thời gian theo định dạng "start1-end1;start2-end2;start3-end3"
            time_ranges = ";".join([f"{start}-{end}" for start, end in segments])
            
            # Tạo danh sách excludes để loại bỏ các khoảng giữa các đoạn đã chọn
            excludes = []
            
            # Loại bỏ phần đầu (0s đến đoạn đầu tiên)
            if segments[0][0] > 0:
                excludes.append(f"0-{segments[0][0]}")
                
            # Loại bỏ các khoảng giữa các đoạn
            for i in range(len(segments) - 1):
                excludes.append(f"{segments[i][1]}-{segments[i+1][0]}")
                
            # Loại bỏ phần cuối (từ đoạn cuối đến hết)
            excludes.append(f"{segments[-1][1]}-{video_duration}")
            
            # Tạo chuỗi excludes
            excludes_str = "excludes=" + ";".join(excludes)
            
            # Khung hình cắt theo yêu cầu
            crop = "crop:300-0-1920-820"
            
            # Tạo dòng URL hoàn chỉnh với tham số
            formatted_url = f"{new_url},{time_ranges},{crop},{excludes_str}"
            
            logger.debug(f"Created video URL with time segments: {time_ranges}")
            logger.debug(f"Excludes: {excludes_str}")
            
            # Thêm dòng mới
            new_lines = []
            new_lines.append("")  # Dòng trống trước video
            new_lines.append(formatted_url)
            
            # Chèn vào vị trí đã xác định
            lines[insert_position:insert_position] = new_lines
            insert_position += len(new_lines)
            videos_added += 1
        else:
            logger.warning(f"Failed to find additional video for '{keywords}'")
            # Tạm dừng để tránh gửi quá nhiều requests
            time.sleep(1)
    
    if videos_added > 0:
        logger.info(f"Successfully added {videos_added} videos to the article")
    else:
        logger.warning("Could not add any additional videos to the article")
        
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
    modified_lines, checked_count, replaced_count, video_count = process_article_lines(
        lines, keywords, video_searcher
    )
    
    # Kiểm tra xem có đủ số lượng video tối thiểu không (ít nhất 3 video)
    MIN_VIDEOS = 3
    logger.info(f"Article has {video_count} videos, minimum required: {MIN_VIDEOS}")
    
    if video_count < MIN_VIDEOS:
        # Thêm video cho đến khi đạt số lượng tối thiểu
        logger.info(f"Adding {MIN_VIDEOS - video_count} more videos to reach minimum")
        modified_lines = add_additional_videos(modified_lines, keywords, video_searcher, MIN_VIDEOS)
    
    # Nối các dòng lại thành bài viết
    data["article"] = '\n'.join(modified_lines)
    
    # Ghi log thông tin xử lý
    processing_time = time.time() - start_time
    logger.info(f"Video processing complete. Checked {checked_count} videos, replaced {replaced_count} unreachable videos, ensured minimum {MIN_VIDEOS} videos in {processing_time:.2f}s")
    
    return data 