"""
MangaThaiAI-Studio: Web Manga Crawler & Proxy
Fetches manga webpage chapters, extracts image URLs, and streams images for real-time translation.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger("WebMangaCrawler")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ja,en-US,en;q=0.9,th;q=0.8",
}


class WebMangaCrawler:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def extract_manga_images_from_url(self, page_url: str) -> Dict[str, Any]:
        """
        Extracts all manga page image URLs from a given webpage URL.
        Handles direct image links as well as HTML manga chapter pages.
        """
        # If the URL directly points to an image
        parsed = urlparse(page_url)
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]):
            return {
                "source_url": page_url,
                "title": Path(parsed.path).stem or "Manga Page",
                "images": [page_url],
                "count": 1,
            }

        try:
            async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(page_url)
                resp.raise_for_status()
                html = resp.text

            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else "Online Manga Reader"

            found_images = []
            seen_urls = set()

            for img in soup.find_all("img"):
                # Handle standard src or lazy-load attributes (data-src, data-lazy-src, data-original, srcset)
                src = (
                    img.get("data-src")
                    or img.get("data-lazy-src")
                    or img.get("data-original")
                    or img.get("src")
                )
                if not src:
                    continue

                abs_url = urljoin(page_url, src.strip())
                if abs_url in seen_urls:
                    continue

                # Filter out obvious small icons, avatars, tracking pixels, ads
                url_lower = abs_url.lower()
                if any(x in url_lower for x in ["avatar", "icon", "logo", "banner", "ad_", "pixel", "tracker", "facebook", "twitter"]):
                    continue

                seen_urls.add(abs_url)
                found_images.append(abs_url)

            return {
                "source_url": page_url,
                "title": title,
                "images": found_images,
                "count": len(found_images),
            }
        except Exception as e:
            logger.error(f"Failed to crawl {page_url}: {e}")
            return {
                "source_url": page_url,
                "title": "Error Fetching Webpage",
                "images": [],
                "count": 0,
                "error": str(e),
            }

    async def fetch_image_bytes(self, image_url: str, referer: Optional[str] = None) -> bytes:
        """Downloads image bytes from URL with proper Referer headers to bypass hotlinking protection."""
        headers = dict(DEFAULT_HEADERS)
        if referer:
            headers["Referer"] = referer
        else:
            parsed = urlparse(image_url)
            headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"

        async with httpx.AsyncClient(headers=headers, timeout=self.timeout, follow_redirects=True) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            return resp.content
