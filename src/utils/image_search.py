#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module cung cấp chức năng tìm kiếm và xác thực hình ảnh

Module này cung cấp lớp ImageSearch để:
1. Tìm kiếm hình ảnh độ phân giải cao từ DuckDuckGo
2. Kiểm tra tính khả dụng của URL hình ảnh
3. Kiểm tra kích thước và độ phân giải của hình ảnh
4. Tìm kiếm hình ảnh thay thế dựa trên từ khóa

Cách sử dụng:
    from src.utils.image_search import ImageSearch
    
    # Khởi tạo đối tượng ImageSearch
    image_searcher = ImageSearch()
    
    # Tìm kiếm hình ảnh
    image_urls = image_searcher.search_duckduckgo("nature landscape")
    
    # Lấy một hình ảnh thay thế
    alt_image_url = image_searcher.get_alternative_image("sunset beach")
    
    # Kiểm tra URL có thể truy cập không
    is_accessible = image_searcher.is_url_accessible("https://example.com/image.jpg")

Tác giả: NX-Editor8 Team
Phiên bản: 1.1
"""

import os
import re
import time
import random
import logging
import traceback
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse, quote_plus
import urllib.request

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

import requests
from ..logger import logger

# Định nghĩa các hằng số
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
DEFAULT_TIMEOUT = 5
DEFAULT_MIN_WIDTH = 800
DEFAULT_MIN_HEIGHT = 600
DEFAULT_MAX_RESULTS = 10


class ImageSearch:
    """
    Lớp cung cấp các chức năng tìm kiếm và xác thực hình ảnh
    
    Attributes:
        session (requests.Session): Phiên HTTP để thực hiện các request
        ddgs (DDGS): Đối tượng DuckDuckGo Search để tìm kiếm
        min_width (int): Chiều rộng tối thiểu của hình ảnh
        min_height (int): Chiều cao tối thiểu của hình ảnh
    """
    
    def __init__(
        self, 
        min_width: int = DEFAULT_MIN_WIDTH, 
        min_height: int = DEFAULT_MIN_HEIGHT
    ) -> None:
        """
        Khởi tạo đối tượng ImageSearch
        
        Args:
            min_width: Chiều rộng tối thiểu của hình ảnh cần tìm
            min_height: Chiều cao tối thiểu của hình ảnh cần tìm
        """
        # Khởi tạo session HTTP
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': DEFAULT_USER_AGENT
        })
        
        # Khởi tạo đối tượng tìm kiếm DuckDuckGo
        self.ddgs = DDGS()
        
        # Thiết lập kích thước tối thiểu cho hình ảnh
        self.min_width = min_width
        self.min_height = min_height
        
        logger.debug(f"ImageSearch initialized with min_width={min_width}, min_height={min_height}")

    def search_duckduckgo(self, query: str, max_results: int = DEFAULT_MAX_RESULTS) -> List[str]:
        """
        Tìm kiếm hình ảnh độ phân giải cao từ DuckDuckGo
        
        Args:
            query: Từ khóa tìm kiếm
            max_results: Số lượng kết quả tối đa
            
        Returns:
            Danh sách URL hình ảnh đạt yêu cầu về độ phân giải
        """
        try:
            logger.info(f"Searching DuckDuckGo for high-res images: {query}")
            start_time = time.time()
            
            # Thực hiện tìm kiếm hình ảnh từ DuckDuckGo
            results = self._perform_duckduckgo_search(query, max_results)
            
            # Xử lý và lọc kết quả
            detailed_results = self._process_search_results(results)
            
            # Sắp xếp kết quả theo kích thước và lấy URLs
            image_urls = self._get_top_image_urls(detailed_results, max_results)
            
            search_time = time.time() - start_time
            logger.info(f"Found {len(image_urls)} high-resolution images for query: '{query}' in {search_time:.2f}s")
            
            return image_urls
            
        except Exception as e:
            logger.error(f"Error searching DuckDuckGo: {str(e)}")
            return []

    def _perform_duckduckgo_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Thực hiện tìm kiếm hình ảnh từ DuckDuckGo
        
        Args:
            query: Từ khóa tìm kiếm
            max_results: Số lượng kết quả tối đa
            
        Returns:
            Kết quả tìm kiếm từ DuckDuckGo
        """
        # Yêu cầu nhiều hơn số kết quả cần để có đủ sau khi lọc
        search_count = max_results * 2
        
        # Sử dụng thư viện duckduckgo-search để tìm kiếm hình ảnh với tham số kích thước
        results = list(self.ddgs.images(
            keywords=query,
            max_results=search_count,
            size="large"  # Yêu cầu hình ảnh lớn
        ))
        
        logger.debug(f"DuckDuckGo returned {len(results)} initial results")
        return results

    def _process_search_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Xử lý và lọc kết quả tìm kiếm
        
        Args:
            results: Kết quả tìm kiếm từ DuckDuckGo
            
        Returns:
            Danh sách kết quả chi tiết với thông tin kích thước
        """
        detailed_results = []
        
        for result in results:
            image_url = result.get("image")
            if not image_url:
                continue
            
            # Lấy kích thước từ metadata hoặc kiểm tra trực tiếp
            detailed_result = self._process_single_result(result, image_url)
            if detailed_result:
                detailed_results.append(detailed_result)
        
        return detailed_results

    def _process_single_result(self, result: Dict[str, Any], image_url: str) -> Optional[Dict[str, Any]]:
        """
        Xử lý một kết quả tìm kiếm đơn lẻ
        
        Args:
            result: Kết quả tìm kiếm
            image_url: URL hình ảnh
            
        Returns:
            Thông tin chi tiết về hình ảnh hoặc None nếu không đạt yêu cầu
        """
        # Lấy kích thước hình ảnh từ metadata nếu có
        width = result.get("width")
        height = result.get("height")
        
        # Nếu kích thước có sẵn trong metadata
        if width and height:
            return self._create_result_from_metadata(image_url, width, height)
        
        # Nếu không có kích thước trong metadata, kiểm tra trực tiếp
        dimensions = self.check_image_resolution(image_url)
        if dimensions:
            width, height = dimensions
            if width >= self.min_width and height >= self.min_height:
                return {
                    "url": image_url,
                    "width": width,
                    "height": height,
                    "size": width * height
                }
        
        # Nếu không thể kiểm tra kích thước, vẫn thêm vào nhưng với kích thước 0
        return {
            "url": image_url,
            "width": 0,
            "height": 0,
            "size": 0
        }

    def _create_result_from_metadata(self, image_url: str, width: Union[str, int], height: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Tạo thông tin kết quả từ metadata
        
        Args:
            image_url: URL hình ảnh
            width: Chiều rộng hình ảnh
            height: Chiều cao hình ảnh
            
        Returns:
            Thông tin chi tiết về hình ảnh hoặc None nếu không đạt yêu cầu
        """
        try:
            width_int = int(width)
            height_int = int(height)
            
            if width_int >= self.min_width and height_int >= self.min_height:
                return {
                    "url": image_url,
                    "width": width_int,
                    "height": height_int,
                    "size": width_int * height_int  # Tính tổng số pixel cho việc sắp xếp
                }
        except (ValueError, TypeError):
            logger.debug(f"Invalid dimensions for {image_url}: width={width}, height={height}")
        
        return None

    def _get_top_image_urls(self, detailed_results: List[Dict[str, Any]], max_results: int) -> List[str]:
        """
        Sắp xếp kết quả theo kích thước và lấy URLs
        
        Args:
            detailed_results: Danh sách kết quả chi tiết
            max_results: Số lượng kết quả tối đa
            
        Returns:
            Danh sách URL hình ảnh
        """
        # Sắp xếp theo kích thước (lớn nhất trước)
        sorted_results = sorted(detailed_results, key=lambda x: x["size"], reverse=True)
        
        # Trích xuất URLs từ kết quả đã sắp xếp
        image_urls = [result["url"] for result in sorted_results[:max_results]]
        
        # Log kích thước hình ảnh cho debug
        if image_urls:
            dimensions = [(r['width'], r['height']) for r in sorted_results[:max_results] if r['width'] > 0]
            logger.debug(f"Top image dimensions: {dimensions}")
        
        return image_urls

    def check_image_resolution(self, url: str, timeout: int = DEFAULT_TIMEOUT // 2) -> Optional[Tuple[int, int]]:
        """
        Kiểm tra độ phân giải của hình ảnh tại URL cụ thể
        
        Args:
            url: URL của hình ảnh cần kiểm tra
            timeout: Thời gian chờ tối đa (giây)
            
        Returns:
            Tuple (chiều rộng, chiều cao) hoặc None nếu kiểm tra không thành công
        """
        try:
            # Kiểm tra nhanh xem URL có thể truy cập không
            if not self._is_valid_url(url):
                logger.debug(f"Invalid URL format: {url}")
                return None
                
            # Tải hình ảnh
            response = self.session.get(url, stream=True, timeout=timeout)
            if response.status_code == 200:
                # Đọc dữ liệu hình ảnh để lấy kích thước
                img_data = BytesIO(response.content)
                img = Image.open(img_data)
                
                # Trả về tuple (chiều rộng, chiều cao)
                dimensions = img.size
                logger.debug(f"Image dimensions for {url}: {dimensions}")
                return dimensions
        except Exception as e:
            logger.debug(f"Failed to check image resolution for {url}: {str(e)}")
        
        return None

    def is_url_accessible(self, url: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        """
        Kiểm tra URL có thể truy cập được không
        
        Args:
            url: URL cần kiểm tra
            timeout: Thời gian chờ tối đa (giây)
            
        Returns:
            True nếu URL có thể truy cập, False nếu không
        """
        try:
            # Kiểm tra định dạng URL
            if not self._is_valid_url(url):
                logger.debug(f"Invalid URL format: {url}")
                return False
                
            # Gửi HEAD request để kiểm tra
            response = self.session.head(url, timeout=timeout, allow_redirects=True)
            status = response.status_code < 400
            
            logger.debug(f"URL accessibility check for {url}: status_code={response.status_code}, accessible={status}")
            return status
        except Exception as e:
            logger.warning(f"URL check failed for {url}: {str(e)}")
            return False

    def _is_valid_url(self, url: str) -> bool:
        """
        Kiểm tra xem một URL có định dạng hợp lệ không
        
        Args:
            url: URL cần kiểm tra
            
        Returns:
            True nếu URL hợp lệ, False nếu không
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def get_alternative_image(self, keywords: str, max_results: int = 5) -> Optional[str]:
        """
        Lấy URL hình ảnh thay thế độ phân giải cao dựa trên từ khóa
        
        Args:
            keywords: Từ khóa tìm kiếm
            max_results: Số lượng kết quả tối đa để chọn ngẫu nhiên
            
        Returns:
            URL hình ảnh hoặc None nếu không tìm thấy
        """
        # Chuẩn bị từ khóa tìm kiếm
        search_query = self._prepare_search_query(keywords)
        
        # Tìm kiếm hình ảnh
        image_urls = self.search_duckduckgo(search_query, max_results)
        
        # Trả về một hình ảnh ngẫu nhiên hoặc None nếu không tìm thấy
        if image_urls:
            selected_url = random.choice(image_urls)
            logger.info(f"Selected alternative image for '{keywords}': {selected_url}")
            return selected_url
            
        logger.warning(f"No alternative images found for '{keywords}'")
        return None

    def _prepare_search_query(self, keywords: str) -> str:
        """
        Chuẩn bị từ khóa tìm kiếm
        
        Args:
            keywords: Từ khóa gốc
            
        Returns:
            Từ khóa đã được chuẩn bị
        """
        if not keywords:
            return "generic image high resolution"
        
        # Thêm "high resolution" vào từ khóa
        if "high resolution" not in keywords.lower() and "hd" not in keywords.lower():
            return f"{keywords} high resolution"
        
        return keywords
