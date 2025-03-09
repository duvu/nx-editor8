import os
import re
import json
import time
import random
import traceback
import requests
import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
import yt_dlp
from duckduckgo_search import DDGS
from .logger import logger
from urllib.parse import urlparse, parse_qs, quote

# Thiết lập mức log của logger thành DEBUG
logger.set_level('DEBUG')

class VideoSearch:
    """
    Lớp hỗ trợ tìm kiếm và xử lý video từ YouTube và các nền tảng khác.
    Sử dụng yt-dlp để tải thông tin video và DuckDuckGo để tìm kiếm.
    """
    
    def __init__(self):
        """Khởi tạo đối tượng VideoSearch với các cấu hình mặc định"""
        # Thiết lập session cho các request
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Khởi tạo DuckDuckGo search
        self.ddgs = DDGS()
        
        # Cấu hình mặc định cho yt-dlp
        self.ytdlp_options = {
            'format': 'best[height<=720]',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'ignoreerrors': True,
            'nocheckcertificate': True,
            'no_color': True,
            'socket_timeout': 5,  # Timeout giảm xuống 5 giây
            'geo_bypass': True,
            'age_limit': 21,  # Bỏ qua giới hạn tuổi
        }
        
        # Yêu cầu tối thiểu cho video
        self.min_duration = 10  # Giảm thời lượng tối thiểu xuống 10 giây
        self.max_duration = 1800  # Tăng thời lượng tối đa lên 30 phút
        self.min_resolution = 240  # Giảm độ phân giải tối thiểu
        
        # Danh sách các đuôi URL của các nền tảng hỗ trợ
        self.supported_platforms = [
            'youtube.com', 'youtu.be',  # YouTube
            'vimeo.com',                # Vimeo
            'dailymotion.com',          # Dailymotion
            'facebook.com',             # Facebook
            'instagram.com',            # Instagram
            'twitter.com', 'x.com',     # Twitter/X
            'linkedin.com',             # LinkedIn
            'tiktok.com',               # TikTok
            'reddit.com'                # Reddit
        ]
        
        logger.info("VideoSearch initialized")
    
    def search_videos(self, keywords: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Tìm kiếm video dựa trên từ khóa
        
        Args:
            keywords: Từ khóa tìm kiếm
            max_results: Số lượng kết quả tối đa
            
        Returns:
            Danh sách các video phù hợp với thông tin chi tiết
        """
        logger.info(f"Searching videos for keywords: '{keywords}', max results: {max_results}")
        
        # Thêm "video" vào từ khóa tìm kiếm
        if "video" not in keywords.lower():
            search_query = f"{keywords} video"
        else:
            search_query = keywords
        
        # Tìm kiếm với DuckDuckGo
        try:
            logger.info(f"Searching DuckDuckGo for: '{search_query}'")
            results = self._search_with_duckduckgo(search_query, max_results)
            logger.info(f"Found {len(results)} suitable videos for query: '{keywords}'")
            return results
        except Exception as e:
            logger.error(f"Error in video search: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return []
    
    def _search_with_duckduckgo(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Tìm kiếm video với DuckDuckGo và trích xuất thông tin
        
        Args:
            query: Từ khóa tìm kiếm
            max_results: Số lượng kết quả tối đa
            
        Returns:
            Danh sách video
        """
        try:
            # Lấy kết quả từ DuckDuckGo
            duck_results = self.search_duckduckgo_videos(query, max_results * 2)
            
            # Lọc các URL từ nền tảng được hỗ trợ
            valid_results = [result for result in duck_results 
                           if self._is_supported_video_platform(result.get('url', ''))]
            
            # Log kết quả tìm kiếm
            logger.debug(f"DuckDuckGo returned {len(duck_results)} results, {len(valid_results)} from supported platforms")
            # Ghi logs kết quả tìm kiếm từ DuckDuckGo
            logger.info(f"DuckDuckGo trả về {len(duck_results)} kết quả cho từ khóa '{query}'")
            
            for i, result in enumerate(valid_results):
                logger.debug(f"Kết quả {i+1}:")
                logger.debug(f"- Tiêu đề: {result.get('title', 'Không có tiêu đề')}")
                logger.debug(f"- URL: {result.get('url', 'Không có URL')}")
                logger.debug(f"- Thời lượng: {result.get('duration', 'Không xác định')}")
                logger.debug(f"- Thumbnail: {result.get('image', 'Không có thumbnail')}")
                logger.debug(f"- Mô tả: {result.get('description', 'Không có mô tả')}")
            # Kết quả cuối cùng
            results = []
            
            # Sử dụng trực tiếp thông tin từ DuckDuckGo mà không cần yt-dlp
            for i, result in enumerate(valid_results[:max_results * 2]):
                try:
                    url = result.get('url', '')
                    if not url:
                        continue
                        
                    logger.debug(f"Processing DuckDuckGo result {i+1}/{len(valid_results)}: {url}")
                    
                    # Trích xuất thông tin từ kết quả DuckDuckGo
                    # Chuyển đổi thời lượng từ string "MM:SS" hoặc "H:MM:SS" sang số giây
                    duration_str = result.get('duration', '0:00')
                    duration = 0
                    
                    try:
                        if duration_str:
                            parts = duration_str.split(':')
                            if len(parts) == 2:  # MM:SS
                                duration = int(parts[0]) * 60 + int(parts[1])
                            elif len(parts) == 3:  # H:MM:SS
                                duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    except Exception as e:
                        logger.debug(f"Error parsing duration '{duration_str}': {str(e)}")
                    
                    # Tạo đối tượng video từ kết quả DuckDuckGo
                    platform = self._get_platform_from_url(url)
                    embed_url = self._get_embed_url(url, {})
                    
                    # Tạo thumbnail URL cho YouTube từ URL video (không cần yt-dlp)
                    thumbnail = result.get('image', '')
                    if not thumbnail and 'youtube' in platform.lower():
                        # Trích xuất ID video từ URL (nếu có thể)
                        video_id = None
                        parsed_url = urlparse(url)
                        
                        if 'youtube.com' in parsed_url.netloc and 'v=' in url:
                            query_params = parse_qs(parsed_url.query)
                            video_id = query_params.get('v', [None])[0]
                        elif 'youtu.be' in parsed_url.netloc:
                            video_id = parsed_url.path.strip('/')
                        
                        if video_id:
                            thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                    
                    video_info = {
                        'url': url,
                        'title': result.get('title', 'Unknown Title'),
                        'description': result.get('description', ''),
                        'thumbnail': thumbnail,
                        'duration': duration,
                        'view_count': 0,  # Không có trong kết quả DuckDuckGo
                        'upload_date': '',
                        'channel': result.get('content', '').split(' by ')[-1] if result.get('content', '') else 'Unknown',
                        'channel_url': '',
                        'embed_url': embed_url,
                        'platform': platform,
                        'resolution': 0,
                        'source': 'duckduckgo'
                    }
                    
                    # Luôn chấp nhận video, không cần kiểm tra thời lượng hay metadata
                    logger.debug(f"Added video: {video_info.get('title', url)}")
                    results.append(video_info)
                
                except Exception as e:
                    logger.warning(f"Error processing DuckDuckGo result {url}: {str(e)}")
                
                # Dừng khi đã có đủ kết quả
                if len(results) >= max_results:
                    break
            
            logger.info(f"DuckDuckGo provided {len(results)} usable video results")
            return results
            
        except Exception as e:
            logger.error(f"Error in _search_with_duckduckgo: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return []
    
    def search_duckduckgo_videos(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Tìm kiếm video trên DuckDuckGo
        
        Args:
            query: Từ khóa tìm kiếm
            max_results: Số lượng kết quả tối đa
            
        Returns:
            Danh sách kết quả tìm kiếm
        """
        try:
            logger.info(f"Searching DuckDuckGo for videos: '{query}'")
            
            # Sử dụng DuckDuckGo để tìm kiếm video - thử với các cấp độ safesearch khác nhau
            try:
                # Thử với safesearch=Off
                results = list(self.ddgs.videos(
                    keywords=query,
                    max_results=max_results,
                    safesearch="off"
                ))
                
                # Nếu không có kết quả, thử lại với moderate
                if not results:
                    logger.debug("No results with safesearch=off, trying with moderate")
                    results = list(self.ddgs.videos(
                        keywords=query,
                        max_results=max_results,
                        safesearch="moderate"
                    ))
            except Exception as e:
                logger.warning(f"Error with specific safesearch setting: {e}")
                # Fallback to default
                results = list(self.ddgs.videos(
                    keywords=query,
                    max_results=max_results
                ))
            
            logger.info(f"DuckDuckGo returned {len(results)} video results")
            # Ghi logs kết quả tìm kiếm
            logger.info(f"DuckDuckGo trả về {len(results)} kết quả cho từ khóa '{query}'")
            
            for i, result in enumerate(results):
                logger.debug(f"Kết quả {i+1}:")
                logger.debug(f"- Tiêu đề: {result.get('title', 'Không có tiêu đề')}")
                logger.debug(f"- URL: {result.get('url', 'Không có URL')}")
                logger.debug(f"- Thời lượng: {result.get('duration', 'Không xác định')}")
                logger.debug(f"- Thumbnail: {result.get('image', 'Không có thumbnail')}")
                logger.debug(f"- Mô tả: {result.get('description', 'Không có mô tả')}")
            # Log một số kết quả đầu tiên để debug
            if results:
                for i, r in enumerate(results[:3]):
                    logger.debug(f"DDG result {i+1}: {r.get('title')} - {r.get('url')}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching DuckDuckGo videos: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return []
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Lấy thông tin chi tiết về video từ URL
        
        Args:
            url: URL của video cần lấy thông tin
            
        Returns:
            Thông tin chi tiết về video hoặc None nếu không thể lấy
        """
        if not self._is_supported_video_platform(url):
            logger.debug(f"Unsupported video platform for URL: {url}")
            return None
            
        logger.debug(f"Getting info for video URL: {url}")
        
        try:
            # Thêm tùy chọn extra_verbose cho debug chi tiết hơn
            options = {**self.ytdlp_options}
            
            with yt_dlp.YoutubeDL(options) as ydl:
                try:
                    # Lấy thông tin cơ bản trước
                    basic_info = ydl.extract_info(url, download=False, process=False)
                    
                    if not basic_info:
                        logger.warning(f"Could not extract basic info from {url}")
                        return None
                    
                    # Nếu là playlist, lấy video đầu tiên
                    if 'entries' in basic_info:
                        if not basic_info['entries']:
                            logger.warning("Playlist has no entries")
                            return None
                            
                        # Lấy URL của video đầu tiên
                        if '_type' in basic_info and basic_info['_type'] == 'playlist':
                            first_entry = basic_info['entries'][0]
                            if 'url' in first_entry:
                                logger.debug(f"Processing first video in playlist: {first_entry.get('url')}")
                                return self.get_video_info(first_entry['url'])
                            else:
                                logger.warning("First entry in playlist has no URL")
                                return None
                    
                    # Lấy thông tin đầy đủ
                    try:
                        info = ydl.extract_info(url, download=False)
                    except Exception as e:
                        logger.warning(f"Error extracting full info: {str(e)}")
                        # Sử dụng thông tin cơ bản nếu không lấy được thông tin đầy đủ
                        info = basic_info
                    
                    # Chuẩn bị dữ liệu video
                    video_info = {
                        'url': url,
                        'title': info.get('title', 'Unknown Title'),
                        'description': info.get('description', ''),
                        'thumbnail': self._get_best_thumbnail(info),
                        'duration': info.get('duration', 0),
                        'view_count': info.get('view_count', 0),
                        'upload_date': self._format_date(info.get('upload_date', '')),
                        'channel': info.get('uploader', 'Unknown'),
                        'channel_url': info.get('uploader_url', ''),
                        'embed_url': self._get_embed_url(url, info),
                        'resolution': self._get_max_resolution(info),
                        'format': info.get('format', ''),
                        'platform': self._get_platform_from_url(url)
                    }
                    
                    logger.debug(f"Successfully extracted info for video: {video_info['title']} (duration: {video_info['duration']}s)")
                    return video_info
                    
                except yt_dlp.utils.DownloadError as e:
                    logger.warning(f"yt-dlp download error for {url}: {str(e)}")
                    # Tạo metadata tối thiểu từ URL
                    return self._create_minimal_video_info(url)
                
        except Exception as e:
            logger.error(f"Error getting video info for {url}: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return None
    
    def _create_minimal_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Tạo thông tin tối thiểu cho video khi không thể lấy đầy đủ
        
        Args:
            url: URL của video
            
        Returns:
            Thông tin cơ bản về video
        """
        logger.debug(f"Creating minimal video info for: {url}")
        
        try:
            platform = self._get_platform_from_url(url)
            
            # Trích xuất ID video từ URL (nếu có thể)
            video_id = None
            parsed_url = urlparse(url)
            
            if 'youtube.com' in parsed_url.netloc and 'v=' in url:
                video_id = parse_qs(parsed_url.query).get('v', [None])[0]
            elif 'youtu.be' in parsed_url.netloc:
                video_id = parsed_url.path.strip('/')
            
            # Tạo thumbnail URL cho YouTube
            thumbnail = ""
            if video_id and ('youtube' in platform.lower() or 'youtu.be' in url):
                thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            
            # Tạo URL nhúng
            embed_url = self._get_embed_url(url, {})
            
            # Tạo tiêu đề từ URL
            path_parts = parsed_url.path.split('/')
            title_part = path_parts[-1] if path_parts else ""
            title = title_part.replace('-', ' ').replace('_', ' ').capitalize() or f"Video on {platform}"
            
            return {
                'url': url,
                'title': title,
                'description': '',
                'thumbnail': thumbnail,
                'duration': 0,  # Không có thông tin thời lượng
                'view_count': 0,
                'channel': platform,
                'channel_url': '',
                'embed_url': embed_url,
                'platform': platform,
                'resolution': 0,
                'format': '',
                'upload_date': ''
            }
        except Exception as e:
            logger.error(f"Error creating minimal video info: {str(e)}")
            return None
    
    def is_video_url_accessible(self, url: str, timeout: int = 10) -> bool:
        """
        Kiểm tra xem URL video có thể truy cập được không
        
        Args:
            url: URL của video cần kiểm tra
            timeout: Thời gian timeout cho request (giây)
            
        Returns:
            True nếu URL có thể truy cập, False nếu không
        """
        if not self._is_supported_video_platform(url):
            logger.debug(f"Unsupported video platform: {url}")
            return False
            
        try:
            # Trước tiên thử kiểm tra bằng cách gửi HEAD request
            response = self.session.head(url, timeout=timeout, allow_redirects=True)
            if response.status_code < 400:
                logger.debug(f"URL accessible via HEAD request: {url}")
                return True
                
            # Nếu HEAD request không thành công, thử dùng yt-dlp để kiểm tra
            logger.debug(f"HEAD request failed, trying yt-dlp for: {url}")
            check_options = {
                'quiet': True,
                'skip_download': True,
                'playlist_items': '1',
                'ignoreerrors': True,
                'socket_timeout': timeout
            }
            
            with yt_dlp.YoutubeDL(check_options) as ydl:
                info = ydl.extract_info(url, download=False, process=False)
                if info:
                    logger.debug(f"URL accessible via yt-dlp: {url}")
                    return True
                    
            logger.warning(f"Video URL is not accessible: {url}")
            return False
            
        except Exception as e:
            logger.warning(f"Error checking video URL {url}: {str(e)}")
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
            keywords = "nature documentary video"
        
        logger.info(f"Searching for alternative video with keywords: '{keywords}'")
        
        # Thêm "HD" vào từ khóa nếu chưa có
        if "HD" not in keywords.upper():
            search_query = f"{keywords} HD"
        else:
            search_query = keywords
        
        try:
            # Tìm kiếm trực tiếp với DuckDuckGo để tăng tốc độ
            duck_results = self.search_duckduckgo_videos(search_query, max_results=10)
            logger.info(f"DuckDuckGo trả về {len(duck_results)} kết quả cho từ khóa '{search_query}'")
            
            # Log thông tin chi tiết về các kết quả
            for i, result in enumerate(duck_results):
                url = result.get('url', 'Không có URL')
                title = result.get('title', 'Không có tiêu đề')
                is_supported = self._is_supported_video_platform(url)
                logger.debug(f"Kết quả #{i+1}: {title} - {url} - Hỗ trợ: {is_supported}")
                
                # Log domain của URL để kiểm tra
                if url:
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc.lower()
                    logger.debug(f"Domain: {domain}")
                    
                    # Kiểm tra xem domain có khớp với bất kỳ platform nào không
                    matches = [platform for platform in self.supported_platforms if platform in domain]
                    logger.debug(f"Khớp với platforms: {matches}")
            
            # Lọc các URL từ nền tảng được hỗ trợ
            valid_results = [result for result in duck_results 
                           if self._is_supported_video_platform(result.get('url', ''))]
            
            logger.info(f"Sau khi lọc, còn {len(valid_results)} kết quả hợp lệ từ các nền tảng được hỗ trợ")
            
            if not valid_results:
                # Nếu không có kết quả hợp lệ, kiểm tra danh sách nền tảng hỗ trợ
                logger.warning(f"No valid video results found for keywords: '{keywords}'")
                logger.debug(f"Supported platforms: {self.supported_platforms}")
                
                # Thử bỏ qua kiểm tra nền tảng và sử dụng kết quả đầu tiên
                if duck_results:
                    logger.info("Sử dụng kết quả đầu tiên bất kể nền tảng")
                    selected_result = duck_results[0]
                    url = selected_result.get('url', '')
                    
                    # Log URL đầy đủ
                    logger.debug(f"Selected URL: {url}")
                    
                    # Tạo thông tin video từ kết quả DuckDuckGo
                    platform = "Unknown"
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc.lower()
                    logger.debug(f"Using domain: {domain}")
                    
                    # Sử dụng URL gốc cho cả URL thông thường và URL nhúng
                    embed_url = self._get_embed_url_from_regular_url(url)
                    logger.debug(f"Generated embed URL: {embed_url}")
                    
                    # Chuyển đổi thời lượng từ string "MM:SS" sang số giây
                    duration_str = selected_result.get('duration', '0:00')
                    duration = 0
                    
                    try:
                        if duration_str:
                            parts = duration_str.split(':')
                            if len(parts) == 2:  # MM:SS
                                duration = int(parts[0]) * 60 + int(parts[1])
                            elif len(parts) == 3:  # H:MM:SS
                                duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    except Exception as e:
                        logger.debug(f"Error parsing duration '{duration_str}': {str(e)}")
                    
                    # Tạo URL thumbnail nếu không có
                    thumbnail = selected_result.get('image', '')
                    if not thumbnail and 'youtube' in domain:
                        video_id = self._extract_youtube_id(url)
                        if video_id:
                            thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                            logger.debug(f"Generated YouTube thumbnail: {thumbnail}")
                    
                    video_info = {
                        'url': url,
                        'title': selected_result.get('title', 'Unknown Title'),
                        'description': selected_result.get('description', ''),
                        'thumbnail': thumbnail,
                        'duration': duration,
                        'view_count': 0,
                        'upload_date': '',
                        'channel': selected_result.get('content', '').split(' by ')[-1] if selected_result.get('content', '') else 'Unknown',
                        'channel_url': '',
                        'embed_url': embed_url,
                        'platform': platform,
                        'resolution': 0,
                        'source': 'duckduckgo'
                    }
                    
                    logger.info(f"Selected fallback video: {video_info.get('title')}")
                    return video_info
                
                return None
                
            # Chọn ngẫu nhiên một video
            selected_result = random.choice(valid_results)
            
            # Tạo thông tin video từ kết quả DuckDuckGo
            url = selected_result.get('url', '')
            platform = self._get_platform_from_url(url)
            embed_url = self._get_embed_url_from_regular_url(url)
            
            # Tạo thumbnail URL cho YouTube từ URL video
            thumbnail = selected_result.get('image', '')
            if not thumbnail and 'youtube' in platform.lower():
                video_id = self._extract_youtube_id(url)
                if video_id:
                    thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            
            # Chuyển đổi thời lượng từ string "MM:SS" sang số giây
            duration_str = selected_result.get('duration', '0:00')
            duration = 0
            
            try:
                if duration_str:
                    parts = duration_str.split(':')
                    if len(parts) == 2:  # MM:SS
                        duration = int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:  # H:MM:SS
                        duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except Exception as e:
                logger.debug(f"Error parsing duration '{duration_str}': {str(e)}")
            
            video_info = {
                'url': url,
                'title': selected_result.get('title', 'Unknown Title'),
                'description': selected_result.get('description', ''),
                'thumbnail': thumbnail,
                'duration': duration,
                'view_count': 0,
                'upload_date': '',
                'channel': selected_result.get('content', '').split(' by ')[-1] if selected_result.get('content', '') else 'Unknown',
                'channel_url': '',
                'embed_url': embed_url,
                'platform': platform,
                'resolution': 0,
                'source': 'duckduckgo'
            }
            
            logger.info(f"Selected alternative video: {video_info.get('title')}")
            return video_info
            
        except Exception as e:
            logger.error(f"Error getting alternative video: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return None
    
    def _get_embed_url_from_regular_url(self, url: str) -> str:
        """
        Chuyển đổi URL thông thường thành URL nhúng
        
        Args:
            url: URL thông thường của video
            
        Returns:
            URL nhúng
        """
        if not url:
            return ""
            
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # YouTube
            if 'youtube.com' in domain or 'youtu.be' in domain:
                video_id = self._extract_youtube_id(url)
                if video_id:
                    return f"https://www.youtube.com/embed/{video_id}"
                    
            # Vimeo
            elif 'vimeo.com' in domain:
                video_id = url.split('/')[-1]
                if video_id.isdigit():
                    return f"https://player.vimeo.com/video/{video_id}"
                    
            # Dailymotion
            elif 'dailymotion.com' in domain:
                video_id = url.split('/')[-1].split('_')[0]
                return f"https://www.dailymotion.com/embed/video/{video_id}"
                
            # Facebook
            elif 'facebook.com' in domain:
                if 'watch' in url:
                    return url.replace('watch', 'plugins/video.php') + "&show_text=0"
                else:
                    return url
                    
            # TikTok
            elif 'tiktok.com' in domain:
                return f"https://www.tiktok.com/embed/v2/{url.split('/')[-1]}"
                
            # Mặc định trả về URL gốc
            logger.debug(f"No special embed URL handling for domain {domain}, using original URL")
            return url
                
        except Exception as e:
            logger.error(f"Error creating embed URL from {url}: {str(e)}")
            return url
            
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
            if parsed_url.netloc in ('youtube.com', 'www.youtube.com'):
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
        embed_url = video_info.get('embed_url', '')
        url = video_info.get('url', '')
        
        if not embed_url and url:
            # Tạo embed URL từ URL thông thường nếu không có sẵn
            embed_url = self._get_embed_url_from_regular_url(url)
            logger.debug(f"Generated embed URL from regular URL: {embed_url}")
        
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
        
        platform = video_info.get('platform', '').lower()
        
        # YouTube
        if 'youtube' in platform:
            return f'<iframe width="{width}" height="{height}" src="{embed_url}" frameborder="0" allowfullscreen></iframe>'
            
        # Vimeo
        elif 'vimeo' in platform:
            return f'<iframe src="{embed_url}" width="{width}" height="{height}" frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe>'
            
        # Facebook
        elif 'facebook' in platform:
            return f'<iframe src="{embed_url}" width="{width}" height="{height}" style="border:none;overflow:hidden" scrolling="no" frameborder="0" allowfullscreen="true" allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"></iframe>'
            
        # Instagram
        elif 'instagram' in platform:
            return f'<iframe width="{width}" height="{height}" src="{embed_url}" frameborder="0" scrolling="no" allowtransparency="true"></iframe>'
            
        # TikTok
        elif 'tiktok' in platform:
            return f'<blockquote class="tiktok-embed" cite="{url}" data-video-id="{url.split("/")[-1]}" style="max-width: {width}px; min-width: 325px;"><section></section></blockquote><script async src="https://www.tiktok.com/embed.js"></script>'
            
        # Twitter
        elif 'twitter' in platform or 'x.com' in platform:
            tweet_id = url.split('/')[-1]
            return f'<blockquote class="twitter-tweet" data-width="{width}" data-dnt="true"><a href="{url}"></a></blockquote><script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'
            
        # Dailymotion
        elif 'dailymotion' in platform:
            return f'<iframe frameborder="0" width="{width}" height="{height}" src="{embed_url}" allowfullscreen allow="autoplay"></iframe>'
        
        # Mặc định nếu không có xử lý đặc biệt
        logger.debug(f"Using default iframe for platform: {platform}")
        return f'<iframe width="{width}" height="{height}" src="{embed_url}" frameborder="0" allowfullscreen></iframe>'
    
    def _is_supported_video_platform(self, url: str) -> bool:
        """Kiểm tra xem URL có phải từ nền tảng video được hỗ trợ không"""
        if not url:
            logger.debug("Empty URL provided to _is_supported_video_platform")
            return False
            
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            logger.debug(f"Checking if domain '{domain}' is supported")
            
            # Kiểm tra từng platform trong danh sách hỗ trợ
            supported = False
            for platform in self.supported_platforms:
                if platform in domain:
                    logger.debug(f"Matched with supported platform: {platform}")
                    supported = True
                    break
            
            # Thêm kiểm tra đặc biệt cho các trang video có domain không chuẩn
            if not supported:
                # Kiểm tra một số trường hợp đặc biệt
                special_cases = [
                    ('bilibili.com', 'Bilibili'),
                    ('twitch.tv', 'Twitch'),
                    ('v.qq.com', 'Tencent Video'),
                    ('iqiyi.com', 'iQIYI'),
                    ('video.google.com', 'Google Video'),
                    ('m.youtube.com', 'YouTube Mobile'),
                    ('youku.com', 'Youku'),
                    ('nicovideo.jp', 'Niconico'),
                    ('tv.naver.com', 'Naver TV'),
                    ('slideshare.net', 'SlideShare'),
                    ('vk.com', 'VK'),
                    ('rutube.ru', 'RuTube'),
                    # Thêm các trường hợp đặc biệt khác
                ]
                
                for case, platform_name in special_cases:
                    if case in domain:
                        logger.debug(f"Matched with special case platform: {platform_name}")
                        supported = True
                        # Thêm vào danh sách nền tảng hỗ trợ để lần sau không cần kiểm tra đặc biệt
                        if case not in self.supported_platforms:
                            self.supported_platforms.append(case)
                        break
            
            # Bỏ qua kiểm tra nền tảng nếu URL chứa từ khóa "video"
            if not supported and ("video" in url.lower() or "watch" in url.lower()):
                logger.debug(f"URL contains 'video' or 'watch', assuming it's a video: {url}")
                supported = True
            
            if not supported:
                logger.debug(f"URL from unsupported platform: {domain}")
            
            return supported
        except Exception as e:
            logger.error(f"Error checking platform support for URL '{url}': {str(e)}")
            # Trong trường hợp lỗi, coi như hỗ trợ để tránh bỏ qua các video hợp lệ
            return True
    
    def _get_best_thumbnail(self, info: Dict[str, Any]) -> str:
        """Lấy URL thumbnail chất lượng cao nhất từ thông tin video"""
        if not info:
            return ""
            
        # Kiểm tra thumbnails trong các định dạng khác nhau
        if 'thumbnails' in info and isinstance(info['thumbnails'], list) and info['thumbnails']:
            # Sắp xếp theo kích thước (nếu có)
            sorted_thumbs = sorted(
                [t for t in info['thumbnails'] if 'url' in t],
                key=lambda x: x.get('width', 0) * x.get('height', 0) if x.get('width') and x.get('height') else 0,
                reverse=True
            )
            if sorted_thumbs:
                return sorted_thumbs[0]['url']
        
        # Fallback vào trường thumbnail đơn
        return info.get('thumbnail', "")
    
    def _format_date(self, date_str: str) -> str:
        """Format ngày tháng từ định dạng YYYYMMDD sang YYYY-MM-DD"""
        if not date_str or len(date_str) != 8:
            return ""
            
        try:
            year = date_str[0:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{year}-{month}-{day}"
        except:
            return date_str
    
    def _get_embed_url(self, original_url: str, info: Dict[str, Any]) -> str:
        """Tạo URL nhúng từ URL video gốc và thông tin video"""
        # Kiểm tra nếu thông tin có sẵn URL nhúng
        if info and 'embed_url' in info:
            return info['embed_url']
            
        parsed_url = urlparse(original_url)
        domain = parsed_url.netloc.lower()
        
        # YouTube
        if 'youtube.com' in domain or 'youtu.be' in domain:
            video_id = None
            if 'youtube.com' in domain and 'v=' in original_url:
                query = parse_qs(parsed_url.query)
                video_id = query.get('v', [None])[0]
            elif 'youtu.be' in domain:
                video_id = parsed_url.path.strip('/')
                
            if video_id:
                return f"https://www.youtube.com/embed/{video_id}"
        
        # Vimeo
        elif 'vimeo.com' in domain:
            match = re.search(r'vimeo\.com/(\d+)', original_url)
            if match:
                video_id = match.group(1)
                return f"https://player.vimeo.com/video/{video_id}"
        
        # Dailymotion
        elif 'dailymotion.com' in domain:
            match = re.search(r'dailymotion\.com/(?:video|embed)/([a-zA-Z0-9]+)', original_url)
            if match:
                video_id = match.group(1)
                return f"https://www.dailymotion.com/embed/video/{video_id}"
        
        # Facebook
        elif 'facebook.com' in domain:
            if 'videos' in original_url:
                return f"https://www.facebook.com/plugins/video.php?href={original_url}"
        
        # Trong trường hợp không thể tạo URL nhúng
        return original_url
    
    def _get_max_resolution(self, info: Dict[str, Any]) -> int:
        """Lấy độ phân giải cao nhất có sẵn từ thông tin video"""
        if not info:
            return 0
            
        # Thử lấy từ formats nếu có
        if 'formats' in info and isinstance(info['formats'], list):
            max_height = 0
            for fmt in info['formats']:
                if fmt.get('height') and isinstance(fmt['height'], int):
                    max_height = max(max_height, fmt['height'])
            
            if max_height > 0:
                return max_height
        
        # Fallback vào thông tin tổng quát
        return info.get('height', 0)
    
    def _get_platform_from_url(self, url: str) -> str:
        """Xác định nền tảng video từ URL"""
        if not url:
            return "unknown"
            
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        if 'youtube.com' in domain or 'youtu.be' in domain:
            return "YouTube"
        elif 'vimeo.com' in domain:
            return "Vimeo"
        elif 'dailymotion.com' in domain:
            return "Dailymotion"
        elif 'facebook.com' in domain:
            return "Facebook"
        elif 'instagram.com' in domain:
            return "Instagram"
        elif 'twitter.com' in domain or 'x.com' in domain:
            return "Twitter/X"
        elif 'tiktok.com' in domain:
            return "TikTok"
        elif 'linkedin.com' in domain:
            return "LinkedIn"
        elif 'reddit.com' in domain:
            return "Reddit"
        else:
            return "Other"

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