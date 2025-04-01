#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module for keyword utilities that can be used across different parts of the application.
Contains functions for extracting, selecting, and manipulating keywords.
"""

import random
import logging

logger = logging.getLogger(__name__)

def select_random_keywords(keywords: str, min_keywords: int = 1, max_keywords: int = 2) -> str:
    """Select 1-2 random keywords from the full keywords string.
    
    Args:
        keywords: Full keywords string
        min_keywords: Minimum number of keywords to select
        max_keywords: Maximum number of keywords to select
        
    Returns:
        String with 1-2 randomly selected keywords
    """
    if not keywords:
        return ""
        
    # Split keywords into a list and remove empty strings
    keyword_list = [kw.strip() for kw in keywords.split() if kw.strip()]
    
    if not keyword_list:
        return ""
        
    # If we have very few keywords, just return them all
    if len(keyword_list) <= min_keywords:
        return " ".join(keyword_list)
        
    # Determine how many keywords to select (between min and max)
    num_to_select = min(random.randint(min_keywords, max_keywords), len(keyword_list))
    
    # Select random keywords
    selected_keywords = random.sample(keyword_list, num_to_select)
    
    logger.info(f"Selected {num_to_select} random keywords from '{keywords}': '{' '.join(selected_keywords)}'")
    return " ".join(selected_keywords)

def extract_keywords(lines, title: str = "") -> str:
    """Extract keywords from article lines or use title as fallback.
    
    Args:
        lines: List of lines from the article
        title: Article title to use as fallback
        
    Returns:
        Keywords string extracted from article or title
    """
    keywords = ""
    for line in lines:
        if line.startswith('#'):
            keywords = line.strip('#').strip()
            break
    
    if not keywords:
        keywords = title if title else "generic search terms"
        logger.info(f"No keywords found, using title: {keywords}")
    
    logger.info(f"Extracted keywords: {keywords}")
    return keywords 