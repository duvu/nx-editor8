#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module chuyển đổi kịch bản thành định dạng JSON
"""

import time
import traceback
from ..logger import logger
from ..utils.script2json import script2json

def s2j_processor(data):
    """
    Convert script to JSON format
    
    Args:
        data (dict): Dữ liệu bài viết đã được xử lý qua các bước trước
        
    Returns:
        dict: Dữ liệu đã được chuyển đổi sang JSON hoặc JSON lỗi nếu thất bại
    """
    logger.info("Starting script2json processor")
    start_time = time.time()
    
    # Validate input
    if not isinstance(data, dict):
        logger.error(f"Expected dict input but got {type(data)}")
        return None
    
    # Extract article
    article = data.get("article", "")
    if not article:
        logger.error("Empty article received in script2json processor")
        return None
        
    logger.debug(f"Converting article to JSON (length: {len(article)} chars)")
    
    try:
        # Thực hiện chuyển đổi sang JSON
        result = script2json(article)
        
        # Log kết quả
        if isinstance(result, dict):
            sections = result.get("sections", [])
            section_count = len(sections) if sections else 0
            logger.info(f"Converted script to JSON with {section_count} sections")
            
            # Log chi tiết hơn về cấu trúc JSON
            logger.debug(f"JSON result keys: {list(result.keys())}")
            if section_count > 0:
                logger.debug(f"First section: {sections[0] if sections else 'No sections'}")
        else:
            logger.warning(f"Unexpected result type from script2json: {type(result)}")
        
        processing_time = time.time() - start_time
        logger.info(f"script2json conversion completed in {processing_time:.2f}s")
        
        return result
    except Exception as e:
        logger.error(f"Error in script2json conversion: {str(e)}")
        logger.error(f"Error stack trace: {traceback.format_exc()}")
        
        # Tạo một JSON lỗi tối thiểu thay vì trả về None
        error_json = {
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": time.time(),
            "original_length": len(article)
        }
        logger.warning("Returning error JSON instead of None")
        return error_json 