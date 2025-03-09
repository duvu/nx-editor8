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
    
    # Log the first few lines of the article for context
    if article_length > 0:
        preview_lines = article.split('\n')[:3]
        preview = '\n'.join(preview_lines)
        logger.debug(f"Article preview (first 3 lines):\n{preview}...")
    
    return {"article": article, "title": title}  # Return both as a dictionary 