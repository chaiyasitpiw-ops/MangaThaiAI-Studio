"""
MangaThaiAI-Studio: Advanced Multi-Site Web Manga Crawler
Supports:
  - Standard HTML img tags (src, data-src, data-lazy-src, srcset)
  - JSON/JavaScript embedded image arrays (MangaPlus, ComicK, etc.)
  - <noscript> fallback images
  - MangaDex public REST API (api.mangadex.org)
  - Direct image URL passthrough
  - Automatic Cloudflare bypass headers
  - Gambling ad + watermark blocking
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
import logging

try:
    from curl_cffi.requests import AsyncSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

logger = logging.getLogger("WebMangaCrawler")

# Rotate between browser user-agents for better site compatibility
USER_AGENTS = [
    # Desktop Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Mobile Safari (iPhone) - passes some Cloudflare checks
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENTS[0],
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,ja-JP,ja;q=0.8,en-US,en;q=0.7,th-TH,th;q=0.6",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

# Blocked keywords for ad/watermark/gambling images
BLOCKED_KEYWORDS = [
    "avatar", "icon", "logo", "banner", "/ad_", "/ads/", "advert",
    "pixel", "tracker", "facebook", "twitter", "/covers/",
    "casino", "slot", "bet", "gamble", "ufabet", "pgslot", "bk8",
    "1xbet", "sponsor", "promo", "affiliate", "popup", "donate",
    "patreon", "discord", "watermark", "credit_page", "thumbnail",
    "favicon", ".svg", "placeholder", "loading", "emoji",
]

# Image extensions to look for
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif"}

# MangaDex API base
MANGADEX_API = "https://api.mangadex.org"
MANGADEX_IMAGE_BASE = "https://uploads.mangadex.org/data"


class WebMangaCrawler:
    def __init__(self, timeout: float = 18.0):
        self.timeout = timeout

    def _is_valid_manga_image(self, url: str, min_size_hint: bool = True) -> bool:
        """Returns True if URL looks like a manga page image (not an ad or icon)."""
        url_lower = url.lower()
        # Must end with image extension
        parsed = urlparse(url)
        path = parsed.path.lower()
        if not any(path.endswith(ext) for ext in IMAGE_EXTS):
            # Allow CDN URLs with no extension but query params (e.g. ...?format=webp)
            has_image_param = any(k in url_lower for k in ["format=webp", "format=jpg", ".webp?", ".jpg?", ".png?"])
            if not has_image_param:
                return False
        # Block ad/gambling/icon content
        if any(x in url_lower for x in BLOCKED_KEYWORDS):
            return False
        return True

    def _extract_images_from_json_script(self, html: str, page_url: str) -> List[str]:
        """
        Extracts image URLs embedded in JavaScript/JSON variables on the page.
        Many modern readers (Asura, Luminous, Reaper, Flame) embed chapter images as JSON.
        """
        images = []
        # Pattern 1: Look for arrays of image URLs in script tags
        url_pattern = re.compile(
            r'https?://[^\s\'"<>]+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^\s\'"<>]*)?',
            re.IGNORECASE
        )
        all_script_urls = url_pattern.findall(html)
        for url in all_script_urls:
            if self._is_valid_manga_image(url):
                images.append(url)

        # Pattern 2: JSON arrays with "url", "src", "image", "path" keys
        json_patterns = [
            r'"(?:url|src|image|path|img|source)"\s*:\s*"(https?://[^"]+\.(?:jpg|jpeg|png|webp)(?:\?[^"]*)?)"',
            r"'(?:url|src|image|path|img|source)'\s*:\s*'(https?://[^']+\.(?:jpg|jpeg|png|webp)(?:\?[^']*)?)'",
        ]
        for pat in json_patterns:
            for m in re.finditer(pat, html, re.IGNORECASE):
                url = m.group(1)
                if self._is_valid_manga_image(url):
                    images.append(url)

        # Pattern 3: Next.js/React data - window.__NEXT_DATA__ or similar
        nextdata_match = re.search(r'__NEXT_DATA__\s*=\s*({.+?})\s*</script>', html, re.DOTALL)
        if nextdata_match:
            try:
                data = json.loads(nextdata_match.group(1))
                raw = json.dumps(data)
                for m in url_pattern.finditer(raw):
                    url = m.group(0)
                    if self._is_valid_manga_image(url):
                        images.append(url)
            except Exception:
                pass

        return list(dict.fromkeys(images))  # Deduplicate preserving order

    async def _handle_mangadex(self, page_url: str) -> List[str]:
        """
        Uses the official MangaDex API to get chapter images.
        URL format: https://mangadex.org/chapter/{chapter_id}/{page}
        """
        # Extract chapter UUID from URL
        m = re.search(r'mangadex\.org/chapter/([a-f0-9-]{36})', page_url)
        if not m:
            return []
        chapter_id = m.group(1)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{MANGADEX_API}/at-home/server/{chapter_id}")
                if r.status_code != 200:
                    return []
                data = r.json()
                base_url = data.get("baseUrl", MANGADEX_IMAGE_BASE)
                chapter = data.get("chapter", {})
                hash_ = chapter.get("hash", "")
                pages = chapter.get("data", [])
                return [f"{base_url}/data/{hash_}/{page}" for page in pages]
        except Exception as e:
            logger.warning(f"MangaDex API failed: {e}")
            return []

    async def extract_manga_images_from_url(self, page_url: str) -> Dict[str, Any]:
        """
        Extracts all manga page image URLs from a given webpage URL.
        Handles: direct image links, HTML manga chapter pages, MangaDex API, JSON-embedded images.
        """
        raw_input = (page_url or "").strip()
        # Detect if user pasted multiple URLs or raw text containing image links
        urls_in_input = re.findall(r'https?://[^\s\'"<>]+\.(?:jpg|jpeg|png|webp|avif|gif)(?:\?[^\s\'"<>]*)?', raw_input, re.IGNORECASE)
        if len(urls_in_input) > 1:
            valid_urls = [u for u in urls_in_input if self._is_valid_manga_image(u)]
            if valid_urls:
                return {
                    "source_url": valid_urls[0],
                    "title": f"Manga Images ({len(valid_urls)} หน้า)",
                    "images": valid_urls,
                    "count": len(valid_urls)
                }

        # Normalize and clean single URL
        page_url = re.sub(r"[\s\u200b\u200e\u200f\ufeff]+", "", raw_input)
        if not page_url:
            return {"source_url": "", "title": "Empty URL", "images": [], "count": 0, "error": "URL ว่างเปล่า กรุณากรอก URL"}
        if not page_url.startswith(("http://", "https://")):
            page_url = "https://" + page_url

        # Direct image URL passthrough
        parsed = urlparse(page_url)
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in IMAGE_EXTS):
            return {"source_url": page_url, "title": Path(parsed.path).stem, "images": [page_url], "count": 1}

        # MangaDex special handling (API-based)
        if "mangadex.org" in page_url:
            images = await self._handle_mangadex(page_url)
            if images:
                return {"source_url": page_url, "title": "MangaDex Chapter", "images": images, "count": len(images)}

        # General HTML scraping with multiple fallback strategies
        html = ""
        title = "Online Manga Reader"
        last_error = ""

        # Strategy 1: curl_cffi with browser TLS impersonation (Bypasses Cloudflare & Bot protection)
        if HAS_CURL_CFFI:
            for impersonate_target in ["chrome124", "safari17_2", "chrome120"]:
                try:
                    headers = dict(DEFAULT_HEADERS)
                    async with AsyncSession(impersonate=impersonate_target, timeout=int(self.timeout)) as session:
                        resp = await session.get(page_url, headers=headers)
                        if resp.status_code == 200 and resp.text:
                            html = resp.text
                            break
                        elif resp.status_code in (403, 503):
                            last_error = f"Bot protection ({resp.status_code})"
                            logger.warning(f"curl_cffi ({impersonate_target}) got {resp.status_code} for {page_url}")
                        else:
                            last_error = f"HTTP {resp.status_code}"
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"curl_cffi ({impersonate_target}) attempt failed: {e}")

        # Strategy 2: Standard httpx fallback
        if not html:
            for ua_index, ua in enumerate(USER_AGENTS):
                headers = dict(DEFAULT_HEADERS)
                headers["User-Agent"] = ua
                try:
                    async with httpx.AsyncClient(
                        headers=headers, timeout=self.timeout,
                        follow_redirects=True, verify=False
                    ) as client:
                        resp = await client.get(page_url)
                        if resp.status_code == 200:
                            html = resp.text
                            break
                        elif resp.status_code in (403, 503):
                            last_error = f"Bot protection ({resp.status_code})"
                            logger.warning(f"Bot protection on attempt {ua_index+1} ({resp.status_code}) for {page_url}")
                            continue
                        else:
                            last_error = f"HTTP {resp.status_code}"
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Fetch attempt {ua_index+1} failed: {e}")
                    continue

        if not html:
            return {
                "source_url": page_url,
                "title": "Could Not Fetch",
                "images": [],
                "count": 0,
                "error": f"ไม่สามารถเข้าถึงหน้าเว็บได้ ({last_error}) กรุณาตรวจสอบว่า URL ถูกต้อง หรือเปิดดูหน้าเว็บต้นฉบับ หรือใช้งาน Local Server",
            }

        return self.extract_manga_images_from_html(html, page_url)

    def extract_manga_images_from_html(self, html: str, page_url: str = "") -> Dict[str, Any]:
        """Extracts all manga page image URLs from raw HTML source string."""
        soup = BeautifulSoup(html, "html.parser")
        title = "Online Manga Reader"
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        found_images = []
        seen_urls = set()

        def add_image(url: str):
            url = url.strip()
            if not url or url in seen_urls:
                return
            abs_url = urljoin(page_url, url) if page_url else url
            if abs_url in seen_urls:
                return
            if not self._is_valid_manga_image(abs_url):
                return
            seen_urls.add(abs_url)
            found_images.append(abs_url)

        # Strategy 1: Standard <img> tags (src, data-src, data-lazy-src, data-original, data-cfsrc, data-url)
        for img in soup.find_all("img"):
            for attr in ["data-src", "data-lazy-src", "data-original", "data-cfsrc", "data-url", "data-full-url", "data-reader-image", "src"]:
                val = img.get(attr)
                if val:
                    add_image(val)
                    break

        # Strategy 2: <noscript> fallback images (bypass lazy-loading detection)
        for ns in soup.find_all("noscript"):
            ns_imgs = BeautifulSoup(str(ns), "html.parser").find_all("img")
            for img in ns_imgs:
                src = img.get("src") or img.get("data-src")
                if src:
                    add_image(src)

        # Strategy 3: JSON/JavaScript-embedded image arrays (most modern readers)
        if len(found_images) < 3:
            json_images = self._extract_images_from_json_script(html, page_url)
            for url in json_images:
                add_image(url)

        # Strategy 4: srcset attribute (responsive images)
        for img in soup.find_all("img", srcset=True):
            srcset = img.get("srcset", "")
            for part in srcset.split(","):
                url = part.strip().split(" ")[0]
                if url:
                    add_image(url)

        # Strategy 5: Background-image in style attributes (some readers use CSS bg images)
        for el in soup.find_all(style=True):
            style = el.get("style", "")
            m = re.search(r'url\(["\']?(https?://[^"\')\s]+)["\']?\)', style)
            if m:
                add_image(m.group(1))

        # Prioritize chapter/page images over thumbnails
        chapter_images = [u for u in found_images if any(
            kw in u.lower() for kw in ["chapter", "/manga/", "/webtoon/", "/comic/", "cdn", "storage", "quicksharefiles"]
        )]
        if len(chapter_images) >= 3:
            found_images = chapter_images

        # Heuristic: Real manga pages are usually > 500px tall; filter very small images
        large_images = [u for u in found_images if not any(
            x in u.lower() for x in ["thumb", "mini", "small", "50x", "100x", "150x", "200x"]
        )]
        if len(large_images) >= 2:
            found_images = large_images

        return {
            "source_url": page_url,
            "title": title,
            "images": found_images,
            "count": len(found_images),
        }
        if len(large_images) >= 2:
            found_images = large_images

        return {
            "source_url": page_url,
            "title": title,
            "images": found_images,
            "count": len(found_images),
        }

    async def fetch_image_bytes(self, image_url: str, referer: Optional[str] = None) -> bytes:
        """Downloads image bytes from URL with proper Referer headers and TLS impersonation to bypass hotlinking protection."""
        headers = dict(DEFAULT_HEADERS)
        parsed = urlparse(image_url)
        if not referer:
            if "quicksharefiles" in parsed.netloc or "newxtoon" in image_url:
                referer = "https://newxtoon5.com/"
            elif "asura" in parsed.netloc:
                referer = "https://asurascans.com/"
            else:
                referer = f"{parsed.scheme}://{parsed.netloc}/"
        headers["Referer"] = referer
        headers["Accept"] = "image/webp,image/apng,image/*,*/*;q=0.8"

        # Try curl_cffi first for browser TLS impersonation
        if HAS_CURL_CFFI:
            try:
                async with AsyncSession(impersonate="chrome124", timeout=int(self.timeout)) as session:
                    resp = await session.get(image_url, headers=headers)
                    if resp.status_code == 200 and resp.content:
                        return resp.content
            except Exception as e:
                logger.warning(f"curl_cffi fetch_image_bytes failed: {e}, falling back to httpx")

        # Fallback to standard httpx
        for k in ["Sec-Fetch-Dest", "Sec-Fetch-Mode", "Upgrade-Insecure-Requests"]:
            headers.pop(k, None)
        headers["Sec-Fetch-Dest"] = "image"
        headers["Sec-Fetch-Mode"] = "no-cors"

        async with httpx.AsyncClient(
            headers=headers, timeout=self.timeout,
            follow_redirects=True, verify=False
        ) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            return resp.content
