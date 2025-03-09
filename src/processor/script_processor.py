#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module thực hiện xử lý và cải thiện kịch bản, bao gồm việc thêm hình ảnh
"""

import time
from ..logger import logger
from ..image_search import ImageSearch

def script_processor(data):
    """
    Perform additional script processing
    
    Args:
        data (dict): Dữ liệu bài viết đã được xử lý qua các bước trước
        
    Returns:
        dict: Dữ liệu bài viết sau khi đã thêm hình ảnh nếu cần
    """
    logger.info("Starting script processor")
    start_time = time.time()
    
    # Validate input
    if not isinstance(data, dict):
        logger.error(f"Expected dict input but got {type(data)}")
        return None
    
    # Extract article and title
    article = data.get("article", "")
    title = data.get("title", "")
    
    if not article:
        logger.warning("Empty article received in script processor")
        return data
    
    logger.debug(f"Processing article with {len(article)} chars and title: '{title}'")
    
    # Count existing image lines
    lines = article.strip().split('\n')
    logger.debug(f"Article split into {len(lines)} lines")
    
    image_lines = [line for line in lines if line.startswith('http://') or line.startswith('https://')]
    image_count = len(image_lines)
    
    logger.info(f"Found {image_count} image lines in the article")
    
    # If we have fewer than 5 images, add more
    if image_count < 5:
        logger.info(f"Article has fewer than 5 images ({image_count}). Adding more images...")
        
        # Extract keywords from the script (lines starting with #)
        keywords = ""
        for i, line in enumerate(lines):
            if line.startswith('#'):
                keywords = line.strip('#').strip()
                logger.debug(f"Found keywords at line {i+1}: '{keywords}'")
                break
        
        # If no keywords found, use title instead of default
        if not keywords:
            keywords = title if title else "generic images"
            logger.info(f"No keywords found in text, using title as keywords: '{keywords}'")
        
        logger.info(f"Using keywords for additional images: '{keywords}'")
        
        # Initialize image search helper
        image_searcher = ImageSearch()
        
        # Add new image lines
        new_images_needed = 5 - image_count
        added_images = []
        
        logger.info(f"Attempting to add {new_images_needed} new images")
        
        for i in range(new_images_needed):
            search_start_time = time.time()
            new_url = image_searcher.get_alternative_image(keywords)
            search_time = time.time() - search_start_time
            
            if new_url:
                added_images.append(new_url)
                logger.info(f"Added new image ({i+1}/{new_images_needed}) in {search_time:.2f}s: {new_url}")
            else:
                logger.warning(f"Failed to find image {i+1}/{new_images_needed} for '{keywords}'")
        
        # Insert new image lines after existing images or at the end if no images exist
        if image_lines:
            # Find the position of the last image line
            last_img_pos = 0
            for i, line in enumerate(lines):
                if line.startswith('http://') or line.startswith('https://'):
                    last_img_pos = i
                    logger.debug(f"Found last image at line {i+1}: {line[:60]}...")
            
            # Add new images after the last image line
            logger.debug(f"Inserting new images after position {last_img_pos}")
            for i, img in enumerate(added_images):
                insert_pos = last_img_pos + 1 + i
                lines.insert(insert_pos, img)
                logger.debug(f"Inserted image at position {insert_pos}")
        else:
            # If no images exist, add them at the end
            logger.debug(f"No existing images. Adding {len(added_images)} images to the end")
            lines.extend(added_images)
        
        # Join lines back into a single string
        data["article"] = '\n'.join(lines)
        logger.info(f"Added {len(added_images)} new images to reach minimum of 5 images")
    else:
        logger.info(f"Article already has {image_count} images (≥5). No need to add more.")
    
    processing_time = time.time() - start_time
    logger.info(f"Script processing completed in {processing_time:.2f}s")
    
    return data 