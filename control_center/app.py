"""
MangaThaiAI-Studio: Interactive Control Center Web Studio
Features:
- Live Zero-Training Manga Translation Demo
- Side-by-Side Visual Comparison (Original vs Cleaned vs Thai Translated)
- Interactive Speech Bubble & Dialogue Editor
- Hardware & Network Monitoring Dashboard
"""

import base64
import io
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image

from control_center.orchestrator import MangaOrchestrator
from control_center.pipeline.pipeline import ZeroTrainingMangaPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ControlCenterApp")

app = FastAPI(title="MangaThaiAI-Studio Control Center", version="1.0.0")

BASE_DIR = Path("D:/code/MangaThaiAI-Studio")
INPUT_DIR = BASE_DIR / "data/inputs"
OUTPUT_DIR = BASE_DIR / "data/outputs"
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Mount outputs for direct download
app.mount("/static/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")

pipeline = ZeroTrainingMangaPipeline()
orchestrator = MangaOrchestrator()


def pil_to_base64(img: Image.Image) -> str:
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def bgr_to_base64(img_bgr) -> str:
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    return pil_to_base64(pil_img)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MangaThaiAI-Studio | Interactive Control Center</title>
        <style>
            :root {
                --primary: #6366f1;
                --primary-hover: #4f46e5;
                --success: #10b981;
                --bg: #090d16;
                --card: #131c2e;
                --card-border: #1e293b;
                --text: #f8fafc;
                --text-muted: #94a3b8;
            }
            * { box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, -apple-system, sans-serif;
                background-color: var(--bg);
                color: var(--text);
                margin: 0;
                padding: 24px;
            }
            .container { max-width: 1300px; margin: 0 auto; }
            header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid var(--card-border);
                padding-bottom: 16px;
                margin-bottom: 24px;
            }
            .grid-stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 16px;
                margin-bottom: 24px;
            }
            .card {
                background: var(--card);
                border: 1px solid var(--card-border);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
            }
            .badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 999px;
                font-size: 12px;
                font-weight: 600;
            }
            .badge-online { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #059669; }
            .badge-offline { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #dc2626; }
            .btn {
                background: var(--primary);
                color: white;
                border: none;
                padding: 10px 18px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 600;
                transition: all 0.2s;
            }
            .btn:hover { background: var(--primary-hover); transform: translateY(-1px); }
            .btn-success { background: var(--success); }
            .btn-success:hover { background: #059669; }
            .btn-outline { background: transparent; border: 1px solid var(--card-border); color: var(--text); }
            .btn-outline:hover { background: #1e293b; }

            .viewer-grid {
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 16px;
                margin-top: 16px;
            }
            @media (max-width: 900px) {
                .viewer-grid { grid-template-columns: 1fr; }
            }
            .view-box {
                background: #0b1120;
                border: 1px solid var(--card-border);
                border-radius: 8px;
                padding: 12px;
                text-align: center;
            }
            .view-box h4 { margin: 0 0 10px; font-size: 14px; color: var(--text-muted); }
            .view-box img {
                max-width: 100%;
                height: auto;
                max-height: 520px;
                border-radius: 6px;
                border: 1px solid #334155;
                object-fit: contain;
                background: #000;
            }
            .table-editor {
                width: 100%;
                border-collapse: collapse;
                margin-top: 16px;
            }
            .table-editor th, .table-editor td {
                padding: 10px;
                border: 1px solid var(--card-border);
                text-align: left;
                font-size: 13px;
            }
            .table-editor th { background: #1e293b; }
            .table-editor input, .table-editor textarea {
                width: 100%;
                background: #090d16;
                color: #fff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                font-family: inherit;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div>
                    <h1 style="margin:0; font-size:26px;">🎨 MangaThaiAI-Studio</h1>
                    <p style="margin:4px 0 0; color:var(--text-muted); font-size:14px;">
                        ระบบแปลมังงะญี่ปุ่นเป็นไทยอัตโนมัติ | <b>Zero-Training Studio Pipeline</b>
                    </p>
                </div>
                <div>
                    <span class="badge badge-online">● Laptop Control Center (Online)</span>
                </div>
            </header>

            <!-- Status Cards -->
            <div class="grid-stats">
                <div class="card" style="margin-bottom:0;">
                    <h3 style="margin-top:0; font-size:16px;">💻 Laptop Status (Control Center)</h3>
                    <p style="font-size:13px; color:var(--text-muted); margin:4px 0;">IP: <code>192.168.1.104</code> | Port: <code>8000</code></p>
                    <p style="font-size:13px; color:var(--text-muted); margin:4px 0;">GPU: <code>NVIDIA GTX 1650 (4GB)</code></p>
                    <p style="font-size:13px; color:var(--text-muted); margin:4px 0;">Storage: <code>D:\code\MangaThaiAI-Studio</code> (121.7GB Free)</p>
                </div>

                <div class="card" style="margin-bottom:0;">
                    <h3 style="margin-top:0; font-size:16px;">🎮 Remote AI Worker (Gaming PC)</h3>
                    <p style="font-size:13px; color:var(--text-muted); margin:4px 0;">Target LAN IP: <code id="workerIp">192.168.1.50:8888</code></p>
                    <p style="font-size:13px; color:var(--text-muted); margin:4px 0;">Status: <span id="workerStatusBadge" class="badge badge-offline">Offline (Standby)</span></p>
                    <div style="margin-top:8px;">
                        <button class="btn btn-outline" style="padding:4px 10px; font-size:12px;" onclick="checkWorker()">↻ Ping Worker</button>
                    </div>
                </div>

                <div class="card" style="margin-bottom:0;">
                    <h3 style="margin-top:0; font-size:16px;">⚡ Zero-Training Pipeline Engine</h3>
                    <p style="font-size:13px; color:var(--text-muted); margin:4px 0;">Detector: <code>Computer Vision Contours</code></p>
                    <p style="font-size:13px; color:var(--text-muted); margin:4px 0;">Inpainter: <code>Mathematical Telea (0 VRAM)</code></p>
                    <p style="font-size:13px; color:var(--text-muted); margin:4px 0;">Typesetter: <code>PyThaiNLP + Smart Scaler</code></p>
                </div>
            </div>

            <!-- Action Controls -->
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                    <div>
                        <h2 style="margin:0; font-size:18px;">ทดลองรันระบบแปลมังงะ (Zero-Training Demo)</h2>
                        <p style="margin:4px 0 0; color:var(--text-muted); font-size:13px;">
                            ทดสอบการตรวจพิกัดบอลลูน ลบข้อความภาษาญี่ปุ่น และจัดพิมพ์ภาษาไทยลงในบอลลูนคำพูดทันที
                        </p>
                    </div>
                    <div style="display:flex; gap:10px;">
                        <button class="btn btn-success" onclick="runSampleDemo()">🚀 โหลดตัวอย่างมังงะ & รันทันที</button>
                        <label class="btn btn-outline" style="cursor:pointer; display:inline-block;">
                            📁 อัปโหลดหน้ามังงะของคุณเอง
                            <input type="file" id="customFileInput" accept="image/*" style="display:none;" onchange="uploadCustomManga(this)">
                        </label>
                    </div>
                </div>

                <!-- Live Results Viewer -->
                <div class="viewer-grid" id="viewerGrid" style="display:none;">
                    <div class="view-box">
                        <h4>1. หน้ามังงะต้นฉบับ (Original JP)</h4>
                        <img id="imgOriginal" src="" alt="Original">
                    </div>
                    <div class="view-box">
                        <h4>2. ผลลัพธ์ลบตัวหนังสือ (Cleaned Inpaint)</h4>
                        <img id="imgCleaned" src="" alt="Cleaned">
                    </div>
                    <div class="view-box">
                        <h4>3. ผลลัพธ์แปลไทย (Thai Typeset)</h4>
                        <img id="imgResult" src="" alt="Translated Thai">
                        <div style="margin-top:10px;">
                            <a id="downloadBtn" href="#" download="manga_thai_translated.png" class="btn" style="text-decoration:none; display:inline-block; font-size:13px; padding:6px 14px;">💾 ดาวน์โหลดรูปภาพแปลไทย</a>
                        </div>
                    </div>
                </div>

                <!-- Interactive Bubble Dialogue Editor -->
                <div id="editorSection" style="display:none; margin-top:20px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h3 style="margin:0; font-size:16px;">📝 แก้ไขคำแปลและตัวอักษรในบอลลูน (Live Editor)</h3>
                        <button class="btn" onclick="reRenderWithEdits()">✨ รีเรนเดอร์ข้อความใหม่</button>
                    </div>
                    <table class="table-editor">
                        <thead>
                            <tr>
                                <th style="width:50px;">ลำดับ</th>
                                <th style="width:140px;">พิกัดบอลลูน (BBox)</th>
                                <th>ข้อความญี่ปุ่นต้นฉบับ</th>
                                <th>คำแปลภาษาไทย (แก้ไขได้)</th>
                            </tr>
                        </thead>
                        <tbody id="bubblesTbody"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            let currentBubbles = [];
            let currentImageSource = 'sample';

            async function checkWorker() {
                const badge = document.getElementById('workerStatusBadge');
                badge.innerText = 'Pinging...';
                try {
                    const res = await fetch('/api/check-worker');
                    const data = await res.json();
                    if (data.status === 'online') {
                        badge.className = 'badge badge-online';
                        badge.innerText = '● Online (' + (data.details.gpu || 'Ready') + ')';
                    } else {
                        badge.className = 'badge badge-offline';
                        badge.innerText = '● Offline';
                    }
                } catch(e) {
                    badge.className = 'badge badge-offline';
                    badge.innerText = '● Unreachable';
                }
            }

            async function runSampleDemo() {
                const viewer = document.getElementById('viewerGrid');
                const editor = document.getElementById('editorSection');
                viewer.style.display = 'grid';
                document.getElementById('imgOriginal').src = '';
                document.getElementById('imgCleaned').src = '';
                document.getElementById('imgResult').src = '';

                const res = await fetch('/api/demo-sample');
                const data = await res.json();
                renderPipelineResults(data);
            }

            async function uploadCustomManga(input) {
                if (!input.files || !input.files[0]) return;
                const file = input.files[0];
                const formData = new FormData();
                formData.append('file', file);

                document.getElementById('viewerGrid').style.display = 'grid';
                const res = await fetch('/api/process-custom-page', { method: 'POST', body: formData });
                const data = await res.json();
                currentImageSource = data.saved_path;
                renderPipelineResults(data);
            }

            function renderPipelineResults(data) {
                document.getElementById('viewerGrid').style.display = 'grid';
                document.getElementById('editorSection').style.display = 'block';

                document.getElementById('imgOriginal').src = 'data:image/png;base64,' + data.original_b64;
                document.getElementById('imgCleaned').src = 'data:image/png;base64,' + data.cleaned_b64;
                document.getElementById('imgResult').src = 'data:image/png;base64,' + data.result_b64;
                document.getElementById('downloadBtn').href = 'data:image/png;base64,' + data.result_b64;

                currentBubbles = data.bubbles;
                populateEditor(data.bubbles);
            }

            function populateEditor(bubbles) {
                const tbody = document.getElementById('bubblesTbody');
                tbody.innerHTML = '';
                bubbles.forEach((b, idx) => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><b>#${b.id}</b></td>
                        <td style="font-family:monospace; font-size:11px;">[${b.bbox.join(', ')}]</td>
                        <td><input type="text" id="jp_${idx}" value="${escapeHtml(b.jp_text)}"></td>
                        <td><textarea id="th_${idx}" rows="2">${escapeHtml(b.th_text)}</textarea></td>
                    `;
                    tbody.appendChild(tr);
                });
            }

            async function reRenderWithEdits() {
                const updatedDialogues = currentBubbles.map((b, idx) => {
                    return {
                        id: b.id,
                        bbox: b.bbox,
                        jp: document.getElementById('jp_' + idx).value,
                        th: document.getElementById('th_' + idx).value
                    };
                });

                const payload = {
                    image_source: currentImageSource,
                    dialogues: updatedDialogues
                };

                const res = await fetch('/api/rerender', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                document.getElementById('imgResult').src = 'data:image/png;base64,' + data.result_b64;
                document.getElementById('downloadBtn').href = 'data:image/png;base64,' + data.result_b64;
            }

            function escapeHtml(str) {
                if (!str) return '';
                return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
            }

            // Check worker on load
            checkWorker();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/check-worker")
async def check_worker():
    return await orchestrator.check_worker_health()


@app.get("/api/demo-sample")
async def demo_sample():
    sample_path = INPUT_DIR / "sample_manga.png"
    if not sample_path.exists():
        from scripts.create_sample_manga import generate_sample_manga
        sample_path = generate_sample_manga(str(sample_path))

    res = pipeline.process_page(sample_path)
    return {
        "status": "success",
        "saved_path": str(sample_path),
        "bubbles": res["bubbles"],
        "original_b64": bgr_to_base64(res["original_bgr"]),
        "cleaned_b64": bgr_to_base64(res["cleaned_bgr"]),
        "result_b64": pil_to_base64(res["result_pil"]),
    }


@app.post("/api/process-custom-page")
async def process_custom_page(file: UploadFile = File(...)):
    save_path = INPUT_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    res = pipeline.process_page(save_path)
    return {
        "status": "success",
        "saved_path": str(save_path),
        "bubbles": res["bubbles"],
        "original_b64": bgr_to_base64(res["original_bgr"]),
        "cleaned_b64": bgr_to_base64(res["cleaned_bgr"]),
        "result_b64": pil_to_base64(res["result_pil"]),
    }


class ReRenderRequest(BaseModel):
    image_source: str
    dialogues: List[Dict[str, Any]]


@app.post("/api/rerender")
async def rerender(req: ReRenderRequest):
    img_path = Path(req.image_source) if req.image_source != "sample" else (INPUT_DIR / "sample_manga.png")
    if not img_path.exists():
        img_path = INPUT_DIR / "sample_manga.png"

    bboxes = [d.get("bbox") for d in req.dialogues if "bbox" in d]
    dialogues = [{"jp": d.get("jp", ""), "th": d.get("th", "")} for d in req.dialogues]

    res = pipeline.process_page(img_path, dialogues=dialogues, custom_bboxes=bboxes)
    return {
        "status": "success",
        "result_b64": pil_to_base64(res["result_pil"]),
    }


if __name__ == "__main__":
    uvicorn.run("control_center.app:app", host="0.0.0.0", port=8000, reload=True)
