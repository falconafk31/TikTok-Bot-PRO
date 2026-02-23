import requests
import re
import os
import uuid
from logger_config import logger

class TikTokShopScraper:
    def __init__(self, temp_dir="temp"):
        self.temp_dir = temp_dir
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        }

    def extract_urls(self, text):
        """Extracts TikTok Shop urls and direct image urls from text."""
        # Pattern for tiktok shop links
        tiktok_pattern = r'https?://(?:[a-zA-Z0-9.-]+\.)?tiktok\.com/\S+'
        # Pattern for direct image links
        image_pattern = r'https?://\S+\.(?:jpg|jpeg|png|webp|avif)(?:\?\S+)?'
        
        urls = re.findall(tiktok_pattern, text) + re.findall(image_pattern, text)
        return list(dict.fromkeys(urls)) # De-duplicate while preserving order

    def scrape_product(self, url):
        """
        Scrapes a TikTok Shop product URL for images OR handles direct image URLs.
        """
        # 1. Check if the URL is already a direct image
        is_direct_image = any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.avif'])
        if is_direct_image:
            logger.info(f"Direct image URL detected: {url}")
            return {
                "success": True,
                "product_name": "Image Link",
                "image_urls": [url],
                "is_direct": True
            }

        logger.info(f"Attempting to scrape TikTok Shop URL: {url}")
        
        try:
            # Handle redirects (especially for short URLs like vt.tiktok.com)
            response = requests.get(url, headers=self.headers, allow_redirects=True, timeout=15)
            final_url = response.url
            html_content = response.text
            
            logger.info(f"Resolved URL: {final_url} (Status: {response.status_code})")

            # Check for CAPTCHA or blocking
            if response.status_code == 403 or "captcha" in html_content.lower() or "verify" in html_content.lower() and "challenge" in html_content.lower():
                logger.warning(f"TikTok Shop scraping blocked by CAPTCHA/Security: {final_url}")
                return {
                    "success": False, 
                    "error": "Tiktok memblokir akses otomatis (CAPTCHA). Silakan coba lagi nanti atau upload foto manual.",
                    "is_captcha": True
                }

            # If the resolved URL is an image (some redirect to images)
            if any(ext in final_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.avif']):
                 return {
                    "success": True,
                    "product_name": "Image Link",
                    "image_urls": [final_url],
                    "is_direct": True
                }

            # 1. Try to find the title/product name
            # Pattern for TikTok Shop product name in metadata/JSON
            title_match = re.search(r'"title":"(.*?)"', html_content)
            product_name = title_match.group(1) if title_match else "Produk TikTok Shop"
            
            # 2. Try to find image URLs
            image_urls = []
            
            # Common pattern for gallery images 
            found_images = re.findall(r'https://[a-zA-Z0-9.-]+\.(?:byteimg|tiktokcdn)\.com/[a-zA-Z0-9/_.-]+~plv-photomode-video:1080:1080\.jpeg', html_content)
            
            if not found_images:
                found_images = re.findall(r'https://[a-zA-Z0-9.-]+\.(?:byteimg|tiktokcdn)\.com/[a-zA-Z0-9/_.-]+\.(?:webp|jpg|jpeg)', html_content)

            # De-duplicate and filter
            seen = set()
            for img_url in found_images:
                clean_url = img_url.replace('\\u002F', '/')
                if clean_url not in seen and ('obj' in clean_url or 'photomode' in clean_url):
                    image_urls.append(clean_url)
                    seen.add(clean_url)
            
            if not image_urls:
                image_urls = list(set(found_images))[:5]
            
            logger.info(f"Found {len(image_urls)} potential images for product: {product_name}")
            
            return {
                "success": True,
                "product_name": product_name,
                "image_urls": image_urls[:6]
            }

        except Exception as e:
            logger.error(f"Scraping Error: {e}")
            return {"success": False, "error": str(e), "is_captcha": False}

    def download_images(self, urls, chat_id):
        """Downloads images to the temporary directory."""
        downloaded_paths = []
        for i, url in enumerate(urls):
            try:
                # Add headers to avoid 403
                resp = requests.get(url, headers=self.headers, timeout=10)
                if resp.status_code == 200:
                    ext = ".jpg" # Default to jpg
                    if ".webp" in url: ext = ".webp"
                    
                    filename = f"scrape_{chat_id}_{i}_{uuid.uuid4().hex[:6]}{ext}"
                    path = os.path.join(self.temp_dir, filename)
                    
                    with open(path, "wb") as f:
                        f.write(resp.content)
                    downloaded_paths.append(path)
                    logger.info(f"Downloaded: {filename}")
            except Exception as e:
                logger.error(f"Download failed for {url}: {e}")
        
        return downloaded_paths
