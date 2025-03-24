#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module cung cấp chức năng tìm kiếm video YouTube bằng yt-dlp
"""

import re
import json
import random
import time
import traceback
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs, quote_plus

import requests
import yt_dlp
from ..logger import logger



class VideoSearch:
    """
    Lớp hỗ trợ tìm kiếm và xử lý video từ YouTube sử dụng yt-dlp.
    """
    
    def __init__(self):
        """Khởi tạo đối tượng VideoSearch với các cấu hình mặc định"""
        # Thiết lập session cho các request
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Cấu hình mặc định cho yt-dlp
        self.ytdlp_options = {
            'format': 'best[height<=720]',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Khai thác nhanh
            'skip_download': True,
            'ignoreerrors': True,
            'nocheckcertificate': True,
            'no_color': True,
            'socket_timeout': 10, 
            'geo_bypass': True,
            'age_limit': 21,  # Bỏ qua giới hạn tuổi
        }
        
        # Cấu hình tìm kiếm
        self.search_options = {
            'extract_flat': True,
            'skip_download': True,
            'playlistend': 20,  # Giới hạn số lượng kết quả tìm kiếm
        }
        
        # Yêu cầu tối thiểu cho video
        self.min_duration = 10  # Thời lượng tối thiểu 10 giây
        self.max_duration = 1800  # Thời lượng tối đa 30 phút
        self.min_resolution = 240  # Độ phân giải tối thiểu
        
        logger.info("VideoSearch initialized")
        
    def search_videos(self, keywords: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Tìm kiếm video YouTube dựa trên từ khóa
        
        Args:
            keywords: Từ khóa tìm kiếm
            max_results: Số lượng kết quả tối đa
            
        Returns:
            Danh sách thông tin video
        """
        if not keywords:
            return []
            
        logger.info(f"Searching videos for keywords: '{keywords}', max results: {max_results}")
        start_time = time.time()
        
        try:
            # Tìm kiếm video trên YouTube
            search_results = self._search_youtube_videos(keywords)
            
            if not search_results:
                logger.warning(f"No search results found for keywords: '{keywords}'")
                return []
                
            logger.info(f"Found {len(search_results)} initial results for query: '{keywords}'")
            
            # Lọc và xử lý kết quả tìm kiếm
            processed_videos = []
            
            for video_data in search_results:
                # Kiểm tra xem đây có phải là video không
                if video_data.get('_type') != 'url' or not video_data.get('url'):
                    continue
                    
                video_id = video_data.get('id') or self._extract_youtube_id(video_data.get('url', ''))
                if not video_id:
                    continue
                    
                # Tạo thông tin video từ dữ liệu tìm kiếm cơ bản
                video_info = {
                    'id': video_id,
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'title': video_data.get('title', 'Unknown Title'),
                    'description': video_data.get('description', ''),
                    'thumbnail': self._get_thumbnail_url(video_id),
                    'duration': video_data.get('duration', 0),
                    'view_count': video_data.get('view_count', 0),
                    'upload_date': video_data.get('upload_date', ''),
                    'channel': video_data.get('channel', 'Unknown Channel'),
                    'channel_url': video_data.get('channel_url', ''),
                    'embed_url': f"https://www.youtube.com/embed/{video_id}",
                    'platform': 'youtube',
                    'resolution': self._estimate_resolution(video_data),
                    'source': 'youtube_search'
                }
                
                processed_videos.append(video_info)
                
                # Dừng nếu đã đủ số lượng kết quả
                if len(processed_videos) >= max_results:
                    break
            
            elapsed_time = time.time() - start_time
            logger.info(f"Found {len(processed_videos)} suitable videos for query: '{keywords}' in {elapsed_time:.2f} seconds")
            
            return processed_videos
            
        except Exception as e:
            logger.error(f"Error searching videos: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return []
    
    def _search_youtube_videos(self, query: str) -> List[Dict[str, Any]]:
        """
        Tìm kiếm video trên YouTube sử dụng yt-dlp
        
        Args:
            query: Từ khóa tìm kiếm
            
        Returns:
            Danh sách thông tin video
        """
        logger.info(f"Searching YouTube for: '{query}'")
        
        try:
            # Tạo URL tìm kiếm YouTube
            search_url = f"ytsearch20:{query}"  # Tìm 20 kết quả
            
            # Cấu hình yt-dlp cho tìm kiếm
            ydl_opts = {
                **self.ytdlp_options,
                **self.search_options
            }
            
            # Thực hiện tìm kiếm
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_results = ydl.extract_info(search_url, download=False)
                
                if not search_results or 'entries' not in search_results:
                    logger.warning(f"No results found or invalid response for query: '{query}'")
                    return []
                
                logger.info(f"YouTube search returned {len(search_results['entries'])} results")
                return search_results['entries']
                
        except Exception as e:
            logger.error(f"Error during YouTube search: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return []
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Lấy thông tin đầy đủ của video từ URL
        
        Args:
            url: URL của video
            
        Returns:
            Thông tin video hoặc None nếu không lấy được
        """
        if not url:
            logger.warning("Empty URL provided to get_video_info")
            return None
            
        logger.info(f"Getting video info for URL: {url}")
        start_time = time.time()
        
        try:
            # Kiểm tra URL hợp lệ
            if not self._is_youtube_url(url):
                logger.warning(f"URL is not a YouTube video: {url}")
                return self._create_minimal_video_info(url)
            
            # Sử dụng yt-dlp để lấy thông tin video
            with yt_dlp.YoutubeDL(self.ytdlp_options) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    logger.warning(f"Could not extract info for URL: {url}")
                    return self._create_minimal_video_info(url)
                
                # Lấy video ID
                video_id = info.get('id', self._extract_youtube_id(url))
                
                # Tạo thông tin video
                video_info = {
                    'id': video_id,
                    'url': url,
                    'title': info.get('title', 'Unknown Title'),
                    'description': info.get('description', ''),
                    'thumbnail': self._get_best_thumbnail(info),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'upload_date': self._format_date(info.get('upload_date', '')),
                    'channel': info.get('uploader', 'Unknown'),
                    'channel_url': info.get('uploader_url', ''),
                    'embed_url': f"https://www.youtube.com/embed/{video_id}",
                    'platform': 'youtube',
                    'resolution': self._get_max_resolution(info),
                    'source': 'yt_dlp'
                }
                
                elapsed_time = time.time() - start_time
                logger.info(f"Video info retrieved in {elapsed_time:.2f} seconds")
                return video_info
                
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            # Tạo thông tin tối thiểu nếu có lỗi
            return self._create_minimal_video_info(url)
    
    def _create_minimal_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Tạo thông tin tối thiểu cho video khi không thể lấy đầy đủ
        
        Args:
            url: URL của video
            
        Returns:
            Thông tin video tối thiểu
        """
        logger.info(f"Creating minimal video info for URL: {url}")
        
        try:
            # Lấy video ID nếu là YouTube
            video_id = self._extract_youtube_id(url)
            
            if video_id:
                # Tạo thông tin cơ bản cho video YouTube
                return {
                    'id': video_id,
                    'url': url,
                    'title': f"YouTube Video {video_id}",
                    'description': '',
                    'thumbnail': self._get_thumbnail_url(video_id),
                    'duration': 0,
                    'view_count': 0,
                    'upload_date': '',
                    'channel': 'Unknown',
                    'channel_url': '',
                    'embed_url': f"https://www.youtube.com/embed/{video_id}",
                    'platform': 'youtube',
                    'resolution': 0,
                    'source': 'minimal'
                }
            else:
                # URL không phải YouTube, tạo thông tin chung
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                
                return {
                    'id': '',
                    'url': url,
                    'title': f"Video from {domain}",
                    'description': '',
                    'thumbnail': '',
                    'duration': 0,
                    'view_count': 0,
                    'upload_date': '',
                    'channel': 'Unknown',
                    'channel_url': '',
                    'embed_url': url,
                    'platform': 'unknown',
                    'resolution': 0,
                    'source': 'minimal'
                }
                
        except Exception as e:
            logger.error(f"Error creating minimal video info: {str(e)}")
            return None
    
    def is_video_url_accessible(self, url: str, timeout: int = 10) -> bool:
        """
        Kiểm tra xem URL video có thể truy cập được không
        
        Args:
            url: URL của video
            timeout: Thời gian chờ tối đa (giây)
            
        Returns:
            True nếu URL có thể truy cập, False nếu không
        """
        if not url:
            return False
            
        logger.info(f"Checking if video URL is accessible: {url}")
        
        try:
            # Kiểm tra nhanh bằng cách yêu cầu HEAD
            response = self.session.head(url, timeout=timeout, allow_redirects=True)
            
            if 200 <= response.status_code < 300:
                logger.info(f"URL is accessible: {url}")
                return True
                
            if 300 <= response.status_code < 400:
                redirect_url = response.headers.get('Location')
                logger.info(f"URL redirects to: {redirect_url}")
                return True
                
            logger.warning(f"URL returned status code {response.status_code}: {url}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking URL accessibility: {str(e)}")
            return False
    
    def get_alternative_video(self, keywords: str) -> Optional[Dict[str, Any]]:
        """
        Tìm video thay thế khi không tìm thấy video phù hợp
        
        Args:
            keywords: Từ khóa tìm kiếm
            
        Returns:
            Thông tin video thay thế hoặc None nếu không tìm thấy
        """
        if not keywords:
            keywords = "nature documentary HD"
        
        logger.info(f"Searching for alternative video with keywords: '{keywords}'")
        
        # Thêm "HD" vào từ khóa nếu chưa có
        if "HD" not in keywords.upper():
            search_query = f"{keywords} HD"
        else:
            search_query = keywords
        
        try:
            # Tìm kiếm video trên YouTube
            results = self._search_youtube_videos(search_query)
            
            if not results:
                logger.warning(f"No alternative videos found for keywords: '{search_query}'")
                return None
                
            logger.info(f"Found {len(results)} alternative videos")
            
            # Chọn ngẫu nhiên một video từ kết quả
            selected_index = random.randint(0, min(5, len(results) - 1))  # Chọn trong 5 kết quả đầu tiên
            selected_result = results[selected_index]
            
            video_id = selected_result.get('id') or self._extract_youtube_id(selected_result.get('url', ''))
            
            if not video_id:
                logger.warning("Could not extract video ID from selected result")
                return None
            
            # Tạo URL từ video ID
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Lấy thông tin đầy đủ của video
            return self.get_video_info(video_url)
            
        except Exception as e:
            logger.error(f"Error getting alternative video: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return None
    
    def get_embed_html(self, video_info: Dict[str, Any], width: int = 640, height: int = 360) -> str:
        """
        Tạo mã HTML để nhúng video
        
        Args:
            video_info: Thông tin video từ get_video_info
            width: Chiều rộng của player
            height: Chiều cao của player
            
        Returns:
            Mã HTML để nhúng video
        """
        if not video_info:
            logger.warning("No video info provided to get_embed_html")
            return ""
            
        embed_url = video_info.get('embed_url', '')
        url = video_info.get('url', '')
        
        if not embed_url and url:
            # Tạo embed URL từ URL thông thường nếu là YouTube
            video_id = self._extract_youtube_id(url)
            if video_id:
                embed_url = f"https://www.youtube.com/embed/{video_id}"
            else:
                embed_url = url
        
        if not embed_url:
            logger.warning(f"No embed URL available for video: {video_info.get('title', 'Unknown')}")
            
            # Tạo mã HTML để hiển thị thông tin video khi không có URL nhúng
            thumbnail = video_info.get('thumbnail', '')
            title = video_info.get('title', 'Unknown Video')
            
            # Tạo mã HTML hiển thị hình ảnh và tiêu đề thay vì video
            fallback_html = f"""
            <div style="width: {width}px; height: {height}px; border: 1px solid #ccc; display: flex; flex-direction: column; justify-content: center; align-items: center; background-color: #f9f9f9; text-align: center; padding: 10px; box-sizing: border-box;">
                {f'<img src="{thumbnail}" alt="{title}" style="max-width: 90%; max-height: 70%; object-fit: contain; margin-bottom: 10px;">' if thumbnail else ''}
                <h3 style="margin: 5px 0; font-family: Arial, sans-serif;">{title}</h3>
                <p style="margin: 5px 0; font-family: Arial, sans-serif; font-size: 12px;">URL: <a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a></p>
                <p style="color: #666; font-family: Arial, sans-serif; font-size: 12px;">Video không có sẵn mã nhúng</p>
            </div>
            """
            
            logger.debug(f"Created fallback HTML for video without embed URL")
            return fallback_html
        
        # Tạo mã HTML nhúng YouTube
        return f'<iframe width="{width}" height="{height}" src="{embed_url}" frameborder="0" allowfullscreen allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"></iframe>'
    
    def _is_youtube_url(self, url: str) -> bool:
        """
        Kiểm tra xem URL có phải là video YouTube không
        
        Args:
            url: URL cần kiểm tra
            
        Returns:
            True nếu là YouTube video, False nếu không phải
        """
        if not url:
            return False
            
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Kiểm tra domain
            youtube_domains = ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com']
            
            if domain not in youtube_domains:
                return False
                
            # Kiểm tra path và query
            if domain == 'youtu.be':
                # youtu.be/<video_id>
                return bool(parsed_url.path and parsed_url.path != '/')
                
            if 'youtube.com' in domain:
                # youtube.com/watch?v=<video_id>
                if '/watch' in parsed_url.path:
                    query = parse_qs(parsed_url.query)
                    return 'v' in query and query['v'][0]
                    
                # youtube.com/v/<video_id>
                if parsed_url.path.startswith('/v/'):
                    return len(parsed_url.path) > 3
                    
                # youtube.com/embed/<video_id>
                if parsed_url.path.startswith('/embed/'):
                    return len(parsed_url.path) > 7
                    
            return False
            
        except Exception as e:
            logger.error(f"Error checking YouTube URL: {str(e)}")
            return False
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """
        Trích xuất ID video YouTube từ URL
        
        Args:
            url: URL YouTube
            
        Returns:
            ID video YouTube hoặc None nếu không tìm thấy
        """
        if not url:
            return None
            
        try:
            parsed_url = urlparse(url)
            
            # youtu.be/<id>
            if parsed_url.netloc == 'youtu.be':
                return parsed_url.path[1:]
                
            # youtube.com/watch?v=<id>
            if parsed_url.netloc in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
                query = parse_qs(parsed_url.query)
                if 'v' in query:
                    return query['v'][0]
                    
            # youtube.com/v/<id>
            if parsed_url.path.startswith('/v/'):
                return parsed_url.path.split('/')[2]
                
            # youtube.com/embed/<id>
            if parsed_url.path.startswith('/embed/'):
                return parsed_url.path.split('/')[2]
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting YouTube ID from {url}: {str(e)}")
            return None
    
    def _get_thumbnail_url(self, video_id: str) -> str:
        """
        Lấy URL thumbnail của video YouTube từ ID
        
        Args:
            video_id: ID video YouTube
            
        Returns:
            URL thumbnail chất lượng cao
        """
        if not video_id:
            return ""
            
        # YouTube cung cấp nhiều kích thước thumbnail:
        # - maxresdefault.jpg (1280x720)
        # - hqdefault.jpg (480x360)
        # - mqdefault.jpg (320x180)
        # - default.jpg (120x90)
        # Ưu tiên chất lượng cao nhất
        return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    
    def _get_best_thumbnail(self, info: Dict[str, Any]) -> str:
        """
        Lấy URL thumbnail chất lượng cao nhất từ thông tin video
        
        Args:
            info: Thông tin video từ yt-dlp
            
        Returns:
            URL thumbnail tốt nhất
        """
        if not info:
            return ""
            
        # Lấy video ID
        video_id = info.get('id')
        
        if not video_id:
            # Nếu không có ID, thử lấy từ thumbnails
            thumbnails = info.get('thumbnails', [])
            if thumbnails:
                # Sắp xếp thumbnail theo kích thước (lớn nhất trước)
                sorted_thumbnails = sorted(
                    thumbnails, 
                    key=lambda x: (x.get('width', 0) * x.get('height', 0)), 
                    reverse=True
                )
                return sorted_thumbnails[0].get('url', '')
            return ""
            
        # Nếu có ID, ưu tiên sử dụng thumbnail chất lượng cao từ YouTube
        return self._get_thumbnail_url(video_id)
    
    def _format_date(self, date_str: str) -> str:
        """
        Định dạng lại chuỗi ngày từ yt-dlp (YYYYMMDD)
        
        Args:
            date_str: Chuỗi ngày từ yt-dlp
            
        Returns:
            Chuỗi ngày định dạng YYYY-MM-DD
        """
        if not date_str or len(date_str) != 8:
            return date_str
            
        try:
            year = date_str[0:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{year}-{month}-{day}"
        except Exception:
            return date_str
    
    def _get_max_resolution(self, info: Dict[str, Any]) -> int:
        """
        Lấy độ phân giải cao nhất của video
        
        Args:
            info: Thông tin video từ yt-dlp
            
        Returns:
            Độ phân giải dọc (height) của video
        """
        if not info:
            return 0
            
        try:
            # Kiểm tra từ formats
            formats = info.get('formats', [])
            
            if formats:
                # Lấy độ phân giải cao nhất
                max_height = 0
                for fmt in formats:
                    height = fmt.get('height', 0)
                    if height and height > max_height:
                        max_height = height
                
                if max_height > 0:
                    return max_height
            
            # Nếu không tìm thấy từ formats, kiểm tra trong thông tin chung
            return info.get('height', 0)
            
        except Exception as e:
            logger.error(f"Error getting max resolution: {str(e)}")
            return 0
    
    def _estimate_resolution(self, video_data: Dict[str, Any]) -> int:
        """
        Ước tính độ phân giải của video từ dữ liệu tìm kiếm
        
        Args:
            video_data: Dữ liệu video từ kết quả tìm kiếm
            
        Returns:
            Độ phân giải ước tính (240, 360, 480, 720, 1080)
        """
        # Kiểm tra nếu có thông tin rõ ràng về độ phân giải
        if 'resolution' in video_data:
            return video_data.get('resolution', 0)
            
        # Ước tính dựa trên tiêu đề
        title = video_data.get('title', '').upper()
        
        if '4K' in title or '2160P' in title:
            return 2160
        elif '1440P' in title or 'QHD' in title:
            return 1440
        elif '1080P' in title or 'FULL HD' in title or 'FHD' in title:
            return 1080
        elif '720P' in title or 'HD' in title:
            return 720
        elif '480P' in title:
            return 480
        elif '360P' in title:
            return 360
        elif '240P' in title:
            return 240
            
        # Giá trị mặc định
        return 480  # Giả sử video có độ phân giải trung bình

# Ví dụ sử dụng
if __name__ == "__main__":
    video_searcher = VideoSearch()
    
    # Tìm kiếm video
    results = video_searcher.search_videos("nature waterfalls", max_results=3)
    
    if results:
        print(f"Found {len(results)} videos")
        for i, video in enumerate(results):
            print(f"\nVideo {i+1}: {video['title']}")
            print(f"Duration: {video['duration']} seconds")
            print(f"Platform: {video['platform']}")
            print(f"URL: {video['url']}")
            print(f"Thumbnail: {video['thumbnail']}")
            
        # Lấy một video thay thế
        alt_video = video_searcher.get_alternative_video("beautiful coral reef")
        if alt_video:
            print(f"\nAlternative video: {alt_video['title']}")
            print(f"Embed HTML: {video_searcher.get_embed_html(alt_video)}")
    else:
        print("No videos found") 