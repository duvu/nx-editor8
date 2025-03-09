#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ví dụ sử dụng VideoSearch để tìm kiếm video YouTube
"""

import os
import sys
import time
from pathlib import Path

# Thêm thư mục cha vào đường dẫn
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import VideoSearch từ module src
from src.video_search import VideoSearch
from src.logger import logger

# Thiết lập mức log thành DEBUG
logger.set_level("DEBUG")

def main():
    """Hàm chính chạy các ví dụ tìm kiếm video"""
    logger.info("Bắt đầu ví dụ tìm kiếm video")
    
    # Khởi tạo VideoSearch
    video_search = VideoSearch()
    
    print("\n=== TÌM KIẾM VIDEO ===")
    keywords = "Việt Nam du lịch"
    print(f"Đang tìm kiếm video với từ khóa: '{keywords}'...")
    
    # Tìm kiếm video
    start_time = time.time()
    videos = video_search.search_videos(keywords, max_results=3)
    elapsed_time = time.time() - start_time
    
    # Hiển thị kết quả
    if videos:
        print(f"Tìm thấy {len(videos)} video trong {elapsed_time:.2f} giây:")
        for i, video in enumerate(videos, 1):
            print(f"\n{i}. {video['title']}")
            print(f"   - URL: {video['url']}")
            print(f"   - Thumbnail: {video['thumbnail']}")
            print(f"   - Thời lượng: {video['duration']} giây")
            print(f"   - Kênh: {video['channel']}")
            
            # Tạo mã HTML nhúng
            embed_html = video_search.get_embed_html(video)
            print(f"\n   Mã HTML để nhúng video:")
            print(f"   {embed_html[:100]}...")
    else:
        print(f"Không tìm thấy video nào với từ khóa '{keywords}'")
    
    print("\n=== KIỂM TRA URL VIDEO ===")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Video nổi tiếng
    
    if videos and videos[0]['url']:
        test_url = videos[0]['url']
        
    is_accessible = video_search.is_video_url_accessible(test_url)
    
    if is_accessible:
        print(f"URL '{test_url}' có thể truy cập được.")
        
        # Lấy thông tin video
        print("\nĐang lấy thông tin video...")
        start_time = time.time()
        video_info = video_search.get_video_info(test_url)
        elapsed_time = time.time() - start_time
        
        if video_info:
            print(f"Lấy thông tin video thành công trong {elapsed_time:.2f} giây:")
            print(f"- Tiêu đề: {video_info.get('title', 'Không xác định')}")
            print(f"- Kênh: {video_info.get('channel', 'Không xác định')}")
            print(f"- Thời lượng: {video_info.get('duration', 0)} giây")
            print(f"- Lượt xem: {video_info.get('view_count', 0)}")
            print(f"- Ngày đăng: {video_info.get('upload_date', 'Không xác định')}")
            print(f"- Độ phân giải: {video_info.get('resolution', 0)}p")
            
            # Tạo mã HTML nhúng
            embed_html = video_search.get_embed_html(video_info)
            print(f"\nMã HTML để nhúng video:")
            print(embed_html)
        else:
            print("Không thể lấy thông tin video.")
    else:
        print(f"URL '{test_url}' không thể truy cập được.")
    
    print("\n=== TÌM VIDEO THAY THẾ ===")
    alternative_keywords = "Hạ Long Bay Vietnam"
    print(f"Đang tìm video thay thế với từ khóa: '{alternative_keywords}'...")
    
    # Tìm video thay thế
    start_time = time.time()
    alt_video = video_search.get_alternative_video(alternative_keywords)
    elapsed_time = time.time() - start_time
    
    if alt_video:
        print(f"Tìm thấy video thay thế trong {elapsed_time:.2f} giây:")
        print(f"- Tiêu đề: {alt_video.get('title', 'Không xác định')}")
        print(f"- Nền tảng: {alt_video.get('platform', 'Không xác định')}")
        print(f"- Thời lượng: {alt_video.get('duration', 0)} giây")
        print(f"- URL: {alt_video.get('url', '')}")
        
        # Tạo mã HTML nhúng
        embed_html = video_search.get_embed_html(alt_video)
        print(f"\nMã HTML để nhúng video:")
        print(embed_html)
    else:
        print(f"Không tìm thấy video thay thế với từ khóa '{alternative_keywords}'")
    
    logger.info("Kết thúc ví dụ tìm kiếm video")

if __name__ == "__main__":
    main() 