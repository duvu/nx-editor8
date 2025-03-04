import requests
import json
import random
import time
from duckduckgo_search import DDGS
from io import BytesIO
from PIL import Image
from .logger import logger

class ImageSearch:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.ddgs = DDGS()
        
        # Define minimum resolution for images
        self.min_width = 800
        self.min_height = 600

    def search_duckduckgo(self, query, max_results=10):
        """
        Search DuckDuckGo for high-resolution images based on query
        
        Args:
            query: Search terms
            max_results: Maximum number of results to return
            
        Returns:
            List of high-resolution image URLs
        """
        try:
            logger.info(f"Searching DuckDuckGo for high-res images: {query}")
            
            # Use the duckduckgo-search library to search for images with size parameters
            # Look for large images by default
            results = self.ddgs.images(
                keywords=query,
                max_results=max_results * 2,  # Request more results to have enough after filtering
                size="large"  # Request large images
            )
            
            # Process and filter results
            image_urls = []
            detailed_results = []
            
            for result in results:
                image_url = result.get("image")
                if not image_url:
                    continue
                    
                # Get image dimensions from result if available
                width = result.get("width")
                height = result.get("height")
                
                # If dimensions are available, check against minimum requirements
                if width and height:
                    width = int(width)
                    height = int(height)
                    if width >= self.min_width and height >= self.min_height:
                        detailed_results.append({
                            "url": image_url,
                            "width": width,
                            "height": height,
                            "size": width * height  # Calculate total pixels for sorting
                        })
                else:
                    # If dimensions aren't in the metadata, check the image
                    dimensions = self.check_image_resolution(image_url)
                    if dimensions:
                        width, height = dimensions
                        if width >= self.min_width and height >= self.min_height:
                            detailed_results.append({
                                "url": image_url,
                                "width": width,
                                "height": height,
                                "size": width * height
                            })
                    else:
                        # If we can't check dimensions, include it anyway
                        detailed_results.append({
                            "url": image_url,
                            "width": 0,
                            "height": 0,
                            "size": 0
                        })
            
            # Sort by image size (largest first)
            sorted_results = sorted(detailed_results, key=lambda x: x["size"], reverse=True)
            
            # Extract URLs from sorted results
            image_urls = [result["url"] for result in sorted_results[:max_results]]
            
            logger.info(f"Found {len(image_urls)} high-resolution images for query: {query}")
            logger.debug(f"Image dimensions: {[(r['width'], r['height']) for r in sorted_results[:max_results] if r['width'] > 0]}")
            return image_urls
            
        except Exception as e:
            logger.error(f"Error searching DuckDuckGo: {str(e)}")
            return []

    def check_image_resolution(self, url, timeout=2):
        """
        Check the resolution of an image at the given URL
        
        Args:
            url: URL of the image to check
            timeout: Request timeout in seconds
            
        Returns:
            Tuple of (width, height) or None if checking fails
        """
        try:
            response = self.session.get(url, stream=True, timeout=timeout)
            if response.status_code == 200:
                # Read only part of the image to efficiently get dimensions
                img_data = BytesIO(response.content)
                img = Image.open(img_data)
                return img.size  # Returns (width, height)
        except Exception as e:
            logger.debug(f"Failed to check image resolution for {url}: {str(e)}")
        return None

    def is_url_accessible(self, url, timeout=5):
        """Check if a URL is accessible by sending a HEAD request"""
        try:
            response = self.session.head(url, timeout=timeout, allow_redirects=True)
            return response.status_code < 400
        except Exception as e:
            logger.warning(f"URL check failed for {url}: {str(e)}")
            return False

    def get_alternative_image(self, keywords):
        """Get a high-resolution alternative image URL based on keywords"""
        if not keywords:
            keywords = "generic image high resolution"
        else:
            keywords = f"{keywords} high resolution"
        
        image_urls = self.search_duckduckgo(keywords)
        
        # Return a random image from results or None if none found
        if image_urls:
            return random.choice(image_urls)
        return None
