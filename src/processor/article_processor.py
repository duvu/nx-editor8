#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module xử lý bài viết để trích xuất nội dung và tiêu đề
"""

import re
from ..logger import logger

def remove_text_between_brackets(text):
    """
    Remove any text enclosed in brackets: (), [], {}, <>
    
    Args:
        text (str): The input text
        
    Returns:
        str: Text with content between brackets removed
    """
    # Remove content within parentheses
    text = re.sub(r'\([^()]*\)', '', text)
    # Remove content within square brackets
    text = re.sub(r'\[[^\[\]]*\]', '', text)
    # Remove content within curly braces
    text = re.sub(r'\{[^\{\}]*\}', '', text)
    # Remove content within angle brackets
    text = re.sub(r'<[^<>]*>', '', text)
    
    # Remove any extra whitespace that might have been created
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

def extract_article(message):
    """
    Extract article and title from message
    
    Args:
        message (dict): Message chứa bài viết cần trích xuất
        
    Returns:
        dict: Bài viết và tiêu đề đã được trích xuất hoặc None nếu không tìm thấy bài viết
    """
    # Set logger to DEBUG level for this function
    original_level = logger.get_level()
    logger.set_level('DEBUG')
    
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
        logger.set_level(original_level)
        return None
    
    # DEBUG: Print the entire article content
    logger.debug(f"FULL ARTICLE CONTENT: \n{article}")
    
    # For markdown content, we want to keep all the content as is
    # We'll just extract the title from the first line if it starts with #
    lines = article.split('\n')
    logger.debug(f"Article split into {len(lines)} lines")
    
    # Extract title from first line if it starts with # (markdown header)
    if lines and lines[0].startswith('#'):
        title = lines[0].lstrip('#').strip()
        logger.debug(f"Extracted title from content: '{title}'")
    
    # We'll keep the entire content for processing
    content = article
    
    # Log content preview
    logger.debug(f"Final content length: {len(content)} characters")
    logger.info(f"Đã trích xuất nội dung: '{content[:50]}...'")  # Only log first 50 chars

    # Return none if content is too short 
    if len(content) < 100:
        logger.error(f"Content is too short: only {len(content)} characters (minimum 100)")
        logger.set_level(original_level)
        return None
    
    # Reset logger level
    logger.set_level(original_level)
    
    return {"article": content, "title": title}