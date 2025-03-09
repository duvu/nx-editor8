import os
import re
import json
import time
import random
import requests
import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
import yt_dlp
from duckduckgo_search import DDGS
from .logger import logger
from urllib.parse import urlparse, parse_qs, quote

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
            
            # Kết quả cuối cùng
            results = []
            
            # THAY ĐỔI: Sử dụng trực tiếp thông tin từ DuckDuckGo thay vì gọi yt-dlp cho mỗi URL
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
                    
                    video_info = {
                        'url': url,
                        'title': result.get('title', 'Unknown Title'),
                        'description': result.get('description', ''),
                        'thumbnail': result.get('image', ''),
                        'duration': duration,
                        'view_count': 0,  # Không có trong kết quả DuckDuckGo
                        'upload_date': '',  # Không có trong kết quả DuckDuckGo
                        'channel': result.get('content', '').split(' by ')[-1] if result.get('content', '') else 'Unknown',
                        'channel_url': '',
                        'embed_url': embed_url,
                        'platform': platform,
                        'resolution': 0,
                        'source': 'duckduckgo'
                    }
                    
                    # Kiểm tra thời lượng nếu có
                    if duration > 0:
                        # Nếu có thời lượng, kiểm tra phạm vi
                        if self.min_duration <= duration <= self.max_duration:
                            logger.debug(f"Video with valid duration ({duration}s) added: {video_info.get('title', url)}")
                            results.append(video_info)
                        else:
                            logger.debug(f"Video duration out of range ({duration}s): {video_info.get('title', url)}")
                    else:
                        # Nếu không có thời lượng, vẫn chấp nhận video
                        logger.debug(f"Video without duration accepted: {video_info.get('title', url)}")
                        results.append(video_info)
                    
                    # FALLBACK: Chỉ khi cần thông tin chi tiết mà DuckDuckGo không cung cấp
                    # và chỉ cho một số kết quả đầu tiên để tăng tốc độ
                    if i < 3 and (not video_info.get('duration') or not video_info.get('thumbnail')):
                        try:
                            logger.debug(f"Trying to enrich metadata for {url} using yt-dlp")
                            detailed_info = self.get_video_info(url)
                            if detailed_info:
                                # Chỉ cập nhật các trường còn thiếu
                                for key, value in detailed_info.items():
                                    if not video_info.get(key) and value:
                                        video_info[key] = value
                                logger.debug(f"Metadata enriched for {url}")
                        except Exception as e:
                            logger.debug(f"Failed to enrich metadata: {str(e)}")
                
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
        Tìm video thay thế dựa trên từ khóa
        
        Args:
            keywords: Từ khóa tìm kiếm
            
        Returns:
            Thông tin video thay thế hoặc None nếu không tìm thấy
        """
        if not keywords:
            keywords = "nature documentary video"
        
        logger.info(f"Searching for alternative video with keywords: '{keywords}'")
        
        # Thêm "HD" vào từ khóa để có video chất lượng cao
        if "HD" not in keywords.upper():
            search_query = f"{keywords} HD"
        else:
            search_query = keywords
        
        # Tìm kiếm video
        videos = self.search_videos(search_query, max_results=5)
        
        # Trả về video ngẫu nhiên hoặc None nếu không tìm thấy
        if videos:
            selected_video = random.choice(videos)
            logger.info(f"Selected alternative video: {selected_video.get('title')}")
            return selected_video
        
        logger.warning(f"No alternative videos found for keywords: '{keywords}'")
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
        if not embed_url:
            logger.warning(f"No embed URL available for video: {video_info.get('title', 'Unknown')}")
            return ""
        
        platform = video_info.get('platform', '').lower()
        
        # Tạo mã HTML dựa trên nền tảng
        if 'youtube' in platform:
            return f'<iframe width="{width}" height="{height}" src="{embed_url}" frameborder="0" allowfullscreen></iframe>'
        elif 'vimeo' in platform:
            return f'<iframe width="{width}" height="{height}" src="{embed_url}" frameborder="0" allow="autoplay; fullscreen" allowfullscreen></iframe>'
        elif 'facebook' in platform:
            return f'<iframe width="{width}" height="{height}" src="{embed_url}" frameborder="0" allowfullscreen></iframe>'
        elif 'dailymotion' in platform:
            return f'<iframe width="{width}" height="{height}" src="{embed_url}" frameborder="0" allowfullscreen></iframe>'
        else:
            return f'<iframe width="{width}" height="{height}" src="{embed_url}" frameborder="0" allowfullscreen></iframe>'
    
    def _is_supported_video_platform(self, url: str) -> bool:
        """Kiểm tra xem URL có phải từ nền tảng video được hỗ trợ không"""
        if not url:
            return False
            
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Kiểm tra domain có chứa bất kỳ nền tảng hỗ trợ nào
        return any(platform in domain for platform in self.supported_platforms)
    
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