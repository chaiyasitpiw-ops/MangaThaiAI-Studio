"""
MangaThaiAI-Studio: Interactive Control Center Web Studio & Real-Time Web Reader
Features:
- Live Zero-Training Manga Translation Demo
- Real-Time Web Manga Reader (Enter URL to read and translate live)
- Universal Browser Bookmarklet (Live translation overlay on ANY external manga website)
- Side-by-Side Visual Comparison & Live Bubble Editor
- CORS-enabled API for external browser interactions
"""

import base64
import io
import json
import logging
import os
import shutil
import tempfile
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
from control_center.web_reader.crawler import WebMangaCrawler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ControlCenterApp")

app = FastAPI(title="MangaThaiAI-Studio Control Center", version="1.0.0")

# Enable CORS for bookmarklet calls from any website
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path("D:/code/MangaThaiAI-Studio")
INPUT_DIR = BASE_DIR / "data/inputs"
OUTPUT_DIR = BASE_DIR / "data/outputs"
STATIC_DIR = BASE_DIR / "control_center/static"

INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

pipeline = ZeroTrainingMangaPipeline()
orchestrator = MangaOrchestrator()
crawler = WebMangaCrawler()


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
        <title>MangaThaiAI-Studio | Real-Time Manga Translator</title>
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
            .tabs {
                display: flex;
                gap: 12px;
                margin-bottom: 20px;
                border-bottom: 1px solid var(--card-border);
                padding-bottom: 8px;
            }
            .tab-btn {
                background: transparent;
                border: none;
                color: var(--text-muted);
                padding: 10px 18px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 15px;
                font-weight: 600;
                transition: all 0.2s;
            }
            .tab-btn.active {
                background: var(--card);
                color: #fff;
                border: 1px solid var(--primary);
            }
            .tab-btn:hover { color: #fff; }

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
            .input-text {
                width: 100%;
                background: #090d16;
                color: #fff;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
            }
            .manga-page-card {
                background: #0b1120;
                border: 1px solid var(--card-border);
                border-radius: 8px;
                margin-bottom: 24px;
                padding: 16px;
                text-align: center;
            }
            .manga-page-card img {
                max-width: 100%;
                max-height: 850px;
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div>
                    <h1 style="margin:0; font-size:26px;">🎨 MangaThaiAI-Studio</h1>
                    <p style="margin:4px 0 0; color:var(--text-muted); font-size:14px;">
                        ระบบแปลมังงะญี่ปุ่นเป็นไทยแบบเรียลไทม์ | <b>Live Web Manga Translator</b>
                    </p>
                </div>
                <div>
                    <span class="badge badge-online">● Laptop Control Center (Online)</span>
                </div>
            </header>

            <!-- Navigation Tabs -->
            <div class="tabs">
                <button class="tab-btn active" onclick="switchTab('tab-webreader')">🌐 โหมดแปลหน้าเว็บมังงะแบบเรียลไทม์ (Web Reader)</button>
                <button class="tab-btn" onclick="switchTab('tab-bookmarklet')">📌 Bookmarklet (แปลบนเว็บใดก็ได้ในโลก)</button>
                <button class="tab-btn" onclick="switchTab('tab-studio')">🛠 สตูดิโอตรวจจับ & ปรับแต่งบอลลูน (Manual Studio)</button>
            </div>

            <!-- ================= TAB 1: WEB READER ================= -->
            <div id="tab-webreader" class="tab-content">
                <div class="card">
                    <h2 style="margin-top:0; font-size:18px;">🌐 ใส่ URL หน้าเว็บมังงะเพื่ออ่านและแปลภาษาไทยแบบเรียลไทม์</h2>
                    <p style="color:var(--text-muted); font-size:13px; margin-bottom:16px;">
                        วางลิงก์หน้าเว็บมังงะ (Manga Chapter URL) หรือลิงก์รูปภาพมังงะ ระบบจะดึงหน้ามังงะมาแสดงและแปลภาษาไทยสดทีละหน้าหรือทุกหน้าอัตโนมัติ
                    </p>
                    <div style="display:flex; gap:10px;">
                        <input type="text" id="webUrlInput" class="input-text" placeholder="ตัวอย่าง: https://example.com/manga-chapter-1 หรือ ลิงก์รูปภาพมังงะ .png / .jpg">
                        <button class="btn btn-success" style="white-space:nowrap;" onclick="fetchAndReadWebManga()">🚀 ดึงข้อมูล & เปิดอ่าน</button>
                    </div>
                    <div style="margin-top:10px; font-size:12px; color:var(--text-muted);">
                        💡 ตัวอย่างสำหรับทดสอบด่วน: <a href="javascript:void(0)" style="color:#818cf8;" onclick="loadTestUrl()">คลิกที่นี่เพื่อใส่ URL ตัวอย่างมังงะทดสอบ</a>
                    </div>
                </div>

                <!-- Web Reader Results Viewer -->
                <div id="webReaderSection" style="display:none;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                        <h3 id="mangaTitleHeader" style="margin:0; font-size:16px; color:#a5b4fc;">รายการหน้ามังงะ</h3>
                        <div>
                            <button class="btn btn-success" onclick="translateAllWebPages()">⚡ แปลทุกหน้าในตอนนี้อัตโนมัติ (Translate All)</button>
                        </div>
                    </div>
                    <div id="pagesContainer"></div>
                </div>
            </div>

            <!-- ================= TAB 2: BOOKMARKLET ================= -->
            <div id="tab-bookmarklet" class="tab-content" style="display:none;">
                <div class="card">
                    <h2 style="margin-top:0; font-size:18px;">📌 ติดตั้ง Bookmarklet แปลมังงะสดบนทุกเว็บไซต์ (One-Click In-Browser Translator)</h2>
                    <p style="color:var(--text-muted); font-size:14px; line-height:1.6;">
                        คุณสามารถแปลมังงะสดได้โดยตรงขณะที่เปิดเว็บไซต์อ่านมังงะใด ๆ ในโลก (เช่น Comic-Walker, Shonen Jump+, Twitter/X, Raw Manga Sites) เพียงลากปุ่มด้านล่างนี้ไปวางที่แถบบุ๊กมาร์ก (Bookmarks Bar) ของเบราว์เซอร์:
                    </p>

                    <div style="background:#090d16; border:2px dashed #4f46e5; border-radius:12px; padding:24px; text-align:center; margin:20px 0;">
                        <a href="javascript:(function(){var s=document.createElement('script');s.src='http://localhost:8000/static/bookmarklet.js?t='+Date.now();document.body.appendChild(s);})();" 
                           class="btn btn-success" 
                           style="font-size:16px; padding:12px 24px; text-decoration:none; display:inline-block; cursor:grab;"
                           title="ลากปุ่มนี้ไปวางที่ Bookmarks Bar ของเบราว์เซอร์">
                            📌 แปลมังงะไทยสด (MangaThaiAI)
                        </a>
                        <p style="margin-top:12px; font-size:12px; color:var(--text-muted);">
                            👆 <b>วิธีติดตั้ง:</b> คลิกเมาส์ค้างที่ปุ่มสีเขียวนี้ แล้ว<b>ลาก (Drag & Drop)</b> ไปปล่อยที่แถบ Bookmarks Bar ด้านบนของเบราว์เซอร์
                        </p>
                    </div>

                    <h3 style="font-size:15px; margin-top:20px;">📖 วิธีใช้งานบนหน้าเว็บจริง:</h3>
                    <ol style="color:#cbd5e1; font-size:14px; line-height:1.8; padding-left:20px;">
                        <li>เปิดหน้าเว็บมังงะภาษาญี่ปุ่นที่คุณต้องการอ่านตามปกติ</li>
                        <li>กดคลิกที่บุ๊กมาร์ก <b>"แปลมังงะไทยสด (MangaThaiAI)"</b> บนแถบเบราว์เซอร์ 1 ครั้ง</li>
                        <li>จะมีเมนูลอยปรากฏขึ้นที่มุมขวาล่าง คุณสามารถ<b>คลิกที่รูปภาพมังงะใด ๆ</b> เพื่อให้ระบบแปลเป็นภาษาไทยทับบนหน้านั้นได้ทันที!</li>
                    </ol>
                </div>
            </div>

            <!-- ================= TAB 3: STUDIO ================= -->
            <div id="tab-studio" class="tab-content" style="display:none;">
                <div class="card">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                        <div>
                            <h2 style="margin:0; font-size:18px;">สตูดิโอปรับแต่งบอลลูนและคำแปล (Manual Editor)</h2>
                            <p style="margin:4px 0 0; color:var(--text-muted); font-size:13px;">
                                โหลดหน้ามังงะ ปรับแต่งคำแปล แก้ไขข้อความ และดาวน์โหลดไฟล์
                            </p>
                        </div>
                        <div style="display:flex; gap:10px;">
                            <button class="btn btn-success" onclick="runSampleDemo()">🚀 โหลดตัวอย่างมังงะ</button>
                            <label class="btn btn-outline" style="cursor:pointer; display:inline-block;">
                                📁 อัปโหลดไฟล์รูปภาพ
                                <input type="file" id="customFileInput" accept="image/*" style="display:none;" onchange="uploadCustomManga(this)">
                            </label>
                        </div>
                    </div>

                    <!-- Viewer -->
                    <div class="viewer-grid" id="viewerGrid" style="display:none;">
                        <div class="view-box">
                            <h4>1. ต้นฉบับ (Original JP)</h4>
                            <img id="imgOriginal" src="" alt="Original">
                        </div>
                        <div class="view-box">
                            <h4>2. ลบตัวหนังสือ (Cleaned Inpaint)</h4>
                            <img id="imgCleaned" src="" alt="Cleaned">
                        </div>
                        <div class="view-box">
                            <h4>3. แปลไทย (Thai Typeset)</h4>
                            <img id="imgResult" src="" alt="Translated Thai">
                            <div style="margin-top:10px;">
                                <a id="downloadBtn" href="#" download="manga_thai.png" class="btn" style="text-decoration:none; display:inline-block; font-size:13px; padding:6px 14px;">💾 ดาวน์โหลดภาพแปลไทย</a>
                            </div>
                        </div>
                    </div>

                    <!-- Editor -->
                    <div id="editorSection" style="display:none; margin-top:20px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <h3 style="margin:0; font-size:16px;">📝 แก้ไขคำแปลในบอลลูน (Live Editor)</h3>
                            <button class="btn" onclick="reRenderWithEdits()">✨ รีเรนเดอร์ข้อความใหม่</button>
                        </div>
                        <table class="table-editor">
                            <thead>
                                <tr>
                                    <th style="width:50px;">ลำดับ</th>
                                    <th style="width:140px;">พิกัดบอลลูน</th>
                                    <th>ข้อความญี่ปุ่นต้นฉบับ</th>
                                    <th>คำแปลภาษาไทย (แก้ไขได้)</th>
                                </tr>
                            </thead>
                            <tbody id="bubblesTbody"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let currentBubbles = [];
            let currentImageSource = 'sample';
            let fetchedWebImages = [];

            function switchTab(tabId) {
                document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                document.getElementById(tabId).style.display = 'block';
                event.target.classList.add('active');
            }

            function loadTestUrl() {
                document.getElementById('webUrlInput').value = 'http://localhost:8000/static/sample_manga.png';
            }

            async function fetchAndReadWebManga() {
                const url = document.getElementById('webUrlInput').value.trim();
                if (!url) {
                    alert('กรุณาใส่ URL หน้าเว็บมังงะ');
                    return;
                }
                const container = document.getElementById('pagesContainer');
                const section = document.getElementById('webReaderSection');
                const titleHeader = document.getElementById('mangaTitleHeader');

                container.innerHTML = '<p style="color:#fbbf24;">⏳ กำลังดึงหน้ามังงะจากหน้าเว็บ...</p>';
                section.style.display = 'block';

                try {
                    const res = await fetch('/api/fetch-webpage-manga', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: url })
                    });
                    const data = await res.json();
                    titleHeader.innerText = '📖 ' + (data.title || 'Manga Reader') + ` (${data.count} หน้า)`;
                    fetchedWebImages = data.images;

                    if (!data.images.length) {
                        container.innerHTML = '<p style="color:#f87171;">ไม่พบรูปภาพมังงะใน URL นี้ (หรืออาจติด Cloudflare/Login)</p>';
                        return;
                    }

                    container.innerHTML = '';
                    data.images.forEach((imgUrl, idx) => {
                        const card = document.createElement('div');
                        card.className = 'manga-page-card';
                        card.id = 'pageCard_' + idx;
                        card.innerHTML = `
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                                <span style="font-weight:600; font-size:14px; color:#cbd5e1;">หน้า ${idx + 1}</span>
                                <div style="display:flex; gap:8px;">
                                    <button class="btn btn-outline" style="font-size:12px; padding:6px 12px;" onclick="toggleOriginalView(${idx})">👁 สลับดูต้นฉบับ</button>
                                    <button id="btnTranslate_${idx}" class="btn btn-success" style="font-size:12px; padding:6px 12px;" onclick="translateSingleWebPage(${idx}, '${escapeHtml(imgUrl)}')">⚡ แปลหน้านี้ทันที</button>
                                </div>
                            </div>
                            <img id="mangaImg_${idx}" src="${escapeHtml(imgUrl)}" data-original="${escapeHtml(imgUrl)}" alt="Page ${idx + 1}">
                            <div id="status_${idx}" style="margin-top:8px; font-size:12px; color:#94a3b8;">ต้นฉบับภาษาญี่ปุ่น</div>
                        `;
                        container.appendChild(card);
                    });
                } catch(e) {
                    container.innerHTML = '<p style="color:#f87171;">เกิดข้อผิดพลาดในการดึงข้อมูล: ' + e + '</p>';
                }
            }

            async function translateSingleWebPage(idx, imgUrl) {
                const imgEl = document.getElementById('mangaImg_' + idx);
                const statusEl = document.getElementById('status_' + idx);
                const btn = document.getElementById('btnTranslate_' + idx);

                btn.disabled = true;
                btn.innerText = '⏳ กำลังแปล...';
                statusEl.innerHTML = '<span style="color:#fbbf24;">กำลังลบตัวหนังสือและลงภาษาไทย...</span>';

                try {
                    const res = await fetch('/api/translate-image-url', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ image_url: imgUrl })
                    });
                    const data = await res.json();
                    if (data.status === 'success') {
                        imgEl.src = 'data:image/png;base64,' + data.result_b64;
                        imgEl.setAttribute('data-translated', 'data:image/png;base64,' + data.result_b64);
                        statusEl.innerHTML = `<span style="color:#34d399;">✓ แปลเป็นภาษาไทยเรียบร้อย (${data.bubbles_count} บอลลูน)</span>`;
                        btn.innerText = '✓ แปลแล้ว';
                    } else {
                        statusEl.innerHTML = `<span style="color:#f87171;">เกิดข้อผิดพลาด: ${data.error}</span>`;
                        btn.innerText = '⚡ ลองใหม่';
                        btn.disabled = false;
                    }
                } catch(e) {
                    statusEl.innerHTML = `<span style="color:#f87171;">ข้อผิดพลาด: ${e}</span>`;
                    btn.disabled = false;
                }
            }

            async function translateAllWebPages() {
                for (let i = 0; i < fetchedWebImages.length; i++) {
                    await translateSingleWebPage(i, fetchedWebImages[i]);
                }
            }

            function toggleOriginalView(idx) {
                const imgEl = document.getElementById('mangaImg_' + idx);
                const orig = imgEl.getAttribute('data-original');
                const trans = imgEl.getAttribute('data-translated');
                const statusEl = document.getElementById('status_' + idx);

                if (!trans) {
                    alert('หน้านี้ยังไม่ได้แปล กรุณากดแปลก่อนครับ');
                    return;
                }

                if (imgEl.src === trans) {
                    imgEl.src = orig;
                    statusEl.innerHTML = `<span style="color:#94a3b8;">กำลังดู: ภาพต้นฉบับ</span>`;
                } else {
                    imgEl.src = trans;
                    statusEl.innerHTML = `<span style="color:#34d399;">กำลังดู: ภาพแปลไทย</span>`;
                }
            }

            // Studio Functions
            async function runSampleDemo() {
                const viewer = document.getElementById('viewerGrid');
                viewer.style.display = 'grid';
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
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


class FetchWebpageRequest(BaseModel):
    url: str


@app.post("/api/fetch-webpage-manga")
async def fetch_webpage_manga(req: FetchWebpageRequest):
    return await crawler.extract_manga_images_from_url(req.url)


class TranslateImageUrlRequest(BaseModel):
    image_url: str
    referer: Optional[str] = None


@app.post("/api/translate-image-url")
async def translate_image_url(req: TranslateImageUrlRequest):
    try:
        # If url is local static sample
        if "sample_manga.png" in req.image_url:
            local_path = INPUT_DIR / "sample_manga.png"
            if not local_path.exists():
                from scripts.create_sample_manga import generate_sample_manga
                local_path = generate_sample_manga(str(local_path))
            res = pipeline.process_page(local_path)
        else:
            image_bytes = await crawler.fetch_image_bytes(req.image_url, referer=req.referer)
            # Save temporarily
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = Path(tmp.name)

            try:
                res = pipeline.process_page(tmp_path)
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

        return {
            "status": "success",
            "bubbles_count": len(res["bubbles"]),
            "bubbles": res["bubbles"],
            "cleaned_b64": bgr_to_base64(res["cleaned_bgr"]),
            "result_b64": pil_to_base64(res["result_pil"]),
        }
    except Exception as e:
        logger.error(f"Error translating image {req.image_url}: {e}")
        return {"status": "error", "error": str(e)}


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
    import uvicorn
    uvicorn.run("control_center.app:app", host="0.0.0.0", port=8000, reload=True)
