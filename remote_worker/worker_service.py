"""
MangaThaiAI-Studio: Remote Worker Service (FastAPI)
Intended to run on Gaming PC to leverage NVIDIA CUDA GPU for:
1. Manga Text Detection & OCR (Manga-OCR / CRAFT)
2. Speech Bubble Inpainting / Text Removal (LaMa)
3. Japanese to Thai Manga Translation (LLM)
"""

import base64
import io
import logging
import os
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import pydantic
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RemoteWorker")

app = FastAPI(title="MangaThaiAI-Studio Remote Worker API", version="1.0.0")


class DetectedBubble(pydantic.BaseModel):
    id: int
    bbox: List[int] # [ymin, xmin, ymax, xmax]
    japanese_text: str
    thai_translation: str
    confidence: float


class ProcessPageResponse(pydantic.BaseModel):
    filename: str
    processing_time_sec: float
    detected_bubbles: List[DetectedBubble]
    cleaned_image_base64: Optional[str] = None


@app.get("/api/health")
async def health_check():
    """Provides hardware and worker status for Control Center monitoring."""
    gpu_info = "CPU Only"
    vram_free = "N/A"
    cuda_available = False

    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_info = torch.cuda.get_device_name(0)
            free_mem = torch.cuda.mem_get_info()[0] / (1024**3)
            total_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            vram_free = f"{free_mem:.2f} GB / {total_mem:.2f} GB"
    except ImportError:
        pass

    return {
        "status": "healthy",
        "service": "MangaThaiAI-Studio Remote Worker",
        "cuda_available": cuda_available,
        "gpu": gpu_info,
        "vram_status": vram_free,
        "timestamp": time.time(),
    }


@app.post("/api/v1/process-page", response_model=ProcessPageResponse)
async def process_page(file: UploadFile = File(...)):
    """Processes an uploaded manga image page through OCR, Inpainting, and Translation."""
    start_time = time.time()
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    width, height = image.size

    logger.info(f"Received manga page {file.filename} ({width}x{height})")

    # Mock/Pipeline processing placeholder
    # Full neural models (Manga-OCR, LaMa, Qwen-2.5) will be plugged in Phase 3
    bubbles = [
        DetectedBubble(
            id=1,
            bbox=[int(height * 0.1), int(width * 0.6), int(height * 0.3), int(width * 0.9)],
            japanese_text="おい、待てよ！",
            thai_translation="เฮ้ย รอก่อนสิ!",
            confidence=0.96,
        )
    ]

    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    cleaned_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    elapsed = round(time.time() - start_time, 2)
    return ProcessPageResponse(
        filename=file.filename,
        processing_time_sec=elapsed,
        detected_bubbles=bubbles,
        cleaned_image_base64=cleaned_base64,
    )


if __name__ == "__main__":
    import uvicorn
    # Default listen on all interfaces on port 8888 so laptop can reach it over LAN
    uvicorn.run("worker_service:app", host="0.0.0.0", port=8888, reload=True)
