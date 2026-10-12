"""
Tests WebMangaCrawler for various real-world webpage structures.
"""

import asyncio
import sys
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from control_center.web_reader.crawler import WebMangaCrawler


async def run():
    crawler = WebMangaCrawler()

    # Case 1: Direct image
    print("Testing Case 1: Direct Image URL...")
    res1 = await crawler.extract_manga_images_from_url("http://localhost:8000/static/sample_manga.png")
    print("  Case 1 Result Count:", res1.get("count"))
    assert res1.get("count") == 1
    assert res1.get("images")[0] == "http://localhost:8000/static/sample_manga.png"

    # Case 2: Local Webpage with HTML
    print("Testing Case 2: Webpage URL...")
    res2 = await crawler.extract_manga_images_from_url("http://localhost:8000/")
    print("  Case 2 Status:", "Images found:", res2.get("count"))

    # Case 3: Invalid URL
    print("Testing Case 3: Invalid URL...")
    res3 = await crawler.extract_manga_images_from_url("http://this-url-definitely-does-not-exist.local.test/")
    print("  Case 3 Handled gracefully:", "error" in res3)
    assert "error" in res3

    # Case 4: Fetch image bytes
    print("Testing Case 4: Fetching Image Bytes...")
    b = await crawler.fetch_image_bytes("http://localhost:8000/static/sample_manga.png")
    print("  Case 4 Image bytes length:", len(b))
    assert len(b) > 1000

    print("ALL CRAWLER TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(run())
