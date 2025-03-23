#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module xử lý bài viết để trích xuất nội dung và tiêu đề
"""

from ..logger import logger

def extract_article(message):
    """
    Extract article and title from message
    
    Args:
        message (dict): Message chứa bài viết cần trích xuất
        
    Returns:
        dict: Bài viết và tiêu đề đã được trích xuất hoặc None nếu không tìm thấy bài viết
    """
    logger.info("Starting extract_article processor")
    
    # Log message type and structure
    logger.debug(f"Message type: {type(message)}")
    if isinstance(message, dict):
        keys = list(message.keys())
        logger.debug(f"Message keys: {keys}")
    
    # Extract article from message. It's the field "article"
    article = message.get("article", "")
    title = message.get("title", "")  # Extract the title
    
    # Logging article length and title for debugging
    article_length = len(article) if article else 0
    logger.info(f"Extracted article (length: {article_length} chars)")
    logger.info(f"Extracted title: '{title}'")
    
    if not article:
        logger.error("No article found in message")
        return None
    
    # Trích xuất nội dung từ bài viết
    # Loại bỏ các dòng bắt đầu bằng ký tự đặc biệt và dòng trống
    SPECIAL_CHARS = ('-', '*', '#', '+', '?', '<', '>')
    EXCLUDED_PREFIXES = ('http://', 'https://')
    
    # Tách thành các dòng và bỏ qua dòng đầu tiên (tiêu đề)
    lines = article.split('\n')[1:]
    
    # Lọc các dòng hợp lệ
    content_lines = []
    for line in lines:
        line = line.strip()
        if not line:  # Bỏ qua dòng trống
            continue
            
        # Kiểm tra nếu dòng chứa ký tự đặc biệt
        if any(char in line for char in SPECIAL_CHARS):
            continue
        if any(line.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            continue
            
        content_lines.append(line)
    
    # Ghép các dòng lại thành nội dung hoàn chỉnh
    content = '\n'.join(content_lines)
    logger.info(f"Đã trích xuất nội dung: '{content}'")

    # Return none if content is too short 
    if len(content) < 100:
        logger.error("Content is too short")
        return None
    
    # Log the first few lines of the article for context
    if article_length > 0:
        preview_lines = article.split('\n')[:3]
        preview = '\n'.join(preview_lines)
        logger.debug(f"Article preview (first 3 lines):\n{preview}...")
    
    return {"article": article, "title": title}  # Return both as a dictionary 