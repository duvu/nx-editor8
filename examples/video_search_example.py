#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import traceback

# Thêm thư mục gốc vào sys.path để import các module trong src
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.video_search import VideoSearch
from src.logger import logger

def main():
    """
    Ví dụ sử dụng VideoSearch để tìm kiếm và xử lý video
    """
    # Thiết lập logger
    logger.set_level("INFO")
    logger.info("Bắt đầu ví dụ tìm kiếm video")
    
    try:
        # Khởi tạo đối tượng VideoSearch
        video_searcher = VideoSearch()
        
        # 1. Tìm kiếm video với từ khóa
        print("\n=== TÌM KIẾM VIDEO ===")
        keywords = "Việt Nam du lịch"
        max_results = 3
        
        print(f"Đang tìm kiếm video với từ khóa: '{keywords}'...")
        start_time = time.time()
        results = video_searcher.search_videos(keywords, max_results=max_results)
        search_time = time.time() - start_time
        
        # Hiển thị kết quả
        if results:
            print(f"Tìm thấy {len(results)} video trong {search_time:.2f} giây:")
            
            for i, video in enumerate(results):
                print(f"\nVideo {i+1}: {video['title']}")
                print(f"- Nền tảng: {video['platform']}")
                print(f"- Thời lượng: {video['duration']} giây")
                print(f"- Độ phân giải: {video['resolution']}p")
                if video['upload_date']:
                    print(f"- Ngày đăng: {video['upload_date']}")
                print(f"- URL: {video['url']}")
                print(f"- Thumbnail: {video['thumbnail']}")
                print(f"- Embed URL: {video['embed_url']}")
        else:
            print(f"Không tìm thấy video nào với từ khóa '{keywords}'")
        
        # 2. Kiểm tra URL video có thể truy cập
        print("\n=== KIỂM TRA URL VIDEO ===")
        if results:
            test_url = results[0]['url']
            print(f"Đang kiểm tra URL: {test_url}")
            
            start_time = time.time()
            is_accessible = video_searcher.is_video_url_accessible(test_url)
            check_time = time.time() - start_time
            
            if is_accessible:
                print(f"URL có thể truy cập được (kiểm tra trong {check_time:.2f} giây)")
            else:
                print(f"URL không thể truy cập được (kiểm tra trong {check_time:.2f} giây)")
        
        # 3. Tìm video thay thế
        print("\n=== TÌM VIDEO THAY THẾ ===")
        alt_keywords = "Hạ Long Bay Vietnam"
        print(f"Đang tìm video thay thế với từ khóa: '{alt_keywords}'...")
        
        start_time = time.time()
        alt_video = video_searcher.get_alternative_video(alt_keywords)
        alt_time = time.time() - start_time
        
        if alt_video:
            print(f"Tìm thấy video thay thế trong {alt_time:.2f} giây:")
            print(f"- Tiêu đề: {alt_video['title']}")
            print(f"- Nền tảng: {alt_video['platform']}")
            print(f"- Thời lượng: {alt_video['duration']} giây")
            print(f"- URL: {alt_video['url']}")
            
            # Lấy mã HTML để nhúng video
            embed_html = video_searcher.get_embed_html(alt_video)
            print(f"\nMã HTML để nhúng video:")
            print(embed_html)
        else:
            print(f"Không tìm thấy video thay thế với từ khóa '{alt_keywords}'")
        
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        traceback.print_exc()
    
    logger.info("Kết thúc ví dụ tìm kiếm video")

if __name__ == "__main__":
    main() 