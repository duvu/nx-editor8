#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module tập hợp tất cả các processor để xử lý dữ liệu
"""

# Import các processor từ các module riêng biệt
from .article_processor import extract_article
from .image_processor import image_processor
from .script_processor import script_processor
from .s2j_processor import s2j_processor

# Export tất cả các processor
__all__ = [
    'extract_article',
    'image_processor',
    'script_processor',
    's2j_processor'
] 