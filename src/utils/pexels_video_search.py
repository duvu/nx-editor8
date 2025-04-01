#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module cung cấp chức năng tìm kiếm và tải video từ Pexels

Module này cung cấp lớp PexelsVideoSearch để:
1. Tìm kiếm video độ phân giải cao từ Pexels
2. Tải xuống video từ Pexels
3. Tìm kiếm video thay thế dựa trên từ khóa

Cách sử dụng:
    from src.utils.pexels_video_search import PexelsVideoSearch
    
    # Khởi tạo đối tượng PexelsVideoSearch
    pexels_searcher = PexelsVideoSearch(api_key="your_api_key")
    
    # Tìm kiếm video
    videos = pexels_searcher.search_videos("nature landscape")
    
    # Lấy một video thay thế
    alt_video_url = pexels_searcher.get_alternative_video("sunset beach")
    
    # Tải xuống video
    local_path = pexels_searcher.download_video("https://www.pexels.com/video/12345", "output.mp4")

Tác giả: NX-Editor8 Team
Phiên bản: 1.0
"""

import os
import re
import time
import random
import traceback
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse, quote_plus

import requests
from src.logger import logger

# Định nghĩa các hằng số
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
DEFAULT_TIMEOUT = 10
DEFAULT_MIN_WIDTH = 1280
DEFAULT_MIN_HEIGHT = 720
DEFAULT_MAX_RESULTS = 10
DEFAULT_PER_PAGE = 15
DEFAULT_API_ENDPOINT = "https://api.pexels.com/videos/search"
DEFAULT_VIDEO_DIR = "temp_videos"


class PexelsVideoSearch:
    """
    Lớp cung cấp các chức năng tìm kiếm và tải video từ Pexels
    
    Attributes:
        session (requests.Session): Phiên HTTP để thực hiện các request
        api_key (str): API key của Pexels
        min_width (int): Chiều rộng tối thiểu của video
        min_height (int): Chiều cao tối thiểu của video
        cache (dict): Cache kết quả tìm kiếm gần đây
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        min_width: int = DEFAULT_MIN_WIDTH, 
        min_height: int = DEFAULT_MIN_HEIGHT
    ) -> None:
        """
        Khởi tạo đối tượng PexelsVideoSearch
        
        Args:
            api_key: API key của Pexels
            min_width: Chiều rộng tối thiểu của video cần tìm
            min_height: Chiều cao tối thiểu của video cần tìm
        """
        # Khởi tạo session HTTP
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': DEFAULT_USER_AGENT
        })
        
        # Thiết lập API key
        self.api_key = api_key or os.environ.get('PEXELS_API_KEY', '')
        if not self.api_key:
            logger.warning("No Pexels API key provided. Set the PEXELS_API_KEY environment variable or pass it to the constructor.")
        
        # Thêm API key vào header
        if self.api_key:
            self.session.headers.update({
                'Authorization': self.api_key
            })
        
        # Thiết lập kích thước tối thiểu cho video
        self.min_width = min_width
        self.min_height = min_height
        
        # Cache kết quả tìm kiếm gần đây
        self.cache = {}
        
        # Tạo thư mục tạm cho video tải xuống
        os.makedirs(DEFAULT_VIDEO_DIR, exist_ok=True)
        
        logger.debug(f"PexelsVideoSearch initialized with min_width={min_width}, min_height={min_height}")

    def search_videos(self, query: str, max_results: int = DEFAULT_MAX_RESULTS, min_duration: int = 10, max_duration: int = 60) -> List[Dict[str, Any]]:
        """
        Tìm kiếm video độ phân giải cao từ Pexels
        
        Args:
            query: Từ khóa tìm kiếm
            max_results: Số lượng kết quả tối đa
            min_duration: Thời lượng tối thiểu (giây)
            max_duration: Thời lượng tối đa (giây)
            
        Returns:
            Danh sách thông tin video
        """
        try:
            # Kiểm tra cache
            cache_key = f"{query}_{max_results}_{min_duration}_{max_duration}"
            if cache_key in self.cache:
                logger.info(f"Returning cached results for query: '{query}'")
                return self.cache[cache_key]
            
            logger.info(f"Searching Pexels for videos: '{query}'")
            start_time = time.time()
            
            # Tính số trang cần tìm kiếm
            per_page = min(DEFAULT_PER_PAGE, max_results)
            pages_to_fetch = (max_results + per_page - 1) // per_page
            
            all_videos = []
            
            # Thực hiện tìm kiếm từng trang
            for page in range(1, pages_to_fetch + 1):
                videos = self._fetch_videos_page(query, page, per_page)
                if not videos:
                    break
                    
                all_videos.extend(videos)
                
                # Dừng nếu đã đủ số lượng kết quả
                if len(all_videos) >= max_results:
                    break
            
            # Lọc theo thời lượng và kích thước
            filtered_videos = []
            for video in all_videos:
                duration = video.get('duration', 0)
                if min_duration <= duration <= max_duration:
                    # Tìm file video tốt nhất
                    best_file = self._find_best_video_file(video.get('video_files', []))
                    if best_file:
                        video['best_file'] = best_file
                        filtered_videos.append(video)
                
                # Dừng nếu đã đủ số lượng kết quả
                if len(filtered_videos) >= max_results:
                    break
            
            # Định dạng kết quả
            results = self._format_video_results(filtered_videos[:max_results])
            
            # Lưu vào cache
            self.cache[cache_key] = results
            
            search_time = time.time() - start_time
            logger.info(f"Found {len(results)} videos for query: '{query}' in {search_time:.2f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching Pexels videos: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return []

    def _fetch_videos_page(self, query: str, page: int = 1, per_page: int = DEFAULT_PER_PAGE) -> List[Dict[str, Any]]:
        """
        Tìm kiếm một trang kết quả từ Pexels API
        
        Args:
            query: Từ khóa tìm kiếm
            page: Số trang
            per_page: Số kết quả mỗi trang
            
        Returns:
            Danh sách thông tin video trong trang
        """
        if not self.api_key:
            logger.error("Cannot fetch videos: No Pexels API key provided")
            return []
            
        try:
            # Chuẩn bị tham số
            params = {
                'query': query,
                'page': page,
                'per_page': per_page,
                'orientation': 'landscape',  # Ưu tiên video ngang
                'size': 'medium'  # Ưu tiên video kích thước trung bình
            }
            
            # Gửi request tới API
            response = self.session.get(
                DEFAULT_API_ENDPOINT,
                params=params,
                timeout=DEFAULT_TIMEOUT
            )
            
            # Kiểm tra kết quả
            if response.status_code != 200:
                logger.error(f"Pexels API error. Status code: {response.status_code}, Response: {response.text}")
                return []
                
            data = response.json()
            
            # Trả về danh sách video
            videos = data.get('videos', [])
            logger.debug(f"Fetched {len(videos)} videos from page {page}")
            
            return videos
            
        except Exception as e:
            logger.error(f"Error fetching videos page: {str(e)}")
            return []

    def _find_best_video_file(self, video_files: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Tìm file video tốt nhất từ danh sách file
        
        Args:
            video_files: Danh sách các file video
            
        Returns:
            Thông tin file video tốt nhất
        """
        if not video_files:
            return None
            
        # Lọc các file có định dạng mp4 và đạt độ phân giải tối thiểu
        suitable_files = [
            f for f in video_files 
            if f.get('file_type', '').startswith('video/mp4') and 
            f.get('width', 0) >= self.min_width and 
            f.get('height', 0) >= self.min_height
        ]
        
        if not suitable_files:
            # Nếu không có file nào phù hợp, lấy file có độ phân giải cao nhất
            return max(video_files, key=lambda x: x.get('width', 0) * x.get('height', 0), default=None)
        
        # Sắp xếp theo kích thước (ưu tiên độ phân giải cao nhất)
        suitable_files.sort(key=lambda x: x.get('width', 0) * x.get('height', 0), reverse=True)
        
        return suitable_files[0]

    def _format_video_results(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Định dạng kết quả video để dễ sử dụng
        
        Args:
            videos: Danh sách thông tin video từ API
            
        Returns:
            Danh sách thông tin video đã định dạng
        """
        formatted_results = []
        
        for video in videos:
            best_file = video.get('best_file', {})
            if not best_file:
                continue
                
            # Tạo thông tin video
            video_info = {
                'id': str(video.get('id', '')),
                'url': best_file.get('link', ''),
                'title': f"Pexels Video {video.get('id', '')}",
                'thumbnail': video.get('image', ''),
                'duration': video.get('duration', 0),
                'width': best_file.get('width', 0),
                'height': best_file.get('height', 0),
                'user': video.get('user', {}).get('name', 'Pexels Contributor'),
                'user_url': video.get('user', {}).get('url', ''),
                'pexels_url': video.get('url', ''),
                'platform': 'pexels',
                'resolution': f"{best_file.get('width', 0)}x{best_file.get('height', 0)}",
                'source': 'pexels_search'
            }
            
            formatted_results.append(video_info)
        
        return formatted_results

    def get_alternative_video(self, keywords: str, max_results: int = 5) -> Optional[Dict[str, Any]]:
        """
        Tìm kiếm video thay thế từ Pexels
        
        Args:
            keywords: Từ khóa tìm kiếm
            max_results: Số lượng kết quả tối đa
            
        Returns:
            Thông tin video thay thế hoặc None nếu không tìm thấy
        """
        if not keywords:
            logger.warning("No keywords provided for alternative video search")
            return None
            
        logger.info(f"Looking for alternative video with keywords: '{keywords}'")
        
        try:
            # Chuẩn bị từ khóa tìm kiếm
            search_query = self._prepare_search_query(keywords)
            logger.debug(f"Prepared search query: '{search_query}'")
            
            # Tìm kiếm video
            videos = self.search_videos(search_query, max_results=max_results)
            
            if not videos:
                logger.warning(f"No videos found for keywords: '{keywords}'")
                return None
                
            # Lấy ngẫu nhiên một video từ kết quả
            selected_video = random.choice(videos)
            logger.info(f"Selected alternative video: {selected_video.get('title', 'Unknown')}")
            
            return selected_video
            
        except Exception as e:
            logger.error(f"Error getting alternative video: {str(e)}")
            return None

    def _prepare_search_query(self, keywords: str) -> str:
        """
        Chuẩn bị từ khóa tìm kiếm
        
        Args:
            keywords: Từ khóa tìm kiếm gốc
            
        Returns:
            Từ khóa tìm kiếm đã chuẩn bị
        """
        # Làm sạch từ khóa
        keywords = re.sub(r'[^\w\s]', ' ', keywords)
        
        # Loại bỏ các từ không cần thiết
        stopwords = ['the', 'a', 'an', 'and', 'or', 'but', 'if', 'then', 'else', 'when', 'where', 'why', 'how']
        keywords = ' '.join([word for word in keywords.split() if word.lower() not in stopwords])
        
        # Thêm một số từ khóa để tìm video chất lượng cao
        quality_terms = ['HD', 'high quality', 'footage']
        search_query = f"{keywords} {random.choice(quality_terms)}"
        
        return search_query.strip()

    def download_video(self, video_url: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Tải xuống video từ URL
        
        Args:
            video_url: URL của video cần tải
            output_path: Đường dẫn lưu video (nếu None, sẽ lưu vào thư mục tạm)
            
        Returns:
            Đường dẫn tới file video đã tải hoặc None nếu tải thất bại
        """
        if not video_url:
            logger.error("No video URL provided for download")
            return None
            
        logger.info(f"Downloading video from URL: {video_url}")
        start_time = time.time()
        
        try:
            # Tạo tên file nếu không được cung cấp
            if not output_path:
                # Tạo tên file từ URL hoặc dùng tên ngẫu nhiên
                url_parts = urlparse(video_url)
                filename = os.path.basename(url_parts.path)
                if not filename or not filename.endswith('.mp4'):
                    filename = f"pexels_video_{int(time.time())}.mp4"
                    
                output_path = os.path.join(DEFAULT_VIDEO_DIR, filename)
            
            # Tạo thư mục cha nếu không tồn tại
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Tải video
            response = self.session.get(video_url, stream=True, timeout=DEFAULT_TIMEOUT)
            
            if response.status_code != 200:
                logger.error(f"Failed to download video. Status code: {response.status_code}")
                return None
                
            # Lưu video vào file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            download_time = time.time() - start_time
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # Size in MB
            
            logger.info(f"Downloaded video to {output_path} ({file_size:.2f}MB) in {download_time:.2f}s")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            return None

    def is_url_accessible(self, url: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        """
        Kiểm tra URL có thể truy cập không
        
        Args:
            url: URL cần kiểm tra
            timeout: Thời gian chờ tối đa (giây)
            
        Returns:
            True nếu URL có thể truy cập, False nếu không
        """
        if not url:
            return False
            
        try:
            # Kiểm tra URL có hợp lệ không
            if not self._is_valid_url(url):
                return False
                
            # Gửi HEAD request để kiểm tra URL
            response = self.session.head(url, timeout=timeout)
            
            # Kiểm tra status code
            if response.status_code == 200:
                return True
            elif response.status_code in [301, 302, 303, 307, 308]:
                # Kiểm tra redirect
                redirect_url = response.headers.get('Location')
                if redirect_url:
                    return self.is_url_accessible(redirect_url, timeout)
            
            return False
            
        except Exception as e:
            logger.debug(f"URL not accessible ({url}): {str(e)}")
            return False

    def _is_valid_url(self, url: str) -> bool:
        """
        Kiểm tra URL có định dạng hợp lệ không
        
        Args:
            url: URL cần kiểm tra
            
        Returns:
            True nếu URL hợp lệ, False nếu không
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        except Exception:
            return False 