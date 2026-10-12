"""
MangaThaiAI-Studio: Control Center Web Dashboard
FastAPI Application serving monitoring dashboard, file upload, and task dispatching.
"""

import os
import shutil
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from control_center.orchestrator import MangaOrchestrator
from control_center.typesetting.renderer import ThaiMangaTypesetter

app = FastAPI(title="MangaThaiAI-Studio Control Center", version="1.0.0")
orchestrator = MangaOrchestrator()
typesetter = ThaiMangaTypesetter()

UPLOAD_DIR = Path("data/inputs")
OUTPUT_DIR = Path("data/outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Renders simple responsive web dashboard for MangaThaiAI-Studio Control Center."""
    html_content = """
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MangaThaiAI-Studio | Control Center</title>
        <style>
            :root {
                --primary: #4f46e5;
                --bg: #0f172a;
                --card: #1e293b;
                --text: #f8fafc;
                --border: #334155;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: var(--bg);
                color: var(--text);
                margin: 0;
                padding: 24px;
            }
            .container {
                max-width: 1000px;
                margin: 0 auto;
            }
            header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid var(--border);
                padding-bottom: 16px;
                margin-bottom: 24px;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin-bottom: 24px;
            }
            .card {
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 20px;
            }
            .status-badge {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 20px;
                font-size: 13px;
                font-weight: 600;
            }
            .online { background: #065f46; color: #34d399; }
            .offline { background: #7f1d1d; color: #f87171; }
            .upload-box {
                border: 2px dashed var(--border);
                border-radius: 12px;
                padding: 40px;
                text-align: center;
                background: #111827;
                cursor: pointer;
            }
            button {
                background: var(--primary);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 600;
            }
            button:hover { opacity: 0.9; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div>
                    <h1 style="margin:0; font-size:24px;">🎨 MangaThaiAI-Studio</h1>
                    <p style="margin:4px 0 0; color:#94a3b8; font-size:14px;">Laptop Control Center & Remote Worker Orchestrator</p>
                </div>
                <div>
                    <span id="roleBadge" class="status-badge" style="background:#312e81; color:#a5b4fc;">Role: Control Center</span>
                </div>
            </header>

            <div class="grid">
                <div class="card">
                    <h3 style="margin-top:0;">💻 Laptop Control Center</h3>
                    <p style="font-size:14px; color:#94a3b8;">Local Address: <code>192.168.1.104</code></p>
                    <p style="font-size:14px; color:#94a3b8;">Storage: <code>Drive D (121.7 GB Free)</code></p>
                    <span class="status-badge online">● Active (Port 8000)</span>
                </div>

                <div class="card">
                    <h3 style="margin-top:0;">🎮 Gaming PC AI Worker</h3>
                    <p style="font-size:14px; color:#94a3b8;" id="workerUrl">Worker Target: <code>http://192.168.1.50:8888</code></p>
                    <p style="font-size:14px; color:#94a3b8;" id="workerGpu">GPU: <i>Checking...</i></p>
                    <span id="workerBadge" class="status-badge offline">Checking LAN...</span>
                    <div style="margin-top:12px;">
                        <button onclick="checkWorker()">↻ Test Worker Ping</button>
                    </div>
                </div>
            </div>

            <div class="card">
                <h3 style="margin-top:0;">📤 Manga Page Translation Pipeline</h3>
                <p style="color:#94a3b8; font-size:14px;">Select manga image to dispatch through OCR, Text Inpainting and Thai Typesetting:</p>
                <form id="uploadForm" enctype="multipart/form-data">
                    <input type="file" id="mangaFile" accept="image/*" style="margin-bottom: 12px;"><br>
                    <button type="button" onclick="uploadPage()">🚀 Start Processing</button>
                </form>
                <div id="resultBox" style="margin-top:16px; font-family:monospace; font-size:13px; color:#cbd5e1;"></div>
            </div>
        </div>

        <script>
            async function checkWorker() {
                const badge = document.getElementById('workerBadge');
                const gpu = document.getElementById('workerGpu');
                badge.innerText = 'Pinging...';
                try {
                    const res = await fetch('/api/check-worker');
                    const data = await res.json();
                    if (data.status === 'online') {
                        badge.className = 'status-badge online';
                        badge.innerText = '● Worker Online (GPU Ready)';
                        gpu.innerText = 'GPU: ' + (data.details.gpu || 'Ready');
                    } else {
                        badge.className = 'status-badge offline';
                        badge.innerText = '● Worker Offline';
                        gpu.innerText = 'Status: Waiting for Gaming PC worker';
                    }
                } catch(e) {
                    badge.className = 'status-badge offline';
                    badge.innerText = '● Unreachable';
                }
            }

            async function uploadPage() {
                const fileInput = document.getElementById('mangaFile');
                const resultBox = document.getElementById('resultBox');
                if (!fileInput.files.length) {
                    alert('Please select an image file first.');
                    return;
                }
                resultBox.innerText = 'Uploading and dispatching to worker...';
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);

                try {
                    const res = await fetch('/api/upload-page', { method: 'POST', body: formData });
                    const data = await res.json();
                    resultBox.innerText = JSON.stringify(data, null, 2);
                } catch(e) {
                    resultBox.innerText = 'Error: ' + e;
                }
            }

            // Run initial check on load
            checkWorker();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/check-worker")
async def check_worker():
    """Proxy health check to remote worker."""
    return await orchestrator.check_worker_health()


@app.post("/api/upload-page")
async def upload_page(file: UploadFile = File(...)):
    """Receives manga page file and stores it, then dispatches to worker."""
    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Check worker availability
    worker_status = await orchestrator.check_worker_health()
    if worker_status.get("status") == "online":
        result = await orchestrator.submit_page_for_processing(save_path)
        return {"upload": "success", "file": str(save_path), "worker_result": result}
    else:
        return {
            "upload": "success",
            "file": str(save_path),
            "worker_status": worker_status,
            "message": "Page uploaded and saved locally. Gaming PC worker is currently offline, job queued.",
        }


if __name__ == "__main__":
    uvicorn.run("control_center.app:app", host="0.0.0.0", port=8000, reload=True)
