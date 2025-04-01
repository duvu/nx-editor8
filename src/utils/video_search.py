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
import ssl
import certifi
import os
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs, quote_plus

import requests
import yt_dlp
from src.logger import logger



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
        
        # Set SSL verification using certifi or system certificates
        cert_paths = [
            certifi.where(),  # certifi's certificates
            '/etc/ssl/certs/ca-certificates.crt',  # Debian/Ubuntu/Gentoo etc.
            '/etc/pki/tls/certs/ca-bundle.crt',  # Fedora/RHEL 6
            '/etc/ssl/ca-bundle.pem',  # OpenSUSE
            '/etc/pki/tls/cacert.pem',  # OpenELEC
            '/etc/ssl/cert.pem',  # Alpine Linux and macOS
        ]
        
        for cert_path in cert_paths:
            if os.path.exists(cert_path):
                try:
                    self.session.verify = cert_path
                    logger.info(f"Using SSL certificates from: {cert_path}")
                    
                    # Set environment variables for other libraries
                    os.environ['REQUESTS_CA_BUNDLE'] = cert_path
                    os.environ['SSL_CERT_FILE'] = cert_path
                    
                    # Set certificate verification mode for urllib3/requests
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    
                    break
                except Exception as e:
                    logger.warning(f"Failed to use certificate path {cert_path}: {str(e)}")
        else:
            # If no certificate path works, use the default verification
            logger.warning("No valid certificate path found, using system default verification")
            self.session.verify = True
        
        # Cấu hình mặc định cho yt-dlp
        self.ytdlp_options = {
            'format': 'best[height<=720]',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Khai thác nhanh
            'skip_download': True,
            'ignoreerrors': True,
            'nocheckcertificate': True,  # Skip certificate verification in yt-dlp
            'no_color': True,
            'socket_timeout': 10, 
            'geo_bypass': True,
            'age_limit': 21,  # Bỏ qua giới hạn tuổi
        }
        
        # Add certificate path to yt-dlp options
        try:
            cert_path = certifi.where()
            if cert_path:
                self.ytdlp_options['http_headers'] = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                os.environ['REQUESTS_CA_BUNDLE'] = cert_path
                os.environ['SSL_CERT_FILE'] = cert_path
                logger.info(f"Set certificate path for yt-dlp: {cert_path}")
        except Exception as e:
            logger.warning(f"Failed to set certificate path for yt-dlp: {str(e)}")
        
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
        
    def search_videos(self, keywords: str, max_results: int = 5, creative_commons_only: bool = False) -> List[Dict[str, Any]]:
        """
        Tìm kiếm video YouTube dựa trên từ khóa
        
        Args:
            keywords: Từ khóa tìm kiếm
            max_results: Số lượng kết quả tối đa
            creative_commons_only: Chỉ trả về video có giấy phép Creative Commons
            
        Returns:
            Danh sách thông tin video
        """
        if not keywords:
            return []
            
        # Determine the search query and YT-DLP search target URL
        search_keywords = keywords
        search_target = f"ytsearch{max_results * 2}:{search_keywords}" # Search more initially to filter later
        
        if creative_commons_only:
            # Use YouTube search filter for Creative Commons
            search_target = f"ytsearch{max_results * 4}:{search_keywords},creativecommons" # Search even more for CC
            logger.info(f"Searching for Creative Commons videos using filter: '{search_keywords}', target: {search_target}")
        else:
            logger.info(f"Searching videos for keywords: '{keywords}', max results: {max_results}, target: {search_target}")
        
        start_time = time.time()
        
        try:
            # Tìm kiếm video trên YouTube using the constructed target
            search_results = self._search_youtube_videos(search_target) # Pass the target URL directly
            
            if not search_results:
                logger.warning(f"No search results found for target: '{search_target}'")
                return []
                
            logger.info(f"Found {len(search_results)} initial results for target: '{search_target}'")
            
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
                    'source': 'youtube_search',
                    'license': video_data.get('license', 'unknown')
                }
                
                # Nếu chỉ tìm Creative Commons, VẪN kiểm tra giấy phép để xác nhận
                if creative_commons_only and not self._is_creative_commons(video_data):
                    logger.debug(f"Skipping video despite CC filter (failed validation): {video_info['title']}")
                    continue
                    
                processed_videos.append(video_info)
                
                # Dừng nếu đã đủ số lượng kết quả
                if len(processed_videos) >= max_results:
                    break
            
            elapsed_time = time.time() - start_time
            logger.info(f"Found {len(processed_videos)} suitable videos for query: '{search_keywords}' (CC: {creative_commons_only}) in {elapsed_time:.2f} seconds")
            
            return processed_videos
            
        except Exception as e:
            logger.error(f"Error searching videos: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return []
    
    def _search_youtube_videos(self, search_target: str) -> List[Dict[str, Any]]:
        """
        Tìm kiếm video trên YouTube sử dụng yt-dlp

        Args:
            search_target: Chuỗi tìm kiếm yt-dlp (e.g., "ytsearch20:query,filter")

        Returns:
            Danh sách thông tin video hoặc danh sách rỗng nếu lỗi
        """
        logger.info(f"Searching YouTube using target: '{search_target}'")

        try:
            # Cấu hình yt-dlp cho tìm kiếm
            ydl_opts = {
                **self.ytdlp_options,
                **self.search_options,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                },
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                        'player_skip': ['configs', 'webpage']
                    }
                }
            }

            # Thực hiện tìm kiếm
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    search_results = ydl.extract_info(search_target, download=False)

                    if not search_results or 'entries' not in search_results:
                        logger.warning(f"No results found or invalid response for target: '{search_target}'")
                        # REMOVED FALLBACK CALL
                        return []

                    logger.info(f"YouTube search returned {len(search_results['entries'])} results")

                    # Filter out None entries
                    valid_entries = [entry for entry in search_results['entries'] if entry is not None]

                    if not valid_entries:
                        logger.warning(f"All entries from YouTube search were None for target: '{search_target}'")
                        # REMOVED FALLBACK CALL
                        return []

                    return valid_entries
            except Exception as e:
                logger.error(f"Error with yt-dlp search for target '{search_target}': {str(e)}")
                # REMOVED FALLBACK CALL
                return []

        except Exception as e:
            logger.error(f"Error during YouTube search setup for target '{search_target}': {str(e)}")
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
                # Return minimal info for non-YouTube or None if ID extraction fails
                return self._create_minimal_video_info(url)

            # Extract video ID from URL
            video_id = self._extract_youtube_id(url)
            if not video_id:
                logger.warning(f"Could not extract video ID from URL: {url}")
                return None # Changed from minimal info

            # Enhanced options for yt-dlp
            ydl_opts = {
                **self.ytdlp_options,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                },
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                        'player_skip': ['configs', 'webpage']
                    }
                }
            }

            # Try to get video info with yt-dlp first
            try:
                # Sử dụng yt-dlp để lấy thông tin video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                    if not info:
                        logger.warning(f"Could not extract info via yt-dlp for URL: {url}")
                        # REMOVED FALLBACK CALL
                        return None

                    # Tạo thông tin video
                    video_info = {
                        'id': video_id,
                        'url': url,
                        'title': info.get('title', f'YouTube Video {video_id}'), # Use ID if title missing
                        'description': info.get('description', ''),
                        'thumbnail': self._get_best_thumbnail(info) or self._get_thumbnail_url(video_id),
                        'duration': info.get('duration', 0),
                        'view_count': info.get('view_count', 0),
                        'upload_date': self._format_date(info.get('upload_date', '')),
                        'channel': info.get('uploader', 'Unknown'),
                        'channel_url': info.get('uploader_url', ''),
                        'embed_url': f"https://www.youtube.com/embed/{video_id}",
                        'platform': 'youtube',
                        'resolution': self._get_max_resolution(info),
                        'license': info.get('license', 'unknown'), # Include license info
                        'source': 'yt_dlp'
                    }

                    elapsed_time = time.time() - start_time
                    logger.info(f"Video info retrieved via yt-dlp in {elapsed_time:.2f} seconds")
                    return video_info
            except Exception as e:
                logger.error(f"Error with yt-dlp video info extraction for {url}: {str(e)}")
                # REMOVED FALLBACK CALL
                return None

        except Exception as e:
            logger.error(f"Error getting video info for {url}: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return None

    def _create_minimal_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        # Keep this helper, but it's now only for non-YouTube URLs or when ID extraction fails in get_video_info
        logger.info(f"Creating minimal video info for URL: {url}")
        try:
            video_id = self._extract_youtube_id(url)
            if video_id:
                # This case might be redundant now if get_video_info returns None on ID failure
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
                    'source': 'minimal_yt_id'
                }
            else:
                # URL is not YouTube or ID extraction failed
                parsed_url = urlparse(url)
                domain = parsed_url.netloc or 'unknown domain'
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
                    'source': 'minimal_non_yt'
                }
        except Exception as e:
            logger.error(f"Error creating minimal video info for {url}: {str(e)}")
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
    
    def get_alternative_video(self, keywords: str, creative_commons_only: bool = False) -> Optional[Dict[str, Any]]:
        """
        Tìm video thay thế khi không tìm thấy video phù hợp.
        Returns None if no suitable video is found (no fallback).

        Args:
            keywords: Từ khóa tìm kiếm
            creative_commons_only: Chỉ tìm video có giấy phép Creative Commons

        Returns:
            Thông tin video thay thế hoặc None nếu không tìm thấy
        """
        if not keywords:
            logger.warning("No keywords provided for alternative video search, using default")
            keywords = "nature documentary HD"

        license_type = "Creative Commons" if creative_commons_only else "Standard"
        logger.info(f"Searching for alternative {license_type} video with keywords: '{keywords}'")

        # Prepare search query/target
        search_query = keywords
        if "HD" not in keywords.upper():
            search_query = f"{keywords} HD"

        if creative_commons_only:
            search_target = f"ytsearch12:{search_query},creativecommons"
            logger.info(f"Using search target: '{search_target}'")
        else:
            search_target = f"ytsearch12:{search_query}"
            logger.info(f"Using search target: '{search_target}'")

        try:
            # Tìm kiếm video trên YouTube
            results = self._search_youtube_videos(search_target)

            if not results:
                logger.warning(f"No alternative videos found for target: '{search_target}'")
                # REMOVED FALLBACK CALL
                return None

            logger.info(f"Found {len(results)} potential alternative videos")

            # Select a random video from the results (apply CC filter if needed)
            valid_results = results # Start with all results

            if creative_commons_only:
                # Filter for CC *after* search, using metadata check as confirmation
                cc_results = []
                for r in valid_results:
                    # Need more info than search results provide for robust CC check
                    # Let's get full info for a few candidates
                    video_id_alt = r.get('id') or self._extract_youtube_id(r.get('url', ''))
                    if video_id_alt:
                        info = self.get_video_info(f"https://www.youtube.com/watch?v={video_id_alt}")
                        if info and self._is_creative_commons(info):
                            cc_results.append(info) # Append the full info dict
                            if len(cc_results) >= 5: # Limit checks
                                break
                    else:
                        logger.debug("Skipping result with no ID for CC check.")

                if not cc_results:
                    logger.warning(f"No confirmed Creative Commons videos found among results for '{search_target}'")
                    # REMOVED FALLBACK CALL
                    return None
                valid_results = cc_results # Use the confirmed CC videos (full info)
                logger.info(f"Found {len(valid_results)} confirmed Creative Commons videos")
            else:
                 # For standard search, we still need full info for one video
                 pass # Handled below when selecting

            if not valid_results:
                 logger.warning(f"No valid results remain after filtering for target: '{search_target}'")
                 return None

            # Select a random video from the valid results
            selected_result_data = random.choice(valid_results)

            # If we already have full info (from CC check), return it
            if isinstance(selected_result_data, dict) and selected_result_data.get('source') == 'yt_dlp':
                 logger.info(f"Returning selected alternative video (already fetched): {selected_result_data.get('title')}")
                 return selected_result_data

            # Otherwise (standard search or initial CC search data), get full info now
            video_id_final = selected_result_data.get('id') or self._extract_youtube_id(selected_result_data.get('url', ''))
            if not video_id_final:
                 logger.warning("Could not get ID from randomly selected result.")
                 return None

            logger.info(f"Fetching full info for selected alternative video ID: {video_id_final}")
            final_video_info = self.get_video_info(f"https://www.youtube.com/watch?v={video_id_final}")

            if not final_video_info:
                 logger.warning(f"Failed to get full info for selected alternative video ID: {video_id_final}")
                 return None

            logger.info(f"Returning selected alternative video: {final_video_info.get('title')}")
            return final_video_info

        except Exception as e:
            logger.error(f"Error getting alternative video for '{keywords}': {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            # REMOVED FALLBACK CALL
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
            # Return placeholder if no info
            return f'<div style="width:{width}px; height:{height}px; border:1px solid #ccc; background-color:#eee; display:flex; align-items:center; justify-content:center; font-family:sans-serif; color:#888;">Video Not Available</div>'

        embed_url = video_info.get('embed_url', '')
        url = video_info.get('url', '')
        title = video_info.get('title', 'Video')

        if not embed_url and url and self._is_youtube_url(url):
            video_id = self._extract_youtube_id(url)
            if video_id:
                embed_url = f"https://www.youtube.com/embed/{video_id}"
            else:
                 embed_url = url # Fallback for non-YouTube if needed
        elif not embed_url:
             embed_url = url # Use original URL if no embed specific one

        if not embed_url:
            logger.warning(f"No embed URL available for video: {title}")
            thumbnail = video_info.get('thumbnail', '')
            # Return placeholder with title/thumbnail if no embed URL
            fallback_html = f"""
            <div style="width: {width}px; height: {height}px; border: 1px solid #ccc; display: flex; flex-direction: column; justify-content: center; align-items: center; background-color: #f9f9f9; text-align: center; padding: 10px; box-sizing: border-box; overflow: hidden;">
                {f'<img src="{thumbnail}" alt="{title}" style="max-width: 90%; max-height: 70%; object-fit: contain; margin-bottom: 10px;">' if thumbnail else ''}
                <h3 style="margin: 5px 0; font-size: 14px; font-family: Arial, sans-serif; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 95%;">{title}</h3>
                {f'<p style="margin: 5px 0; font-family: Arial, sans-serif; font-size: 11px;">URL: <a href="{url}" target="_blank" rel="noopener noreferrer" style="color: #007bff;">Link</a></p>' if url else ''}
                <p style="color: #666; font-family: Arial, sans-serif; font-size: 11px; margin-top: 5px;">Video embedding not available.</p>
            </div>
            """
            logger.debug(f"Created fallback HTML display for video without embed URL")
            return fallback_html

        # Create embed iframe
        return f'<iframe width="{width}" height="{height}" src="{embed_url}" title="{title}" frameborder="0" allowfullscreen allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"></iframe>'

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

    def _is_creative_commons(self, video_data: Dict[str, Any]) -> bool:
        """
        Kiểm tra xem video có giấy phép Creative Commons không
        
        Args:
            video_data: Thông tin video từ yt-dlp
            
        Returns:
            True nếu video có giấy phép Creative Commons
        """
        # Kiểm tra thông tin giấy phép trong metadata nếu có
        license_info = str(video_data.get('license', '')).lower()
        if license_info and ('creative commons' in license_info or 'cc by' in license_info):
            return True
        
        # Kiểm tra từ khóa trong tiêu đề
        title = str(video_data.get('title', '')).lower()
        if 'creative commons' in title or 'cc by' in title:
            return True
        
        # Kiểm tra trong mô tả video
        description = str(video_data.get('description', '')).lower()
        cc_indicators = [
            'licensed under creative commons', 
            'cc-by', 
            'cc by', 
            'creative commons attribution',
            'creative commons license'
        ]
        
        for indicator in cc_indicators:
            if indicator in description:
                return True
            
        return False

    def search_creative_commons_videos(self, keywords: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Tìm kiếm video YouTube có giấy phép Creative Commons.

        Đây là một phương thức tiện lợi gọi search_videos với creative_commons_only=True.
        
        Args:
            keywords: Từ khóa tìm kiếm
            max_results: Số lượng kết quả tối đa
            
        Returns:
            Danh sách thông tin video Creative Commons hoặc danh sách rỗng nếu không tìm thấy.
        """
        logger.info(f"Initiating Creative Commons video search for keywords: '{keywords}'")
        return self.search_videos(keywords, max_results=max_results, creative_commons_only=True)

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