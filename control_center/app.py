"""
MangaThaiAI-Studio: Interactive Control Center Web Studio & Real-Time Web Reader
Features:
- Live Progress HUD with Stopwatch, Page-by-Page Progress & Dynamic ETA
- High-Speed Sliced OCR & Batch Translation Engine
- Authentic Manga Typography & Adaptive Backdrops (Mali Comic, Kanit Shonen, Chakra Petch Gaming)
- High-Performance Disk & Memory Caching for Instant Page Reloads
- Glassmorphism Webtoon Reader with Fullscreen Mode & Floating Controls
- 3-Worker Parallel Background Streaming
"""

import base64
import hashlib
import io
import json
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2
from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image

from control_center.orchestrator import MangaOrchestrator
from control_center.pipeline.pipeline import ZeroTrainingMangaPipeline
from control_center.pipeline.translator import manga_translator, MangaTone
from control_center.web_reader.crawler import WebMangaCrawler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ControlCenterApp")

app = FastAPI(title="MangaThaiAI-Studio Control Center", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parent.parent))
INPUT_DIR = BASE_DIR / "data/inputs"
OUTPUT_DIR = BASE_DIR / "data/outputs"
CACHE_DIR = OUTPUT_DIR / "cache"
STATIC_DIR = BASE_DIR / "control_center/static"

INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

pipeline = ZeroTrainingMangaPipeline()
orchestrator = MangaOrchestrator()
crawler = WebMangaCrawler()

# Pre-warm Korean OCR engine to eliminate cold-start delay
try:
    pipeline.get_ocr_engine("kr")
    logger.info("Korean OCR engine pre-warmed successfully.")
except Exception as e:
    logger.warning(f"Could not pre-warm Korean OCR engine: {e}")


def pil_to_base64(img: Image.Image, format: str = "JPEG", quality: int = 85) -> str:
    buffered = io.BytesIO()
    if format.upper() == "JPEG":
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(buffered, format="JPEG", quality=quality, optimize=True)
    else:
        img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def bgr_to_base64(img_bgr, format: str = "JPEG", quality: int = 85) -> str:
    if img_bgr is None:
        return ""
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    b64 = pil_to_base64(pil_img, format=format, quality=quality)
    del rgb
    del pil_img
    return b64


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html_file = Path(__file__).resolve().parent / "static" / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>MangaThai AI Online</h1>")


class FetchWebpageRequest(BaseModel):
    url: str


class ExtractHtmlRequest(BaseModel):
    html: str
    url: Optional[str] = "https://newxtoon5.com/"


@app.post("/api/fetch-webpage-manga")
async def fetch_webpage_manga(req: FetchWebpageRequest):
    return await crawler.extract_manga_images_from_url(req.url)


@app.post("/api/extract-manga-from-html")
async def extract_manga_from_html_endpoint(req: ExtractHtmlRequest):
    return crawler.extract_manga_images_from_html(req.html, req.url)


@app.get("/manifest.json")
async def pwa_manifest():
    """PWA Web App Manifest for iPhone/iPad Add to Home Screen."""
    manifest_path = STATIC_DIR / "manifest.json"
    if manifest_path.exists():
        return FileResponse(str(manifest_path), media_type="application/manifest+json")
    return JSONResponse({"name": "MangaThaiAI Studio", "short_name": "มังงะไทย",
                         "start_url": "/", "display": "standalone", "theme_color": "#6366f1"})


@app.get("/health")
async def health_check():
    """Health check endpoint for uptime monitoring."""
    return {"status": "online", "version": "2.0.0", "service": "MangaThaiAI-Studio"}


class TranslateImageUrlRequest(BaseModel):
    image_url: str
    referer: Optional[str] = None
    tone: str = "adult_18"
    source_lang: str = "auto"
    font_family: str = "mali"
    backdrop_mode: str = "natural"


@app.post("/api/translate-image-url")
async def translate_image_url(req: TranslateImageUrlRequest):
    t0 = time.time()
    try:
        # Check high-performance disk cache
        cache_key = hashlib.md5(
            f"{req.image_url}_{req.tone}_{req.source_lang}_{req.font_family}_{req.backdrop_mode}".encode("utf-8")
        ).hexdigest()
        cache_file = CACHE_DIR / f"{cache_key}.json"

        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    cached_data["cached"] = True
                    cached_data["elapsed_seconds"] = 0.05
                    return cached_data
            except Exception:
                pass

        if req.image_url.startswith("data:image"):
            header, b64data = req.image_url.split(",", 1)
            image_bytes = base64.b64decode(b64data)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = Path(tmp.name)
            try:
                res = pipeline.process_page(
                    tmp_path,
                    tone=req.tone,
                    source_lang=req.source_lang,
                    font_family=req.font_family,
                    backdrop_mode=req.backdrop_mode,
                )
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
        elif "sample_manga.png" in req.image_url:
            local_path = INPUT_DIR / "sample_manga.png"
            if not local_path.exists():
                from scripts.create_sample_manga import generate_sample_manga
                local_path = generate_sample_manga(str(local_path))
            res = pipeline.process_page(
                local_path,
                tone=req.tone,
                source_lang=req.source_lang,
                font_family=req.font_family,
                backdrop_mode=req.backdrop_mode,
            )
        else:
            image_bytes = await crawler.fetch_image_bytes(req.image_url, referer=req.referer)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = Path(tmp.name)

            try:
                res = pipeline.process_page(
                    tmp_path,
                    tone=req.tone,
                    source_lang=req.source_lang,
                    font_family=req.font_family,
                    backdrop_mode=req.backdrop_mode,
                )
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

        elapsed = round(time.time() - t0, 2)
        has_text = res.get("has_text", True) and len(res.get("bubbles", [])) > 0
        if has_text and res.get("result_pil"):
            result_b64 = pil_to_base64(res["result_pil"], format="JPEG", quality=85)
        else:
            result_b64 = ""

        response_data = {
            "status": "success",
            "cached": False,
            "elapsed_seconds": elapsed,
            "has_text": has_text,
            "bubbles_count": len(res.get("bubbles", [])),
            "bubbles": res.get("bubbles", []),
            "cleaned_b64": "",  # Skipped to save 50% RAM & JSON network size
            "result_b64": result_b64,
        }

        # Save to disk cache for instantaneous reloads
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(response_data, f, default=str)
        except Exception as e:
            logger.warning(f"Could not cache result: {e}")

        # Explicit cleanup to prevent memory accumulation on low-RAM cloud instances
        del res
        import gc
        gc.collect()

        return response_data

    except Exception as e:
        logger.error(f"Error translating image {req.image_url}: {e}")
        return {"status": "error", "error": str(e), "elapsed_seconds": round(time.time() - t0, 2)}


@app.get("/api/demo-sample")
async def demo_sample(tone: str = "shonen", font_family: str = "mali", backdrop_mode: str = "natural"):
    sample_path = INPUT_DIR / "sample_manga.png"
    if not sample_path.exists():
        from scripts.create_sample_manga import generate_sample_manga
        sample_path = generate_sample_manga(str(sample_path))

    res = pipeline.process_page(
        sample_path,
        tone=tone,
        font_family=font_family,
        backdrop_mode=backdrop_mode,
    )
    return {
        "status": "success",
        "saved_path": str(sample_path),
        "bubbles": res["bubbles"],
        "original_b64": bgr_to_base64(res["original_bgr"]),
        "cleaned_b64": bgr_to_base64(res["cleaned_bgr"]),
        "result_b64": pil_to_base64(res["result_pil"]),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("control_center.app:app", host="0.0.0.0", port=8000, reload=True)
