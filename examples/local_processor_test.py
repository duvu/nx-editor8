#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kiểm tra chuỗi xử lý processor cục bộ, không kết nối RabbitMQ

Script này cho phép chạy chuỗi xử lý processor trên dữ liệu đầu vào cục bộ
mà không cần kết nối đến RabbitMQ. Hữu ích cho phát triển và kiểm thử nhanh.

Cách sử dụng:
    python examples/local_processor_test.py [input_file]

    Nếu không cung cấp input_file, script sẽ sử dụng dữ liệu mẫu
"""

import os
import sys
import time
import json
import traceback
import random
from datetime import datetime
from pathlib import Path
import argparse

# Thêm thư mục gốc vào đường dẫn Python
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import các module cần thiết từ dự án
from src.processor_chain import ProcessorChain
from src.logger import logger
from src.processor import extract_article, image_processor, script_processor, s2j_processor, video_processor

# Thiết lập mức log
logger.set_level("DEBUG")

def error_handler(message, error, processor_name):
    """Xử lý lỗi trong quá trình xử lý dữ liệu"""
    logger.error(f"Lỗi trong processor '{processor_name}': {str(error)}")
    logger.error(f"Stack trace: {traceback.format_exc()}")
    
    # Tạo ID lỗi duy nhất để dễ theo dõi
    error_id = f"ERR-{int(time.time())}-{random.randint(1000, 9999)}"
    logger.error(f"Error ID: {error_id}")
    
    if isinstance(message, dict):
        message["processing_error"] = {
            "error_id": error_id,
            "processor": processor_name,
            "error": str(error),
            "timestamp": time.time(),
            "error_type": type(error).__name__
        }
        logger.info(f"Đã thêm thông tin lỗi vào message với error_id: {error_id}")
        return message  # Tiếp tục xử lý với thông tin lỗi được thêm vào
    
    logger.warning(f"Message không phải là dict, không thể thêm thông tin lỗi. Loại: {type(message)}")
    return None  # Dừng xử lý nếu message không phải là dict

def create_complete_pipeline():
    """Tạo và cấu hình pipeline xử lý hoàn chỉnh"""
    logger.info("Đang tạo pipeline xử lý")
    
    chain = ProcessorChain("local_pipeline")
    
    # Bỏ qua extract_article processor theo yêu cầu
    # logger.debug("Thêm extract_article processor vào pipeline")
    # chain.add_processor(extract_article, "extract_article")
    logger.info("Bỏ qua extract_article processor theo yêu cầu")
    
    logger.debug("Thêm image_processor vào pipeline")
    chain.add_processor(image_processor, "image_processor")
    
    logger.debug("Thêm video_processor vào pipeline")
    chain.add_processor(video_processor, "video_processor")
    
    logger.debug("Thêm script_processor vào pipeline")
    chain.add_processor(script_processor, "script_processor")
    
    logger.debug("Thêm s2j_processor vào pipeline")
    chain.add_processor(s2j_processor, "script2json")
    
    logger.debug("Thiết lập xử lý lỗi")
    chain.set_error_handler(error_handler)
    
    logger.info("Đã tạo xong pipeline xử lý")
    return chain

def load_input_data(file_path=None):
    """Tải dữ liệu đầu vào từ file sample2.txt"""
    # Cố định đầu vào từ file sample2.txt
    logger.info("Cố định đầu vào từ file sample2.txt")
    sample_file = os.path.join(project_root, "sample2.txt")
    
    if not os.path.exists(sample_file):
        logger.error(f"Không tìm thấy file mẫu: {sample_file}")
        logger.warning("Sử dụng dữ liệu mẫu cứng")
        return {
            "article": """
TÀI CHÍNH KINH DOANH: 2025 - NHỮNG QUAN ĐIỂM CỦA ÔNG TRUMP SẼ ĐỊNH HÌNH LẠI TRẬT TỰ KINH TẾ TOÀN CẦU?

#Donald Trump, thuế quan, chiến tranh thương mại, di cư, biên giới

+playlist: Thời sự thế giới
+description: Năm 2025, mang theo nhiều kỳ vọng nhưng cũng không ít lo ngại
+thumbnail:https://static.kinhtedothi.vn/w960/images/upload/2021/12/22/trump-nham-chuc-biden.png

Năm 2025, mang theo nhiều kỳ vọng nhưng cũng không ít lo ngại, về những thách thức có thể định hình kinh tế toàn cầu. Từ bất ổn địa chính trị, vấn đề nhập cư đến tiến bộ công nghệ và bất bình đẳng kinh tế, thế giới đang đối mặt với hàng loạt thách thức chưa từng có.
            """,
            "title": "Mẫu: Donald Trump và kinh tế toàn cầu"
        }
    
    # Đọc file sample2.txt
    logger.info(f"Đang đọc dữ liệu mẫu từ: {sample_file}")
    with open(sample_file, 'r', encoding='utf-8') as f:
        content = f.read()
    return {"article": content, "title": "Donald Trump và kinh tế toàn cầu - sample2.txt"}

def save_output(data, output_file=None):
    """Lưu kết quả ra file"""
    # Luôn sử dụng sample2.json làm file đầu ra
    output_file = os.path.join(project_root, "sample2.json")
    
    logger.info(f"Lưu kết quả ra file: {output_file}")
    
    # Lưu ra file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Đã lưu kết quả ra file: {output_file}")
    return output_file

def display_summary(result, input_data):
    """Hiển thị tóm tắt kết quả xử lý"""
    logger.info("=== TÓM TẮT KẾT QUẢ XỬ LÝ ===")
    
    if not result:
        logger.error("Xử lý không thành công, không có kết quả")
        return
    
    if "processing_error" in result:
        logger.warning(f"Xử lý có lỗi: {result['processing_error']['error']}")
        logger.warning(f"Lỗi xảy ra tại processor: {result['processing_error']['processor']}")
    
    # Hiển thị thông tin video
    if "video" in result and isinstance(result["video"], list):
        videos = result["video"]
        logger.info(f"Số video: {len(videos)}")
        for i, video in enumerate(videos, 1):
            media_clips = video.get("media_clips", [])
            video_count = sum(1 for clip in media_clips if clip.get("type") == "video")
            image_count = sum(1 for clip in media_clips if clip.get("type") == "image")
            logger.info(f"Video {i}: {video_count} clip video, {image_count} clip hình ảnh")
    
    # Hiển thị các nội dung từ input đến output
    if "title" in input_data and "title" in result:
        logger.info(f"Tiêu đề: '{input_data['title']}' -> '{result['title']}'")
    
    if "keyword" in result:
        logger.info(f"Từ khóa: {result['keyword']}")
    
    if "description" in result:
        description = result["description"]
        if len(description) > 100:
            description = description[:97] + "..."
        logger.info(f"Mô tả: {description}")

def main():
    """Hàm chính của chương trình"""
    # Chỉ giữ lại tùy chọn trợ giúp
    parser = argparse.ArgumentParser(description="Chạy chuỗi xử lý processor cục bộ")
    parser.add_argument("-h", "--help", action="help", help="Hiển thị thông báo trợ giúp này và thoát")
    args = parser.parse_args()
    
    start_time = time.time()
    logger.info(f"===== BẮT ĐẦU XỬ LÝ LOCAL =====")
    
    try:
        # Tải dữ liệu đầu vào từ sample2.txt
        input_data = load_input_data()
        
        # Tạo pipeline xử lý (bỏ qua extract_article)
        pipeline = create_complete_pipeline()
        
        # Xử lý dữ liệu
        logger.info("Bắt đầu xử lý dữ liệu")
        process_start = time.time()
        result = pipeline.process(input_data)
        process_time = time.time() - process_start
        logger.info(f"Hoàn thành xử lý dữ liệu trong {process_time:.2f} giây")
        
        # Kiểm tra kết quả
        if result is None:
            logger.error("Xử lý không thành công, kết quả là None")
            return 1
        
        # Hiển thị tóm tắt kết quả
        display_summary(result, input_data)
        
        # Lưu kết quả vào sample2.json
        output_file = save_output(result)
        logger.info(f"Đã lưu kết quả tại: {output_file}")
        
    except Exception as e:
        logger.error(f"Lỗi không mong muốn: {str(e)}")
        logger.error(traceback.format_exc())
        return 1
    
    # Hiển thị thông tin kết thúc
    total_time = time.time() - start_time
    logger.info(f"===== KẾT THÚC XỬ LÝ LOCAL (Tổng thời gian: {total_time:.2f} giây) =====")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 