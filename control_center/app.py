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
    html_content = """
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="มังงะไทย">
        <meta name="theme-color" content="#6366f1">
        <link rel="manifest" href="/static/manifest.json">
        <link rel="apple-touch-icon" href="/static/icon-192.png">
        <title>MangaThaiAI-Studio | Real-Time Manga & Webtoon Studio</title>
        <!-- Google Fonts: Mali (Comic), Kanit (Action), Chakra Petch (Gaming Status), Prompt (UI) -->
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;700&family=Kanit:wght@400;600;700&family=Mali:wght@500;600;700&family=Prompt:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #6366f1;
                --primary-hover: #4f46e5;
                --accent-cyan: #38bdf8;
                --accent-gold: #fbbf24;
                --success: #10b981;
                --danger: #ef4444;
                --bg: #070b14;
                --card: #0f172a;
                --card-border: #1e293b;
                --text: #f8fafc;
                --text-muted: #94a3b8;
            }
            * { box-sizing: border-box; }
            body {
                font-family: 'Prompt', -apple-system, BlinkMacSystemFont, sans-serif;
                background-color: var(--bg);
                color: var(--text);
                margin: 0;
                padding: 20px;
                padding-bottom: 80px;
                line-height: 1.5;
                padding-left: max(20px, env(safe-area-inset-left));
                padding-right: max(20px, env(safe-area-inset-right));
                padding-bottom: max(80px, env(safe-area-inset-bottom));
            }
            .container { max-width: 1320px; margin: 0 auto; }
            header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid var(--card-border);
                padding-bottom: 16px;
                margin-bottom: 20px;
                flex-wrap: wrap;
                gap: 12px;
            }
            .header-title {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .logo-icon {
                font-size: 28px;
                background: linear-gradient(135deg, #6366f1, #38bdf8);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .tabs {
                display: flex;
                gap: 8px;
                margin-bottom: 20px;
                border-bottom: 1px solid var(--card-border);
                padding-bottom: 8px;
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
                scrollbar-width: none;
            }
            .tabs::-webkit-scrollbar { display: none; }
            .tab-btn {
                background: transparent;
                border: none;
                color: var(--text-muted);
                padding: 10px 18px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Prompt', sans-serif;
                transition: all 0.2s;
                white-space: nowrap;
                min-height: 44px;
                display: inline-flex;
                align-items: center;
                gap: 8px;
            }
            .tab-btn.active {
                background: var(--card);
                color: #fff;
                border: 1px solid var(--primary);
                box-shadow: 0 0 15px rgba(99, 102, 241, 0.25);
            }
            .tab-btn:hover { color: #fff; }

            .card {
                background: var(--card);
                border: 1px solid var(--card-border);
                border-radius: 14px;
                padding: 22px;
                margin-bottom: 20px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            }
            .badge {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 5px 12px;
                border-radius: 999px;
                font-size: 12px;
                font-weight: 600;
            }
            .badge-online { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
            .badge-fast { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
            
            .btn {
                background: var(--primary);
                color: white;
                border: none;
                padding: 10px 18px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Prompt', sans-serif;
                transition: all 0.2s;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                min-height: 44px;
                -webkit-tap-highlight-color: transparent;
            }
            .btn:hover { background: var(--primary-hover); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3); }
            .btn:active { transform: scale(0.97); }
            .btn-success { background: var(--success); }
            .btn-success:hover { background: #059669; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); }
            .btn-outline { background: transparent; border: 1px solid var(--card-border); color: var(--text); }
            .btn-outline:hover { background: #1e293b; color: #fff; }
            .btn-theater { background: #1e1b4b; border: 1px solid #6366f1; color: #c7d2fe; }
            .btn-theater:hover { background: #312e81; color: #fff; }

            .input-text, select.input-text {
                background: #090d16;
                color: #fff;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                font-family: 'Prompt', sans-serif;
                outline: none;
                transition: border-color 0.2s;
                min-height: 44px;
            }
            .input-text:focus, select.input-text:focus { border-color: var(--primary); }

            /* Tag Pills */
            .tag-pill {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: #090d16;
                border: 1px solid #334155;
                color: #cbd5e1;
                padding: 6px 14px;
                border-radius: 999px;
                font-size: 12px;
                font-weight: 500;
                text-decoration: none;
                cursor: pointer;
                transition: all 0.2s;
            }
            .tag-pill:hover {
                border-color: #6366f1;
                color: #fff;
                background: #1e1b4b;
                transform: translateY(-1px);
            }

            /* Step Cards for iOS & Deploy Guides */
            .step-card {
                background: #090d16;
                border: 1px solid #1e293b;
                border-radius: 12px;
                padding: 18px;
                position: relative;
                transition: all 0.2s;
            }
            .step-card:hover { border-color: #38bdf8; transform: translateY(-2px); }
            .step-badge {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 28px;
                height: 28px;
                border-radius: 50%;
                background: #6366f1;
                color: #fff;
                font-weight: 700;
                font-size: 13px;
                margin-right: 8px;
                flex-shrink: 0;
            }

            /* Webtoon Reader Layout */
            #readerStreamWrapper {
                margin: 0 auto;
                max-width: 780px;
                transition: max-width 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .webtoon-page {
                width: 100%;
                display: block;
                margin: 0;
                padding: 0;
                position: relative;
                transition: all 0.3s ease;
            }
            .webtoon-page img {
                width: 100%;
                height: auto;
                display: block;
                border: none;
                margin: 0;
                padding: 0;
                transition: opacity 0.3s ease;
            }
            .page-floating-bar {
                background: rgba(15, 23, 42, 0.88);
                backdrop-filter: blur(8px);
                border-bottom: 1px solid rgba(51, 65, 85, 0.6);
                padding: 6px 14px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 12px;
                z-index: 10;
            }

            /* Floating Glass Controls HUD */
            .floating-hud {
                position: fixed;
                bottom: 24px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(15, 23, 42, 0.92);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(99, 102, 241, 0.4);
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
                border-radius: 999px;
                padding: 8px 18px;
                display: flex;
                align-items: center;
                gap: 14px;
                z-index: 100;
                transition: all 0.3s ease;
                bottom: max(24px, env(safe-area-inset-bottom));
            }
            .floating-hud:hover { border-color: var(--accent-cyan); }

            /* ON/OFF Power Toggle */
            .power-toggle {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 200;
                display: flex;
                align-items: center;
                gap: 8px;
                background: rgba(15, 23, 42, 0.95);
                backdrop-filter: blur(12px);
                border: 1px solid #334155;
                border-radius: 999px;
                padding: 8px 14px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                top: max(20px, env(safe-area-inset-top));
                right: max(20px, env(safe-area-inset-right));
            }
            .power-dot {
                width: 10px; height: 10px;
                border-radius: 50%;
                background: #10b981;
                box-shadow: 0 0 8px #10b981;
                transition: all 0.3s;
            }
            .power-dot.off {
                background: #ef4444;
                box-shadow: 0 0 8px #ef4444;
            }
            .toggle-switch {
                position: relative; width: 44px; height: 24px; cursor: pointer;
            }
            .toggle-switch input { opacity: 0; width: 0; height: 0; }
            .toggle-track {
                position: absolute; inset: 0;
                background: #1e293b;
                border-radius: 999px;
                border: 1px solid #334155;
                transition: 0.3s;
            }
            .toggle-switch input:checked + .toggle-track { background: #10b981; border-color: #10b981; }
            .toggle-thumb {
                position: absolute;
                top: 2px; left: 2px;
                width: 18px; height: 18px;
                background: white;
                border-radius: 50%;
                transition: 0.3s;
            }
            .toggle-switch input:checked ~ .toggle-thumb { left: 22px; }

            /* iOS Add to Home Screen Banner */
            #iosBanner {
                display: none;
                background: linear-gradient(135deg, #1e1b4b, #0f172a);
                border: 1px solid #6366f1;
                border-radius: 12px;
                padding: 14px 18px;
                margin-bottom: 16px;
                font-size: 13px;
                color: #c7d2fe;
                position: relative;
            }

            /* Fullscreen Theater Mode */
            body.theater-mode {
                padding: 0 !important;
                background: #000 !important;
            }
            body.theater-mode header,
            body.theater-mode .tabs,
            body.theater-mode #webUrlCard,
            body.theater-mode #progressHUD {
                display: none !important;
            }
            body.theater-mode .page-floating-bar {
                opacity: 0.15;
                transition: opacity 0.2s;
            }
            body.theater-mode .page-floating-bar:hover {
                opacity: 1;
            }
            body.theater-mode #readerStreamWrapper {
                margin: 0 auto !important;
            }
            body.theater-mode .power-toggle { opacity: 0.3; transition: 0.2s; }
            body.theater-mode .power-toggle:hover { opacity: 1; }

            /* Mobile Bottom Navigation Dock */
            .mobile-bottom-nav {
                display: none;
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: rgba(15, 23, 42, 0.94);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border-top: 1px solid #1e293b;
                padding: 6px 12px;
                padding-bottom: max(10px, env(safe-area-inset-bottom));
                z-index: 150;
                justify-content: space-around;
                align-items: center;
            }
            .mobile-nav-btn {
                background: transparent;
                border: none;
                color: #94a3b8;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 3px;
                font-size: 11px;
                font-weight: 600;
                font-family: 'Prompt', sans-serif;
                cursor: pointer;
                padding: 6px 12px;
                border-radius: 8px;
                transition: all 0.2s;
                -webkit-tap-highlight-color: transparent;
            }
            .mobile-nav-btn.active {
                color: #38bdf8;
                background: rgba(56, 189, 248, 0.1);
            }
            .mobile-nav-icon {
                font-size: 20px;
                line-height: 1;
            }

            /* Responsive rules */
            @media (max-width: 768px) {
                .mobile-bottom-nav { display: flex; }
                body { padding: 12px; padding-bottom: calc(75px + env(safe-area-inset-bottom)) !important; }
                .tabs { display: none !important; }
                h1 { font-size: 18px !important; }
                .card { padding: 16px; }
                #readerStreamWrapper { max-width: 100% !important; }
                .floating-hud { width: calc(100% - 32px); border-radius: 16px; padding: 10px 14px; }
                #floatingSideNav { display: none !important; }
                select.input-text, .input-text { font-size: 16px; }
            }
        </style>
    </head>
    <body>
        <!-- ON/OFF Power Toggle (Fixed, always visible) -->
        <div class="power-toggle" id="powerToggle">
            <div class="power-dot" id="powerDot"></div>
            <span style="font-size:12px; font-weight:600; color:#cbd5e1;" id="powerLabel">ระบบ: เปิด</span>
            <label class="toggle-switch" title="เปิด/ปิดระบบแปลอัตโนมัติ">
                <input type="checkbox" id="systemPowerSwitch" checked onchange="toggleSystemPower(this.checked)">
                <div class="toggle-track"></div>
                <div class="toggle-thumb"></div>
            </label>
        </div>

        <div class="container">
            <!-- iOS Add to Home Screen Banner -->
            <div id="iosBanner" class="card" style="border-color:#6366f1; background:#0f0e1f;">
                <div style="display:flex; align-items:flex-start; gap:12px;">
                    <span style="font-size:28px;">📱</span>
                    <div>
                        <b style="color:#a5b4fc; font-size:14px;">ติดตั้งเป็นแอปบน iPhone/iPad ของคุณ!</b>
                        <p style="margin:4px 0 0; font-size:12px; color:#94a3b8; line-height:1.6;">
                            กดปุ่ม <b style="color:#fff;">Share</b> (กล่องลูกศรขึ้น) ใน Safari → เลือก <b style="color:#fff;">"Add to Home Screen"</b><br>
                            → ใช้งานแบบแอปเต็มหน้าจอ ไร้แถบ URL กวนใจ!
                        </p>
                    </div>
                    <button onclick="document.getElementById('iosBanner').style.display='none'" style="background:none;border:none;color:#94a3b8;cursor:pointer;font-size:18px;padding:0;min-height:auto;">✕</button>
                </div>
            </div>

            <header>
                <div class="header-title">
                    <span class="logo-icon">⚡</span>
                    <div>
                        <h1 style="margin:0; font-size:24px; font-weight:700;">MangaThaiAI-Studio 2.0</h1>
                        <p style="margin:2px 0 0; color:var(--text-muted); font-size:13px;">
                            ระบบแปลมังงะ/มันฮวาเรียลไทม์ ฟอนต์การ์ตูนแท้ & จัดหน้าเว็บบาลานซ์ | Zero-Training Studio
                        </p>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    <span class="badge badge-fast">⚡ Sliced OCR 2.0 (เร่งสปีด 2 เท่า)</span>
                    <span class="badge badge-online">● Cloud Server Active</span>
                </div>
            </header>

            <!-- Desktop Category Tabs Navigation -->
            <div class="tabs">
                <button class="tab-btn active" data-tab="tab-webreader" onclick="switchTab('tab-webreader')">📖 อ่านมังงะ (Manga Reader)</button>
                <button class="tab-btn" data-tab="tab-settings" onclick="switchTab('tab-settings')">🎨 ฟอนต์ & ปรับแต่ง (Preferences)</button>
                <button class="tab-btn" data-tab="tab-ios" onclick="switchTab('tab-ios')">📱 iPhone / iPad (iOS App)</button>
                <button class="tab-btn" data-tab="tab-deploy" onclick="switchTab('tab-deploy')">🚀 วิธี Deploy เอง (Self-Deploy)</button>
            </div>

            <!-- ================= CATEGORY 1: WEB READER ================= -->
            <div id="tab-webreader" class="tab-content">
                <!-- Input Hero Card -->
                <div id="webUrlCard" class="card">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px;">
                        <h2 style="margin:0; font-size:17px; display:flex; align-items:center; gap:8px;">
                            <span>📖</span> วาง URL ตอนมังงะ/เว็บตูนเพื่อแปลและอ่านเป็นภาษาไทย
                        </h2>
                        <span class="badge" style="background:#064e3b; color:#6ee7b7; font-size:12px;">
                            ✓ รองรับ NewxToon, Asura Scans, MangaDex, Webtoons
                        </span>
                    </div>

                    <!-- URL Input & Action Buttons -->
                    <div style="display:flex; gap:10px; flex-wrap:wrap;">
                        <input type="text" id="webUrlInput" class="input-text" style="flex:1; min-width:280px;" 
                               placeholder="วางลิงก์ เช่น https://newxtoon5.com/comics/358/chapters/1080994">
                        
                        <!-- Action Buttons -->
                        <button class="btn btn-outline" style="border-color:#38bdf8; color:#38bdf8;" onclick="openSourceWebpage()" title="เปิดดูหน้าเว็บต้นฉบับในแท็บใหม่ทันที">
                            🌐 เปิดหน้าเว็บต้นฉบับ
                        </button>
                        <button class="btn btn-outline" style="border-color:#a855f7; color:#c084fc;" onclick="checkAllWebtoonPages()" title="เช็คจำนวนหน้าทั้งหมดในตอนนี้">
                            🔍 เช็คหน้าทั้งหมด
                        </button>
                        <button class="btn btn-success" onclick="fetchAndReadWebManga(true)" title="เช็คหน้าและแปลภาษาไทยครบทุกหน้าทันที">
                            ⚡ กดแปลทั้งหมดทันที
                        </button>
                        <button class="btn btn-primary" style="background:linear-gradient(135deg, #ec4899, #8b5cf6); border:none; color:white; font-weight:700; box-shadow:0 2px 10px rgba(236,72,153,0.3);" onclick="pasteFromIPhoneClipboard()" title="แตะเพื่อวางรูปภาพ หรือ URL จากคลิปบอร์ด iPhone ทันที">
                            📋 วางภาพจากคลิปบอร์ด iPhone
                        </button>
                        <button class="btn btn-outline" style="border-color:#10b981; color:#34d399;" onclick="document.getElementById('fileUploadInput').click()" title="อัปโหลดรูปภาพมังงะจากเครื่อง หรือกด Ctrl+V เพื่อวางรูปภาพได้ทันที">
                            📁 อัปโหลดรูป / ถ่ายภาพ (Photos)
                        </button>
                        <input type="file" id="fileUploadInput" accept="image/*" multiple style="display:none;" onchange="handleFileUpload(this.files)">
                    </div>

                    <!-- Quick Shortcuts / Tag Pills -->
                    <div style="margin-top:14px; display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                        <span style="font-size:12px; color:var(--text-muted); font-weight:600;">⚡ ตอนทดสอบด่วน:</span>
                        <a class="tag-pill" style="border-color:#ef4444; color:#fca5a5; font-weight:700; background:#450a0a;" onclick="loadQuickUrl('newxtoon_18')">🔞 NewXtoon 18+ ตอน 24 (졸업 후 반 친구들을 다 따먹음)</a>
                        <a class="tag-pill" style="border-color:#a855f7; color:#d8b4fe;" onclick="loadQuickUrl('newxtoon')">🇰🇷 NewxToon ตอน 120 (75 หน้า)</a>
                        <a class="tag-pill" onclick="loadQuickUrl('overgeared')">⚡ Overgeared ตอน 343 (Asura)</a>
                        <a class="tag-pill" onclick="loadQuickUrl('sololeveling')">⚔️ Solo Leveling</a>
                        <a class="tag-pill" onclick="loadQuickUrl('demo')">🧪 ภาพทดสอบระบบ Demo</a>
                    </div>

                    <!-- HTML Source / Direct Images Paste Box (Instant Cloudflare Bypass) -->
                    <div style="margin-top:12px;">
                        <button class="btn btn-outline" style="font-size:12px; padding:4px 12px; color:#38bdf8; border-color:#0284c7;" onclick="toggleHtmlPasteDrawer()">
                            📋 วางโค้ด HTML หน้าเว็บ / ลิงก์รูปภาพโดยตรง (แก้ปัญหาเว็บติด Cloudflare เช่น NewXtoon) ▼
                        </button>
                        <div id="htmlPasteDrawer" style="display:none; margin-top:10px; background:#0b1329; border:1px solid #334155; border-radius:8px; padding:12px;">
                            <div style="font-size:12px; color:#94a3b8; margin-bottom:6px;">
                                💡 หากเว็บมังงะติด Cloudflare ป้องกัน คุณสามารถเปิดหน้าเว็บในเบราว์เซอร์ → คลิกขวา <b>"ดูซอร์สโค้ดหน้าเว็บ (View Source)"</b> หรือกด <b>Ctrl+U</b> → คัดลอกมาวางที่นี่เพื่อดึงรูปครบ 100% ทันที:
                            </div>
                            <textarea id="rawHtmlInput" class="input-text" style="width:100%; height:90px; font-size:12px; font-family:monospace;" placeholder="วางโค้ด HTML ของหน้ามังงะ หรือวางลิงก์รูปภาพแยกทีละบรรทัดที่นี่..."></textarea>
                            <div style="margin-top:8px; display:flex; gap:8px; justify-content:flex-end;">
                                <button class="btn btn-success" style="font-size:12px; padding:6px 14px;" onclick="extractAndReadFromPastedHtml()">📥 ดึงรูปภาพจากโค้ด HTML ทันที</button>
                            </div>
                        </div>
                    </div>

                    <!-- In-App Webpage Preview Collapsible Drawer -->
                    <div id="webpagePreviewContainer" style="display:none; margin-top:16px; border-radius:10px; overflow:hidden; border:1px solid #334155; background:#000;">
                        <div style="background:#0f172a; padding:8px 14px; display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-size:13px; color:#38bdf8; font-weight:600;">🌐 หน้าเว็บต้นฉบับ (In-App Preview)</span>
                            <div style="display:flex; gap:8px;">
                                <button class="btn btn-outline" style="font-size:11px; padding:3px 8px;" onclick="openSourceWebpage()">↗ เปิดแท็บใหม่</button>
                                <button class="btn btn-outline" style="font-size:11px; padding:3px 8px;" onclick="toggleWebpagePreview()">✕ ปิดพรีวิว</button>
                            </div>
                        </div>
                        <iframe id="sourceWebpageIframe" style="width:100%; height:480px; border:none; background:#fff;" src="about:blank"></iframe>
                    </div>

                    <!-- Chapter Overview / Inspector Card (Appears after checking pages) -->
                    <div id="chapterInspectorCard" style="display:none; margin-top:16px; background:#091222; border:1px solid #2563eb; border-radius:10px; padding:14px 18px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                            <div>
                                <div style="font-size:11px; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px;">ผลการเช็คหน้าเว็บมังงะ</div>
                                <h3 id="inspectTitle" style="margin:4px 0; font-size:16px; color:#60a5fa;">ตอนมังงะ/เว็บตูน</h3>
                                <div id="inspectSubtitle" style="font-size:13px; color:#cbd5e1;">
                                    ตรวจพบทั้งหมด <b id="inspectPageCount" style="color:#34d399; font-size:15px;">0</b> หน้า | สถานะ: กำลังตรวจสอบ
                                </div>
                            </div>
                            <div style="display:flex; gap:10px; align-items:center;">
                                <button class="btn btn-outline" style="font-size:12px; padding:6px 12px;" onclick="toggleWebpagePreview()">👁 ดูพรีวิวเว็บ</button>
                                <button id="btnStartBatchInspect" class="btn btn-success" style="font-size:13px; padding:8px 18px; font-weight:700;" onclick="startBatchTranslation()">
                                    ⚡ เริ่มแปลทั้ง <span id="inspectPageCountBtn">0</span> หน้าทันที
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Compact Reader Preferences Bar -->
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:12px; margin-top:16px; padding-top:16px; border-top:1px solid #1e293b;">
                        <div>
                            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">🌐 ภาษาต้นฉบับ (Source Language):</label>
                            <select id="sourceLangSelect" class="input-text" style="width:100%;" onchange="onSettingChanged()">
                                <option value="auto" selected>🌐 ตรวจจับภาษาอัตโนมัติ (Auto-Detect)</option>
                                <option value="kr">🇰🇷 เกาหลี (Korean Manhwa - เช่น NewXtoon, Toptoon)</option>
                                <option value="ru">🇷🇺 รัสเซีย (Russian Manga/Webtoons - เช่น MangaLib)</option>
                                <option value="en">🇺🇸 อังกฤษ (English Comics/Webtoons - เช่น Asura)</option>
                                <option value="cn">🇨🇳 จีน (Chinese Manhua - เช่น ColaManga)</option>
                                <option value="jp">🇯🇵 ญี่ปุ่น (Japanese Manga & Doujinshi)</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">🎭 โทนสำนวนบทพูด:</label>
                            <select id="globalToneSelect" class="input-text" style="width:100%;" onchange="onSettingChanged()">
                                <option value="adult_18" selected>🔞 มังงะ 18+ / สายดาร์ก & ผู้ใหญ่ (เผ็ดร้อน ครางเสียว จัดหนัก [แนะนำ])</option>
                                <option value="shonen">⚔️ โชเน็น / แอ็กชัน (แก, ข้า, ลุย, ดุดัน)</option>
                                <option value="shojo">🌸 โรแมนติก / ตาหวาน (นาย, ฉัน, ละมุน)</option>
                                <option value="seinen">🕵️ สืบสวน / สุขุม (จริงจัง ลุ่มลึก เป็นธรรมชาติ)</option>
                                <option value="comedy">🤣 การ์ตูนแก๊ก / ตลก (คำสร้อย กวนๆ ฮาๆ)</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">🎨 ฟอนต์ตัวอักษร:</label>
                            <select id="fontFamilySelect" class="input-text" style="width:100%;" onchange="onSettingChanged()">
                                <option value="mali" selected>✍️ Mali Comic (ลายเส้นมังงะ เข้าถึงอารมณ์ [แนะนำ])</option>
                                <option value="kanit">⚔️ Kanit Shonen (แอ็กชันดุดัน คมชัด หนักแน่น)</option>
                                <option value="chakrapetch">🎮 Chakra Petch (ระบบเกม/สเตตัส ล้ำยุค)</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">✨ รูปแบบพื้นหลังบอลลูน:</label>
                            <select id="backdropModeSelect" class="input-text" style="width:100%;" onchange="onSettingChanged()">
                                <option value="natural" selected>🎨 ลายเส้นมังงะแท้ 100% (ไร้กรอบ ไร้เหลี่ยม [แนะนำ])</option>
                                <option value="soft_white">⚪ รองพื้นขาวนุ่มนวล (Soft White)</option>
                                <option value="none">✨ ตัวหนังสือเพียวๆ</option>
                            </select>
                        </div>
                    </div>

                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; flex-wrap:wrap; gap:8px;">
                        <label style="display:flex; align-items:center; gap:8px; cursor:pointer; font-size:13px; color:#a5b4fc; font-weight:600;">
                            <input type="checkbox" id="autoTranslateCheck" checked> ⚡ แปลภาษาไทยอัตโนมัติทันทีที่เปิดตอน (Auto Stream)
                        </label>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span class="badge" style="background:#064e3b; color:#6ee7b7; font-size:11px;">🛡️ ปิดกั้นโฆษณา & ป๊อปอัป 100%</span>
                            <a href="javascript:void(0)" onclick="switchTab('tab-settings')" style="color:#38bdf8; font-size:12px; text-decoration:none;">🎨 สตูดิโอปรับแต่งฟอนต์ & สำนวน →</a>
                        </div>
                    </div>
                </div>

                <!-- Web Reader Results Viewer -->
                <div id="webReaderSection" style="display:none;">
                    <!-- Real-time Progress HUD with Stopwatch & ETA -->
                    <div id="progressHUD" class="card" style="border:1px solid #3b82f6; background:#0c192c; margin-bottom:16px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                            <div>
                                <b id="progressTitle" style="color:#60a5fa; font-size:16px;">⏳ กำลังประมวลผลแปลภาษาไทย...</b>
                                <div id="progressSubtitle" style="font-size:13px; color:#cbd5e1; margin-top:4px;">
                                    หน้า 0/0 | ⏱ ใช้เวลาไปแล้ว: 00:00 วินาที | ⏳ ประมาณการเวลาที่เหลือ: คำนวณ...
                                </div>
                            </div>
                            <div style="display:flex; gap:8px;">
                                <button id="btnPauseResume" class="btn btn-outline" style="font-size:12px; padding:6px 12px;" onclick="togglePauseResume()">⏸ หยุดชั่วคราว</button>
                                <button class="btn btn-outline" style="font-size:12px; padding:6px 12px;" onclick="reTranslateAll()">↻ แปลซ้ำทุกหน้า</button>
                                <button class="btn btn-theater" style="font-size:12px; padding:6px 12px;" onclick="toggleTheaterMode()">⛶ อ่านเต็มจอ</button>
                            </div>
                        </div>
                        <div style="width:100%; background:#1e293b; border-radius:999px; height:8px; margin-top:12px; overflow:hidden;">
                            <div id="progressBarFill" style="width:0%; background:linear-gradient(90deg, #3b82f6, #38bdf8); height:100%; transition:width 0.3s;"></div>
                        </div>
                    </div>

                    <!-- Reader Controls Bar -->
                    <div class="card" style="padding:10px 18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:16px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:13px; font-weight:600; color:#cbd5e1;">📱 จัดวางหน้า:</span>
                            <button id="btnModeSeamless" class="btn btn-success" style="font-size:12px; padding:5px 12px;" onclick="setReaderMode('seamless')">เว็บตูนไร้รอยต่อ</button>
                            <button id="btnModeCard" class="btn btn-outline" style="font-size:12px; padding:5px 12px;" onclick="setReaderMode('card')">การ์ดแยกหน้า</button>
                        </div>
                        <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
                            <label style="display:flex; align-items:center; gap:6px; cursor:pointer; font-size:12px; color:#38bdf8; font-weight:600;" title="คลิกครึ่งบนเพื่อเลื่อนขึ้น / คลิกครึ่งล่างเพื่อเลื่อนลง">
                                <input type="checkbox" id="clickScrollCheck" checked onchange="toggleClickScroll(this.checked)">
                                🖱️ คลิกขึ้น-ลง (บน/ล่าง)
                            </label>
                            <div style="display:flex; gap:6px;">
                                <button class="btn btn-outline" style="font-size:11px; padding:4px 8px;" onclick="scrollUpStep()" title="เลื่อนขึ้น 1 หน้าจอ (ArrowUp / K)">▲ เลื่อนขึ้น</button>
                                <button class="btn btn-outline" style="font-size:11px; padding:4px 8px;" onclick="scrollDownStep()" title="เลื่อนลง 1 หน้าจอ (ArrowDown / J / Space)">▼ เลื่อนลง</button>
                                <button id="btnAutoScroll" class="btn btn-outline" style="font-size:11px; padding:4px 8px;" onclick="toggleAutoScroll()" title="เลื่อนอ่านอัตโนมัติ">▶ ออโต้สกรอลล์</button>
                            </div>
                        </div>
                        <div style="display:flex; align-items:center; gap:10px;">
                            <span style="font-size:13px; color:#cbd5e1;">🔍 ขนาดความกว้าง:</span>
                            <input type="range" id="widthSlider" min="550" max="1050" value="780" step="20" oninput="changeReaderWidth(this.value)">
                            <span id="widthValueLabel" style="font-size:12px; color:var(--accent-cyan); width:50px; font-weight:600;">780px</span>
                        </div>
                    </div>

                    <!-- Centered Webtoon Stream Container -->
                    <div id="readerStreamWrapper">
                        <div id="pagesContainer"></div>
                    </div>
                </div>
            </div>

            <!-- Floating Side Navigation Buttons -->
            <div id="floatingSideNav" style="position:fixed; right:20px; top:50%; transform:translateY(-50%); display:flex; flex-direction:column; gap:8px; z-index:90;">
                <button class="btn btn-outline" style="border-radius:50%; width:44px; height:44px; padding:0; display:flex; align-items:center; justify-content:center; font-size:18px; background:rgba(15,23,42,0.85); backdrop-filter:blur(8px); box-shadow:0 4px 15px rgba(0,0,0,0.5);" onclick="scrollUpStep()" title="เลื่อนขึ้น 1 หน้าจอ">▲</button>
                <button id="floatingSideAuto" class="btn btn-outline" style="border-radius:50%; width:44px; height:44px; padding:0; display:flex; align-items:center; justify-content:center; font-size:13px; background:rgba(15,23,42,0.85); backdrop-filter:blur(8px); box-shadow:0 4px 15px rgba(0,0,0,0.5);" onclick="toggleAutoScroll()" title="เลื่อนอ่านอัตโนมัติ">▶</button>
                <button class="btn btn-outline" style="border-radius:50%; width:44px; height:44px; padding:0; display:flex; align-items:center; justify-content:center; font-size:18px; background:rgba(15,23,42,0.85); backdrop-filter:blur(8px); box-shadow:0 4px 15px rgba(0,0,0,0.5);" onclick="scrollDownStep()" title="เลื่อนลง 1 หน้าจอ">▼</button>
            </div>

            <!-- ================= CATEGORY 2: FONTS & SETTINGS ================= -->
            <div id="tab-settings" class="tab-content" style="display:none;">
                <!-- Live Interactive Sandbox Card -->
                <div class="card" style="border:1px solid #6366f1;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:16px;">
                        <h2 style="margin:0; font-size:18px; display:flex; align-items:center; gap:8px;">
                            <span>🎮</span> กล่องทดลองปรับแต่งสด (Live Interactive Sandbox)
                        </h2>
                        <span class="badge" style="background:#1e3a8a; color:#bfdbfe;">อัปเดตตัวอย่างแบบเรียลไทม์</span>
                    </div>
                    <p style="color:var(--text-muted); font-size:13px; margin-top:0;">
                        ปรับแต่งฟอนต์ บอลลูนคำพูด และโทนสำนวน แล้วดูผลลัพธ์ที่จะใช้ในโหมดอ่านมังงะได้ทันที:
                    </p>

                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px; margin-bottom:16px;">
                        <div>
                            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">🎨 เลือกฟอนต์:</label>
                            <select id="sandboxFontSelect" class="input-text" style="width:100%;" onchange="updateLivePreview()">
                                <option value="mali" selected>✍️ Mali Comic (ลายเส้นมังงะแท้ [แนะนำ])</option>
                                <option value="kanit">⚔️ Kanit Shonen (แอ็กชันดุดัน)</option>
                                <option value="chakrapetch">🎮 Chakra Petch (กล่องเควสต์ระบบ)</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">✨ สไตล์บอลลูนคำพูด:</label>
                            <select id="sandboxBackdropSelect" class="input-text" style="width:100%;" onchange="updateLivePreview()">
                                <option value="natural" selected>🎨 ลายเส้นมังงะแท้ (ขอบมน คมชัด)</option>
                                <option value="soft_white">⚪ รองพื้นขาวนุ่มนวล</option>
                                <option value="dark_box">⬛ กล่องดำสไตล์ระบบเกม</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">🎭 โทนสำนวนการ์ตูน:</label>
                            <select id="sandboxToneSelect" class="input-text" style="width:100%;" onchange="updateLivePreview()">
                                <option value="shonen" selected>⚔️ โชเน็น (แก, ข้า, ลุย!)</option>
                                <option value="shojo">🌸 ตาหวาน (นาย, ฉัน, ละมุน)</option>
                                <option value="seinen">🕵️ สุขุม / สืบสวน (จริงจัง ลุ่มลึก)</option>
                                <option value="comedy">🤣 การ์ตูนแก๊ก (ฮาๆ กวนๆ)</option>
                            </select>
                        </div>
                    </div>

                    <div style="margin-bottom:16px;">
                        <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">✍️ ลองพิมพ์ข้อความของคุณเอง (จะแสดงในบอลลูนทันที):</label>
                        <input type="text" id="sandboxCustomText" class="input-text" style="width:100%;" 
                               placeholder="พิมพ์ข้อความทดสอบที่นี่... (เช่น เฮ้ย! รอก่อนสิฟะ!)" oninput="updateLivePreview()">
                    </div>

                    <!-- Live Bubble Sandbox Display -->
                    <div id="sandboxBubbleDisplay" style="background:#ffffff; color:#0f172a; padding:28px; border-radius:24px; border:3px solid #334155; text-align:center; min-height:110px; display:flex; align-items:center; justify-content:center; box-shadow:0 8px 30px rgba(0,0,0,0.6); transition:all 0.3s ease;">
                        <div id="sandboxBubbleText" style="font-family:'Mali', cursive; font-size:20px; font-weight:700; line-height:1.4;">
                            "เฮ้ย! รอก่อนสิฟะ!<br>อย่าเพิ่งไปทางนั้นนะโว้ย!"
                        </div>
                    </div>
                </div>

                <!-- Font Showcase Cards -->
                <div class="card">
                    <h2 style="margin-top:0; font-size:18px;">🎨 แกลเลอรีฟอนต์ระดับพรีเมียม (Font Showcase)</h2>
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:18px; margin-top:16px;">
                        <div style="background:#090d16; border:1px solid #334155; border-radius:12px; padding:18px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <b style="color:#6ee7b7; font-size:15px;">1. Mali Comic (ลายเส้นมังงะ)</b>
                                <span class="badge" style="background:#064e3b; color:#a7f3d0;">ยอดนิยม</span>
                            </div>
                            <p style="color:var(--text-muted); font-size:13px; margin:8px 0 14px;">
                                โค้งมน เป็นธรรมชาติ ถ่ายทอดอารมณ์เหมือนอ่านรวมเล่มภาษาไทย
                            </p>
                            <div style="background:#fff; color:#0f172a; padding:14px; border-radius:16px; text-align:center;">
                                <div style="font-family:'Mali', cursive; font-size:17px; font-weight:700;">"รอเดี๋ยวสิ! ฉันยังไม่ได้เริ่มเลยนะ!"</div>
                            </div>
                        </div>
                        <div style="background:#090d16; border:1px solid #334155; border-radius:12px; padding:18px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <b style="color:#60a5fa; font-size:15px;">2. Kanit Shonen (แอ็กชันดุดัน)</b>
                                <span class="badge" style="background:#1e3a8a; color:#bfdbfe;">มันฮวาต่อสู้</span>
                            </div>
                            <p style="color:var(--text-muted); font-size:13px; margin:8px 0 14px;">
                                ตัวหนา คมชัด สไตล์มันฮวาเกาหลีแอ็กชัน (Solo Leveling, Overgeared)
                            </p>
                            <div style="background:#fff; color:#0f172a; padding:14px; border-radius:16px; text-align:center;">
                                <div style="font-family:'Kanit', sans-serif; font-size:17px; font-weight:700;">"ข้าจะไม่ยอมแพ้ที่นี่เด็ดขาด!"</div>
                            </div>
                        </div>
                        <div style="background:#090d16; border:1px solid #334155; border-radius:12px; padding:18px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <b style="color:#fcd34d; font-size:15px;">3. Chakra Petch (กล่องระบบเกม)</b>
                                <span class="badge" style="background:#451a03; color:#fde68a;">เควสต์ & สเตตัส</span>
                            </div>
                            <p style="color:var(--text-muted); font-size:13px; margin:8px 0 14px;">
                                ดิจิทัลไซเบอร์ สไตล์หน้าต่างสเตตัสและข้อความเควสต์
                            </p>
                            <div style="background:#0b1221; color:#38bdf8; padding:14px; border-radius:10px; border:2px solid #38bdf8; text-align:center;">
                                <div style="font-family:'Chakra Petch', sans-serif; font-size:15px; font-weight:700;">[ เควสต์สำเร็จ : ได้รับดาบแห่งราชา ]</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Tone Comparisons -->
                <div class="card">
                    <h2 style="margin-top:0; font-size:18px;">🎭 เทียบสำนวนมังงะแท้ (Natural AI) vs แปลตรงตัวแข็งทื่อ</h2>
                    <div style="display:flex; flex-direction:column; gap:14px; margin-top:14px;">
                        <div class="step-card">
                            <b>Overgeared ตอน 343: ข้อความเควสต์ระบบ</b>
                            <div style="margin-top:4px; color:#cbd5e1; font-size:13px;">QUEST CLEAR CONDITIONS: GIVE THE NECESSARY HELP TO 5,000 CITIZENS</div>
                            <div style="margin-top:8px; color:#6ee7b7; font-weight:600;">✅ สำนวนมังงะ: "เงื่อนไขการเคลียร์ภารกิจ: มอบความช่วยเหลือแก่ประชาชน 5,000 คน!"</div>
                            <div style="margin-top:4px; color:#f87171; font-size:12px;">❌ แปลตรงตัวดั้งเดิม: "เงื่อนไขที่ชัดเจนในการค้นหา: ให้ความช่วยเหลือที่จำเป็นแก่พลเมือง 5,000 คน"</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ================= CATEGORY 3: IPHONE / IPAD ================= -->
            <div id="tab-ios" class="tab-content" style="display:none;">
                <!-- Fast 3 Methods for iPhone -->
                <div class="card" style="border-color:#ec4899;">
                    <h2 style="margin-top:0; font-size:18px; display:flex; align-items:center; gap:8px;">
                        <span>📱</span> 3 วิธีใช้งานบน iPhone ที่ง่ายที่สุด (เลือกวิธีที่สะดวกได้เลย)
                    </h2>
                    <p style="color:var(--text-muted); font-size:13px; line-height:1.6;">
                        ไม่ต้องเปิดคอมทิ้งไว้ ระบบคลาวด์ทำงาน 24 ชั่วโมงฟรี! บน iPhone คุณสามารถเลือกแปลได้ 3 รูปแบบตามความสะดวก:
                    </p>

                    <!-- Method 1: Copy Image & 1-Tap Paste -->
                    <div style="background:#13112c; border:1px solid #a855f7; border-radius:12px; padding:16px; margin-top:14px;">
                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                            <span style="background:#ec4899; color:white; font-size:12px; font-weight:800; padding:2px 8px; border-radius:6px;">วิธีที่ 1 (ง่ายสุด 0 การตั้งค่า)</span>
                            <b style="color:#f472b6; font-size:15px;">แตะค้างที่รูปในเว็บมังงะ ➡️ คัดลอก ➡️ วางแปลทันที</b>
                        </div>
                        <p style="color:#cbd5e1; font-size:13px; line-height:1.6; margin:0 0 10px;">
                            เวลาเปิดอ่านมังงะใน Safari แล้วเจอหน้าที่อยากอ่านเป็นภาษาไทย:
                        </p>
                        <ol style="color:#94a3b8; font-size:12px; line-height:1.8; margin:0; padding-left:20px;">
                            <li><b>แตะค้างที่รูปภาพมังงะ</b> ใน Safari ➡️ แตะเลือก <b>"คัดลอก (Copy)"</b></li>
                            <li>สลับมาที่หน้า MangaThaiAI นี้ ➡️ แตะปุ่มสีชมพู <b>"📋 วางภาพจากคลิปบอร์ด iPhone"</b></li>
                            <li>AI แปลงตัวหนังสือเกาหลี/ญี่ปุ่น เป็นภาษาไทย 18+ ฟอนต์การ์ตูนให้ทันทีใน 1-2 วินาที!</li>
                        </ol>
                    </div>

                    <!-- Method 2: Safari 1-Second Shortcut ("แปล") -->
                    <div style="background:#09192c; border:1px solid #0284c7; border-radius:12px; padding:16px; margin-top:14px;">
                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                            <span style="background:#0284c7; color:white; font-size:12px; font-weight:800; padding:2px 8px; border-radius:6px;">วิธีที่ 2 (แปลทั้งตอน 89 หน้า)</span>
                            <b style="color:#38bdf8; font-size:15px;">สูตรลัด Safari: พิมพ์คำว่า "แปล" ในช่อง URL</b>
                        </div>
                        <p style="color:#cbd5e1; font-size:13px; line-height:1.6; margin:0 0 10px;">
                            เปิดเว็บมังงะใดๆ ใน Safari (เช่น NewXtoon) แล้วแปลไทยได้ทันทีทั้ง 89 หน้าโดยไม่ต้องออกจากหน้าเว็บ:
                        </p>
                        <div style="background:#0b1329; border:1px dashed #38bdf8; border-radius:8px; padding:14px; text-align:center; margin-bottom:10px;">
                            <button class="btn btn-primary" style="font-size:14px; padding:10px 20px;" onclick="copyBookmarkletCode()">
                                📋 1. กดที่นี่เพื่อคัดลอกโค้ด Bookmarklet
                            </button>
                            <div style="font-size:11px; color:#94a3b8; margin-top:8px;">
                                2. ใน Safari: บุ๊กมาร์กหน้านี้ไว้ ➡️ กดแก้ไข (Edit) ➡️ ตั้งชื่อว่า <b>แปล</b> ➡️ วางโค้ดลงในช่อง URL
                            </div>
                        </div>
                        <div style="font-size:12px; color:#6ee7b7; background:#064e3b; padding:8px 12px; border-radius:6px; line-height:1.5;">
                            ✨ <b>วิธีใช้จริง:</b> เวลาอ่านมังงะใน Safari แตะที่ช่องพิมพ์ URL ด้านล่าง ➡️ พิมพ์คำว่า <b>แปล</b> ➡️ แตะที่บุ๊กมาร์ก แถบแปลภาษาจะลอยขึ้นมาแปลทั้ง 89 หน้าทันที!
                        </div>
                    </div>

                    <!-- Method 3: PWA Add to Home Screen -->
                    <div style="background:#0d1b1e; border:1px solid #059669; border-radius:12px; padding:16px; margin-top:14px;">
                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                            <span style="background:#059669; color:white; font-size:12px; font-weight:800; padding:2px 8px; border-radius:6px;">วิธีที่ 3 (แอปเต็มจอ)</span>
                            <b style="color:#34d399; font-size:15px;">ติดตั้งเป็นแอปเต็มจอ (Add to Home Screen)</b>
                        </div>
                        <p style="color:#94a3b8; font-size:13px; line-height:1.6; margin:0;">
                            แตะไอคอน <b>แชร์ (สี่เหลี่ยมลูกศรชี้ขึ้น ⬆️)</b> ที่แถบเมนู Safari ➡️ เลื่อนลงเลือก <b>"เพิ่มไปยังหน้าจอโฮม (Add to Home Screen)"</b> ➡️ กด Add จะได้ไอคอนแอปบนหน้าจอมือถือ เปิดอ่านได้เต็มจอไร้ขอบ Safari
                        </p>
                    </div>
                </div>

                <!-- Mobile Touch Gestures -->
                <div class="card">
                    <h2 style="margin-top:0; font-size:18px;">👆 เคล็ดลับการควบคุมบนหน้าจอสัมผัส (Touch Navigation)</h2>
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:14px; margin-top:14px;">
                        <div class="step-card">
                            <b style="color:#38bdf8;">▲ แตะครึ่งบนของจอ</b>
                            <p style="color:#94a3b8; font-size:13px; margin:4px 0 0;">เลื่อนขึ้น 1 หน้าจออัตโนมัติ ไม่ต้องคอยปัดนิ้วบ่อยๆ</p>
                        </div>
                        <div class="step-card">
                            <b style="color:#38bdf8;">▼ แตะครึ่งล่างของจอ</b>
                            <p style="color:#94a3b8; font-size:13px; margin:4px 0 0;">เลื่อนลง 1 หน้าจอ เหมาะสำหรับการอ่านตอนนอนหรือมือเดียว</p>
                        </div>
                        <div class="step-card">
                            <b style="color:#38bdf8;">▶ ปุ่มออโต้สกรอลล์</b>
                            <p style="color:#94a3b8; font-size:13px; margin:4px 0 0;">ให้หน้าเว็บค่อยๆ ไหลลงมาแบบสบายตา ปรับความเร็วได้</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ================= CATEGORY 4: SELF-DEPLOY GUIDE ================= -->
            <div id="tab-deploy" class="tab-content" style="display:none;">
                <!-- Deploy Overview -->
                <div class="card" style="border:1px solid #10b981;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:14px;">
                        <h2 style="margin:0; font-size:18px; display:flex; align-items:center; gap:8px;">
                            <span>🚀</span> วิธี Deploy และอัปเดตระบบด้วยตนเอง (Self-Deploy Architecture)
                        </h2>
                        <span class="badge" style="background:#064e3b; color:#a7f3d0;">ฟรี 100% ตลอดชีพ</span>
                    </div>
                    <p style="color:var(--text-muted); font-size:13px; line-height:1.6; margin-top:0;">
                        ระบบ MangaThaiAI-Studio ถูกออกแบบมาให้ Deploy และอัปเดตง่ายที่สุดแบบ <b>Zero-Maintenance</b> ทุกครั้งที่คุณแก้ไขโค้ดหรือต้องการอัปเดต แค่ดับเบิ้ลคลิกไฟล์เดียว ระบบคลาวด์จะซิงก์ให้อัตโนมัติ:
                    </p>

                    <!-- 4-Step Pipeline Flow -->
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:16px; margin-top:18px;">
                        <div class="step-card">
                            <div style="display:flex; align-items:center; margin-bottom:8px;">
                                <span class="step-badge" style="background:#3b82f6;">1</span>
                                <b style="color:#fff; font-size:15px;">แก้ไขโค้ดในเครื่อง</b>
                            </div>
                            <p style="color:#94a3b8; font-size:13px; line-height:1.6; margin:0;">
                                ทำงานหรือปรับแต่งไฟล์ในโฟลเดอร์ <code>D:\code\MangaThaiAI-Studio</code> ได้ตามต้องการ
                            </p>
                        </div>
                        <div class="step-card">
                            <div style="display:flex; align-items:center; margin-bottom:8px;">
                                <span class="step-badge" style="background:#10b981;">2</span>
                                <b style="color:#fff; font-size:15px;">ดับเบิ้ลคลิก push_to_github.bat</b>
                            </div>
                            <p style="color:#94a3b8; font-size:13px; line-height:1.6; margin:0;">
                                ดับเบิ้ลคลิกไฟล์ <code>push_to_github.bat</code> ในโฟลเดอร์โปรเจกต์ สคริปต์จะ commit และ push ขึ้น GitHub ให้อัตโนมัติใน 3 วินาที
                            </p>
                        </div>
                        <div class="step-card">
                            <div style="display:flex; align-items:center; margin-bottom:8px;">
                                <span class="step-badge" style="background:#8b5cf6;">3</span>
                                <b style="color:#fff; font-size:15px;">GitHub ซิงก์ Webhook</b>
                            </div>
                            <p style="color:#94a3b8; font-size:13px; line-height:1.6; margin:0;">
                                โค้ดจะถูกเก็บไว้ที่ GitHub <code>chaiyasitpiw-ops/MangaThaiAI-Studio</code> และส่งสัญญาณไปยัง Render.com
                            </p>
                        </div>
                        <div class="step-card">
                            <div style="display:flex; align-items:center; margin-bottom:8px;">
                                <span class="step-badge" style="background:#ec4899;">4</span>
                                <b style="color:#fff; font-size:15px;">Render Auto-Deploy</b>
                            </div>
                            <p style="color:#94a3b8; font-size:13px; line-height:1.6; margin:0;">
                                Render จะดึง Dockerfile ไปบิลด์และรันเซิร์ฟเวอร์บนคลาวด์ใหม่อัตโนมัติ (1-2 นาที) พร้อมใช้ได้ทุกที่ทั่วโลก!
                            </p>
                        </div>
                    </div>
                </div>

                <!-- Live Health & Server Links -->
                <div class="card">
                    <h2 style="margin-top:0; font-size:18px;">🔍 ตรวจสอบสถานะเซิร์ฟเวอร์คลาวด์สด (Live Status)</h2>
                    <div style="display:flex; align-items:center; gap:12px; margin-top:14px; flex-wrap:wrap;">
                        <button class="btn btn-outline" onclick="checkLiveServerHealth()" style="font-size:13px;">
                            ⚡ กดเพื่อตรวจสอบการเชื่อมต่อเซิร์ฟเวอร์สด
                        </button>
                        <span id="healthStatusResult" style="font-size:13px; color:#94a3b8;">กดปุ่มเพื่อทดสอบ</span>
                    </div>

                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:14px; margin-top:18px; padding-top:18px; border-top:1px solid #1e293b;">
                        <div>
                            <span style="font-size:12px; color:var(--text-muted);">🌐 ลิงก์เว็บแอปบนคลาวด์ (ใช้งานได้ทุกเครื่อง):</span>
                            <div style="margin-top:4px;">
                                <a href="https://mangathaiai-studio.onrender.com" target="_blank" style="color:#38bdf8; font-weight:600; text-decoration:none;">
                                    👉 https://mangathaiai-studio.onrender.com ↗
                                </a>
                            </div>
                        </div>
                        <div>
                            <span style="font-size:12px; color:var(--text-muted);">☁️ แดชบอร์ด Render.com:</span>
                            <div style="margin-top:4px;">
                                <a href="https://dashboard.render.com" target="_blank" style="color:#a78bfa; font-weight:600; text-decoration:none;">
                                    👉 https://dashboard.render.com ↗
                                </a>
                            </div>
                        </div>
                        <div>
                            <span style="font-size:12px; color:var(--text-muted);">🐙 GitHub Repository ซอร์สโค้ด:</span>
                            <div style="margin-top:4px;">
                                <a href="https://github.com/chaiyasitpiw-ops/MangaThaiAI-Studio" target="_blank" style="color:#34d399; font-weight:600; text-decoration:none;">
                                    👉 github.com/chaiyasitpiw-ops/MangaThaiAI-Studio ↗
                                </a>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Explanation of Fixed Errors -->
                <div class="card">
                    <h2 style="margin-top:0; font-size:18px;">💡 สาเหตุข้อผิดพลาดที่เกิดขึ้นก่อนหน้านี้ & ได้รับการแก้ไขแล้ว</h2>
                    <div style="display:flex; flex-direction:column; gap:12px; margin-top:14px;">
                        <div class="step-card">
                            <b style="color:#fbbf24;">1. จอดำขึ้น "'in' is not recognized..." และ "'หั สผ าน' is not recognized..."</b>
                            <p style="color:#94a3b8; font-size:13px; line-height:1.6; margin:6px 0 0;">
                                <b>สาเหตุ:</b> เกิดจาก Windows CMD อ่าน encoding ภาษาไทยในไฟล์ batch ไม่ถูกต้อง ทำให้แยกคำสั่งผิดพลาด<br>
                                <b>การแก้ไข:</b> เราได้เขียนสคริปต์ <code>push_to_github.bat</code> ใหม่เป็นคำสั่ง ASCII บริสุทธิ์ 100% ทำให้รันได้เสถียร ไม่ขึ้น error อีกต่อไป
                            </p>
                        </div>
                        <div class="step-card">
                            <b style="color:#fbbf24;">2. Render Log แจ้ง "ModuleNotFoundError: No module named 'bs4'"</b>
                            <p style="color:#94a3b8; font-size:13px; line-height:1.6; margin:6px 0 0;">
                                <b>สาเหตุ:</b> ใน Dockerfile ขาดแพ็กเกจ <code>beautifulsoup4</code> ที่ใช้ดึงรูปมังงะจากหน้าเว็บ<br>
                                <b>การแก้ไข:</b> เราได้ใส่ <code>beautifulsoup4>=4.12.0</code> และ <code>lxml>=5.1.0</code> เข้าไปใน requirements และ push ขึ้น GitHub แล้ว ตอนนี้ Render บิลด์ผ่านฉลุยและออนไลน์ 100%
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Mobile Bottom Navigation Dock (iPhone / iPad / Mobile Screens) -->
        <div class="mobile-bottom-nav">
            <button class="mobile-nav-btn active" data-tab="tab-webreader" onclick="switchTab('tab-webreader')">
                <span class="mobile-nav-icon">📖</span>
                <span>อ่านมังงะ</span>
            </button>
            <button class="mobile-nav-btn" data-tab="tab-settings" onclick="switchTab('tab-settings')">
                <span class="mobile-nav-icon">🎨</span>
                <span>ปรับแต่ง</span>
            </button>
            <button class="mobile-nav-btn" data-tab="tab-ios" onclick="switchTab('tab-ios')">
                <span class="mobile-nav-icon">📱</span>
                <span>iPhone</span>
            </button>
            <button class="mobile-nav-btn" data-tab="tab-deploy" onclick="switchTab('tab-deploy')">
                <span class="mobile-nav-icon">🚀</span>
                <span>Deploy</span>
            </button>
        </div>

        <!-- Floating Glass Theater HUD -->
        <div id="floatingTheaterHud" class="floating-hud" style="display:none;">
            <span id="floatingHudStatus" style="font-size:13px; font-weight:600; color:#cbd5e1;">หน้า 0/0</span>
            <div style="height:16px; width:1px; background:#334155;"></div>
            <button class="btn btn-outline" style="font-size:12px; padding:4px 10px;" onclick="scrollToTop()">⬆ บนสุด</button>
            <button class="btn btn-theater" style="font-size:12px; padding:4px 10px;" onclick="toggleTheaterMode()">⛶ สลับโหมด</button>
        </div>

        <script>
            let fetchedWebImages = [];
            let currentReaderMode = 'seamless';
            let isPaused = false;
            let timerInterval = null;
            let startTime = 0;
            let translatedCount = 0;
            let isTheaterMode = false;
            let systemEnabled = true;

            // ── System Power Toggle ──────────────────────────────────────
            function toggleSystemPower(enabled) {
                systemEnabled = enabled;
                const dot = document.getElementById('powerDot');
                const label = document.getElementById('powerLabel');
                const toggle = document.getElementById('powerToggle');
                if (enabled) {
                    dot.classList.remove('off');
                    label.innerText = 'ระบบ: เปิด';
                    toggle.style.borderColor = '#334155';
                    showNotification('⚡ ระบบแปลมังงะเปิดใช้งานแล้ว', 'success');
                } else {
                    dot.classList.add('off');
                    label.innerText = 'ระบบ: ปิด';
                    toggle.style.borderColor = '#ef4444';
                    showNotification('⏸ ระบบแปลมังงะหยุดชั่วคราวแล้ว', 'warning');
                }
            }

            function showNotification(msg, type) {
                const n = document.createElement('div');
                n.style.cssText = `position:fixed;top:70px;right:20px;z-index:9999;padding:10px 16px;border-radius:10px;font-size:13px;font-weight:600;font-family:'Prompt',sans-serif;box-shadow:0 4px 20px rgba(0,0,0,0.5);transition:all 0.3s;opacity:0;transform:translateX(20px);`;
                n.style.background = type === 'success' ? '#064e3b' : '#451a03';
                n.style.color = type === 'success' ? '#6ee7b7' : '#fde68a';
                n.style.border = `1px solid ${type === 'success' ? '#10b981' : '#f59e0b'}`;
                n.innerText = msg;
                document.body.appendChild(n);
                setTimeout(() => { n.style.opacity = '1'; n.style.transform = 'translateX(0)'; }, 10);
                setTimeout(() => { n.style.opacity = '0'; setTimeout(() => n.remove(), 300); }, 2500);
            }

            function copyBookmarkletCode() {
                const origin = window.location.origin;
                const code = `javascript:(function(){var s=document.createElement('script');s.src='${origin}/static/bookmarklet.js?t='+Date.now();document.body.appendChild(s);})();`;
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(code).then(() => {
                        showNotification('📋 คัดลอกโค้ด Bookmarklet สำเร็จ! นำไปวางในช่อง URL ของ Safari ได้เลย', 'success');
                    }).catch(() => {
                        prompt('คัดลอกโค้ด Bookmarklet สำหรับ Safari:', code);
                    });
                } else {
                    prompt('คัดลอกโค้ด Bookmarklet สำหรับ Safari:', code);
                }
            }

            // Anti-Gambling Popup Shield - allow user-initiated window opens
            const _nativeWindowOpen = window.open ? window.open.bind(window) : null;
            function safeOpenUrl(url) {
                if (!url) return;
                const a = document.createElement('a');
                a.href = url;
                a.target = '_blank';
                a.rel = 'noopener noreferrer';
                document.body.appendChild(a);
                a.click();
                setTimeout(() => a.remove(), 100);
            }

            let isClickScrollEnabled = true;
            function toggleClickScroll(enabled) {
                isClickScrollEnabled = enabled;
            }

            function scrollUpStep() {
                window.scrollBy({ top: -window.innerHeight * 0.78, behavior: 'smooth' });
            }

            function scrollDownStep() {
                window.scrollBy({ top: window.innerHeight * 0.78, behavior: 'smooth' });
            }

            let autoScrollTimer = null;
            let autoScrollSpeed = 2;
            function toggleAutoScroll() {
                const btn = document.getElementById('btnAutoScroll');
                const fBtn = document.getElementById('floatingSideAuto');
                if (autoScrollTimer) {
                    clearInterval(autoScrollTimer);
                    autoScrollTimer = null;
                    if (btn) { btn.innerText = '▶ ออโต้สกรอลล์'; btn.classList.remove('btn-success'); }
                    if (fBtn) { fBtn.innerText = '▶'; fBtn.classList.remove('btn-success'); }
                } else {
                    autoScrollTimer = setInterval(() => {
                        window.scrollBy(0, autoScrollSpeed);
                    }, 25);
                    if (btn) { btn.innerText = '⏸ หยุดเลื่อน'; btn.classList.add('btn-success'); }
                    if (fBtn) { fBtn.innerText = '⏸'; fBtn.classList.add('btn-success'); }
                }
            }

            // Click-to-Scroll Event Handler
            document.addEventListener('click', function(e) {
                if (!isClickScrollEnabled) return;
                if (e.target.closest('button, input, select, a, .page-floating-bar, .floating-hud, #floatingSideNav, header, .card, .mobile-bottom-nav')) {
                    return;
                }
                const y = e.clientY;
                const winH = window.innerHeight;
                if (y < winH * 0.40) {
                    scrollUpStep();
                } else if (y > winH * 0.60) {
                    scrollDownStep();
                }
            });

            // Keyboard Navigation
            document.addEventListener('keydown', function(e) {
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
                if (e.key === 'ArrowDown' || e.key === 'j' || e.key === 'J' || e.key === 'PageDown' || (e.key === ' ' && !e.shiftKey)) {
                    e.preventDefault();
                    scrollDownStep();
                } else if (e.key === 'ArrowUp' || e.key === 'k' || e.key === 'K' || e.key === 'PageUp' || (e.key === ' ' && e.shiftKey)) {
                    e.preventDefault();
                    scrollUpStep();
                }
            });

            // Switch Category Tabs (Both Top Tabs and Bottom Mobile Dock)
            function switchTab(tabId) {
                document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                document.querySelectorAll('.mobile-nav-btn').forEach(btn => btn.classList.remove('active'));
                
                const target = document.getElementById(tabId);
                if (target) {
                    target.style.display = 'block';
                }
                
                document.querySelectorAll(`[data-tab="${tabId}"]`).forEach(btn => btn.classList.add('active'));
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }

            function toggleHtmlPasteDrawer() {
                const el = document.getElementById('htmlPasteDrawer');
                el.style.display = (el.style.display === 'none') ? 'block' : 'none';
            }

            function extractAndReadFromPastedHtml() {
                const raw = document.getElementById('rawHtmlInput').value.trim();
                if (!raw) {
                    alert('กรุณาวางโค้ด HTML หรือลิงก์รูปภาพก่อนครับ');
                    return;
                }

                const seen = new Set();
                const urls = [];

                // 1. Keyword-based extraction for manga chapter images
                const re = /https?:\/\/[^\s'"<>]+\.(?:webp|jpg|jpeg|png)(?:\?[^\s'"<>]*)?/gi;
                let m;
                while ((m = re.exec(raw)) !== null) {
                    const u = m[0];
                    const uLow = u.toLowerCase();
                    if (!seen.has(u) && !uLow.includes('/ads/') && !uLow.includes('avatar') && !uLow.includes('banner') && !uLow.includes('logo') && !uLow.includes('icon')) {
                        if (uLow.includes('chapter') || uLow.includes('quicksharefiles') || uLow.includes('comic') || uLow.includes('manga') || uLow.includes('storage') || uLow.includes('cdn')) {
                            seen.add(u);
                            urls.push(u);
                        }
                    }
                }

                // 2. Fallback: if no keyword matches, accept all non-ad image URLs
                if (urls.length === 0) {
                    re.lastIndex = 0;
                    while ((m = re.exec(raw)) !== null) {
                        const u = m[0];
                        const uLow = u.toLowerCase();
                        if (!seen.has(u) && !uLow.includes('/ads/') && !uLow.includes('avatar') && !uLow.includes('banner')) {
                            seen.add(u);
                            urls.push(u);
                        }
                    }
                }

                if (urls.length > 0) {
                    fetchedWebImages = urls;
                    const inspectCard = document.getElementById('chapterInspectorCard');
                    const inspectTitle = document.getElementById('inspectTitle');
                    const inspectSubtitle = document.getElementById('inspectSubtitle');
                    const inspectPageCount = document.getElementById('inspectPageCount');
                    const inspectPageCountBtn = document.getElementById('inspectPageCountBtn');

                    inspectCard.style.display = 'block';
                    inspectTitle.innerText = 'สกัดรูปภาพจากโค้ด HTML สำเร็จ';
                    inspectPageCount.innerText = urls.length;
                    inspectPageCountBtn.innerText = urls.length;
                    inspectSubtitle.innerHTML = `✅ สกัดรูปภาพตอนมังงะได้ทั้งหมด <b style="color:#34d399; font-size:15px;">${urls.length}</b> หน้า พร้อมแปลทันที!`;
                    showNotification(`✅ สกัดรูปภาพได้ ${urls.length} หน้าจากโค้ด HTML!`, 'success');
                    renderPagesIntoReader(urls);
                    document.getElementById('webReaderSection').style.display = 'block';
                    document.getElementById('htmlPasteDrawer').style.display = 'none';
                    if (document.getElementById('autoTranslateCheck').checked) {
                        startBatchTranslation();
                    }
                } else {
                    alert('ไม่พบรูปภาพมังงะในข้อความที่วาง กรุณาตรวจสอบว่ามีแท็ก <img> หรือลิงก์รูปภาพ .webp / .jpg');
                }
            }

            function loadQuickUrl(type) {
                const input = document.getElementById('webUrlInput');
                switchTab('tab-webreader');
                if (type === 'newxtoon_18') {
                    input.value = 'https://newxtoon5.com/comics/17962/chapters/1080367';
                    document.getElementById('globalToneSelect').value = 'adult_18';
                    document.getElementById('sourceLangSelect').value = 'kr';
                    checkAllWebtoonPages();
                } else if (type === 'newxtoon') {
                    input.value = 'https://newxtoon5.com/comics/17962/chapters/1080367';
                    document.getElementById('globalToneSelect').value = 'adult_18';
                    document.getElementById('sourceLangSelect').value = 'kr';
                    checkAllWebtoonPages();
                } else if (type === 'overgeared') {
                    input.value = 'https://asurascans.com/comics/overgeared-1bb35e56/chapter/343';
                    document.getElementById('sourceLangSelect').value = 'en';
                    checkAllWebtoonPages();
                } else if (type === 'sololeveling') {
                    input.value = 'https://asurascans.com/comics/solo-leveling/chapter/1';
                    document.getElementById('sourceLangSelect').value = 'en';
                    checkAllWebtoonPages();
                } else if (type === 'onepiece') {
                    input.value = 'https://mangaplus.shueisha.co.jp/viewer/1000001';
                    document.getElementById('sourceLangSelect').value = 'en';
                    checkAllWebtoonPages();
                } else if (type === 'demo') {
                    input.value = window.location.origin + '/static/sample_manga.png';
                    checkAllWebtoonPages();
                }
            }

            function changeReaderWidth(val) {
                document.getElementById('readerStreamWrapper').style.maxWidth = val + 'px';
                document.getElementById('widthValueLabel').innerText = val + 'px';
            }

            function setReaderMode(mode) {
                currentReaderMode = mode;
                const pages = document.querySelectorAll('.webtoon-page');
                const btnSeamless = document.getElementById('btnModeSeamless');
                const btnCard = document.getElementById('btnModeCard');

                if (mode === 'seamless') {
                    btnSeamless.className = 'btn btn-success';
                    btnCard.className = 'btn btn-outline';
                    pages.forEach(p => {
                        p.style.marginBottom = '0';
                        p.style.borderRadius = '0';
                        p.style.border = 'none';
                    });
                } else {
                    btnSeamless.className = 'btn btn-outline';
                    btnCard.className = 'btn btn-success';
                    pages.forEach(p => {
                        p.style.marginBottom = '20px';
                        p.style.borderRadius = '8px';
                        p.style.border = '1px solid #334155';
                    });
                }
            }

            function toggleTheaterMode() {
                isTheaterMode = !isTheaterMode;
                if (isTheaterMode) {
                    document.body.classList.add('theater-mode');
                    document.getElementById('floatingTheaterHud').style.display = 'flex';
                } else {
                    document.body.classList.remove('theater-mode');
                    document.getElementById('floatingTheaterHud').style.display = 'none';
                }
            }

            function scrollToTop() {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }

            function onSettingChanged() {
                // Settings changed handler
            }

            // ── Live Interactive Sandbox Preview ─────────────────────────
            const tonePresetsText = {
                shonen: '"เฮ้ย! รอก่อนสิฟะ!<br>อย่าเพิ่งไปทางนั้นนะโว้ย!"',
                shojo: '"นี่... นายจะไปจริงๆ เหรอ?<br>ฉันยังไม่อยากให้ไปเลยนะ..."',
                seinen: '"ความจริงมีเพียงหนึ่งเดียวเท่านั้น...<br>และหลักฐานชิ้นนี้คือคำตอบ"',
                comedy: '"เดี๋ยวก่อนนะพี่ชาย!<br>ลืมรูดซิปกางเกงหรือเปล่าเนี่ย 555!"'
            };

            function updateLivePreview() {
                const font = document.getElementById('sandboxFontSelect').value;
                const backdrop = document.getElementById('sandboxBackdropSelect').value;
                const tone = document.getElementById('sandboxToneSelect').value;
                const custom = document.getElementById('sandboxCustomText').value.trim();

                const displayBox = document.getElementById('sandboxBubbleDisplay');
                const textBox = document.getElementById('sandboxBubbleText');

                if (font === 'mali') {
                    textBox.style.fontFamily = "'Mali', cursive";
                } else if (font === 'kanit') {
                    textBox.style.fontFamily = "'Kanit', sans-serif";
                } else if (font === 'chakrapetch') {
                    textBox.style.fontFamily = "'Chakra Petch', sans-serif";
                }

                if (backdrop === 'natural') {
                    displayBox.style.background = '#ffffff';
                    displayBox.style.color = '#0f172a';
                    displayBox.style.border = '3px solid #334155';
                    displayBox.style.borderRadius = '24px';
                    displayBox.style.boxShadow = '0 8px 30px rgba(0,0,0,0.6)';
                } else if (backdrop === 'soft_white') {
                    displayBox.style.background = 'rgba(255, 255, 255, 0.95)';
                    displayBox.style.color = '#0f172a';
                    displayBox.style.border = '2px dashed #94a3b8';
                    displayBox.style.borderRadius = '20px';
                    displayBox.style.boxShadow = '0 4px 15px rgba(255,255,255,0.1)';
                } else if (backdrop === 'dark_box') {
                    displayBox.style.background = '#0b1221';
                    displayBox.style.color = '#38bdf8';
                    displayBox.style.border = '2px solid #38bdf8';
                    displayBox.style.borderRadius = '10px';
                    displayBox.style.boxShadow = '0 0 25px rgba(56,189,248,0.35)';
                }

                if (custom) {
                    textBox.innerText = custom;
                } else {
                    textBox.innerHTML = tonePresetsText[tone] || tonePresetsText['shonen'];
                }

                const mainFont = document.getElementById('fontFamilySelect');
                if (mainFont) mainFont.value = font;
                const mainTone = document.getElementById('globalToneSelect');
                if (mainTone) mainTone.value = tone;
                const mainBackdrop = document.getElementById('backdropModeSelect');
                if (mainBackdrop) mainBackdrop.value = (backdrop === 'dark_box' ? 'natural' : backdrop);
            }

            // ── Cloud Server Health Checker ──────────────────────────────
            async function checkLiveServerHealth() {
                const el = document.getElementById('healthStatusResult');
                el.innerHTML = '<span style="color:#fbbf24;">⏳ กำลังเชื่อมต่อเซิร์ฟเวอร์...</span>';
                const t0 = Date.now();
                try {
                    const res = await fetch('/health');
                    const data = await res.json();
                    const latency = Date.now() - t0;
                    if (data.status === 'online') {
                        el.innerHTML = `<span style="color:#34d399; font-weight:600;">● ออนไลน์สมบูรณ์ (${latency}ms) | เวอร์ชัน: ${data.version} | เซิร์ฟเวอร์: ${data.service}</span>`;
                    } else {
                        el.innerHTML = `<span style="color:#ef4444;">ข้อผิดพลาด: ${JSON.stringify(data)}</span>`;
                    }
                } catch(e) {
                    el.innerHTML = `<span style="color:#ef4444;">เชื่อมต่อล้มเหลว: ${e}</span>`;
                }
            }

            function openSourceWebpage() {
                const input = document.getElementById('webUrlInput');
                let url = input.value.trim();
                if (!url) {
                    alert('กรุณากรอกหรือวาง URL หน้าเว็บมังงะก่อนครับ');
                    return;
                }
                if (!url.startsWith('http://') && !url.startsWith('https://')) {
                    url = 'https://' + url;
                    input.value = url;
                }
                safeOpenUrl(url);
                showNotification('🌐 กำลังเปิดหน้าเว็บต้นฉบับในแท็บใหม่...', 'success');
            }

            function toggleWebpagePreview() {
                const container = document.getElementById('webpagePreviewContainer');
                const iframe = document.getElementById('sourceWebpageIframe');
                const input = document.getElementById('webUrlInput');
                let url = input.value.trim();
                if (!url) {
                    alert('กรุณากรอกหรือวาง URL หน้าเว็บมังงะก่อนครับ');
                    return;
                }
                if (!url.startsWith('http://') && !url.startsWith('https://')) {
                    url = 'https://' + url;
                    input.value = url;
                }
                if (container.style.display === 'none') {
                    container.style.display = 'block';
                    iframe.src = url;
                    showNotification('👁 เปิดพรีวิวหน้าเว็บในหน้านี้แล้ว', 'success');
                } else {
                    container.style.display = 'none';
                    iframe.src = 'about:blank';
                }
            }

            function renderPagesIntoReader(images) {
                const container = document.getElementById('pagesContainer');
                container.innerHTML = '';
                images.forEach((imgUrl, idx) => {
                    const pageDiv = document.createElement('div');
                    pageDiv.className = 'webtoon-page';
                    pageDiv.id = 'pageCard_' + idx;
                    pageDiv.innerHTML = `
                        <div class="page-floating-bar">
                            <span style="font-weight:600; color:#cbd5e1;">หน้า ${idx + 1} / ${images.length}</span>
                            <span id="timeBadge_${idx}" style="color:#94a3b8; font-size:11px;">ต้นฉบับ</span>
                            <div style="display:flex; gap:6px;">
                                <button class="btn btn-outline" style="font-size:11px; padding:3px 8px;" onclick="toggleOriginalView(${idx})">👁 สลับต้นฉบับ</button>
                                <button id="btnTranslate_${idx}" class="btn btn-success" style="font-size:11px; padding:3px 8px;" onclick="translateSingleWebPage(${idx}, '${escapeHtml(imgUrl)}')">⚡ แปล</button>
                            </div>
                        </div>
                        <img id="mangaImg_${idx}" src="${escapeHtml(imgUrl)}" data-original="${escapeHtml(imgUrl)}" alt="Page ${idx + 1}">
                    `;
                    container.appendChild(pageDiv);
                });
                setReaderMode(currentReaderMode);
            }

            function handleFileUpload(files) {
                if (!files || files.length === 0) return;
                const images = [];
                let loaded = 0;
                Array.from(files).forEach((file) => {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        images.push(e.target.result);
                        loaded++;
                        if (loaded === files.length) {
                            fetchedWebImages = images;
                            const inspectCard = document.getElementById('chapterInspectorCard');
                            document.getElementById('inspectTitle').innerText = `อัปโหลด ${images.length} รูปภาพสำเร็จ`;
                            document.getElementById('inspectPageCount').innerText = images.length;
                            document.getElementById('inspectPageCountBtn').innerText = images.length;
                            document.getElementById('inspectSubtitle').innerHTML = `✅ โหลดรูปภาพจากเครื่องเรียบร้อย <b>${images.length}</b> หน้า พร้อมแปลทันที`;
                            inspectCard.style.display = 'block';
                            renderPagesIntoReader(images);
                            document.getElementById('webReaderSection').style.display = 'block';
                            showNotification(`📁 โหลดรูปภาพ ${images.length} หน้าพร้อมแปล!`, 'success');
                        }
                    };
                    reader.readAsDataURL(file);
                });
            }

            // ── iPhone 1-Tap Clipboard Paste ─────────────────────────────
            async function pasteFromIPhoneClipboard() {
                try {
                    if (navigator.clipboard && navigator.clipboard.read) {
                        try {
                            const clipboardItems = await navigator.clipboard.read();
                            const imageFiles = [];
                            for (const item of clipboardItems) {
                                for (const type of item.types) {
                                    if (type.startsWith('image/')) {
                                        const blob = await item.getType(type);
                                        imageFiles.push(new File([blob], "iphone_pasted.png", { type: type }));
                                    }
                                }
                            }
                            if (imageFiles.length > 0) {
                                showNotification('📋 โหลดรูปภาพจากคลิปบอร์ด iPhone สำเร็จ!', 'success');
                                handleFileUpload(imageFiles);
                                return;
                            }
                        } catch(clipErr) {
                            console.log('Clipboard image read error, falling back to text:', clipErr);
                        }
                    }

                    if (navigator.clipboard && navigator.clipboard.readText) {
                        const text = await navigator.clipboard.readText();
                        if (text && text.trim()) {
                            const cleanText = text.trim();
                            if (cleanText.startsWith('http://') || cleanText.startsWith('https://')) {
                                document.getElementById('webUrlInput').value = cleanText;
                                showNotification('📋 วาง URL จากคลิปบอร์ด iPhone เรียบร้อย!', 'success');
                                checkAllWebtoonPages();
                                return;
                            } else if (cleanText.includes('<img') || cleanText.includes('http')) {
                                document.getElementById('rawHtmlInput').value = cleanText;
                                toggleHtmlPasteDrawer();
                                extractAndReadFromPastedHtml();
                                return;
                            }
                        }
                    }
                    showNotification('💡 คุณสามารถแตะค้างในช่อง URL แล้วกด "วาง (Paste)" ได้เลยครับ', 'info');
                } catch(e) {
                    showNotification('💡 แตะค้างที่ช่อง URL แล้วกด "วาง (Paste)" เพื่อแปลได้ทันที', 'info');
                }
            }

            // Clipboard Paste support (Ctrl+V)
            window.addEventListener('paste', (e) => {
                const items = (e.clipboardData || (e.originalEvent && e.originalEvent.clipboardData))?.items;
                if (!items) return;
                const imageFiles = [];
                for (let item of items) {
                    if (item.type && item.type.indexOf('image') !== -1) {
                        const blob = item.getAsFile();
                        if (blob) imageFiles.push(blob);
                    }
                }
                if (imageFiles.length > 0) {
                    handleFileUpload(imageFiles);
                }
            });

            async function checkAllWebtoonPages() {
                if (!systemEnabled) {
                    showNotification('❌ ระบบปิดอยู่ กรุณาเปิดสวิตช์มุมขวาบนก่อน', 'warning');
                    return false;
                }
                const input = document.getElementById('webUrlInput');
                let url = input.value.trim();
                if (!url) {
                    alert('กรุณากรอกหรือวาง URL หน้าเว็บมังงะก่อนครับ');
                    return false;
                }
                if (!url.startsWith('http://') && !url.startsWith('https://')) {
                    url = 'https://' + url;
                    input.value = url;
                }

                const inspectCard = document.getElementById('chapterInspectorCard');
                const inspectTitle = document.getElementById('inspectTitle');
                const inspectSubtitle = document.getElementById('inspectSubtitle');
                const inspectPageCount = document.getElementById('inspectPageCount');
                const inspectPageCountBtn = document.getElementById('inspectPageCountBtn');

                inspectCard.style.display = 'block';
                inspectTitle.innerHTML = '⏳ กำลังสแกนตรวจสอบหน้าเว็บและรูปภาพทั้งหมด...';
                inspectSubtitle.innerHTML = '<span style="color:#fbbf24;">กำลังเชื่อมต่อไปยัง ' + escapeHtml(url) + '</span>';

                try {
                    const res = await fetch('/api/fetch-webpage-manga', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: url })
                    });
                    const data = await res.json();
                    
                    if (data.images && data.images.length > 0) {
                        fetchedWebImages = data.images;
                        inspectTitle.innerText = data.title || 'ตอนมังงะ/เว็บตูน';
                        inspectPageCount.innerText = data.images.length;
                        inspectPageCountBtn.innerText = data.images.length;
                        inspectSubtitle.innerHTML = `✅ ตรวจพบทั้งหมด <b style="color:#34d399; font-size:15px;">${data.images.length}</b> หน้า พร้อมแปลทันที | รูปภาพครบถ้วน 100%`;
                        showNotification(`✅ ตรวจพบทั้งหมด ${data.images.length} หน้า พร้อมแปล!`, 'success');
                        
                        renderPagesIntoReader(data.images);
                        document.getElementById('webReaderSection').style.display = 'block';
                        return true;
                    } else {
                        const errMsg = data.error || 'ไม่พบรูปภาพมังงะใน URL นี้';
                        const isBot = errMsg.includes('Bot protection') || errMsg.includes('403');
                        inspectTitle.innerHTML = `<span style="color:#f87171;">⚠️ ไม่พบรูปภาพ ${isBot ? '(เว็บติดระบบกันบอท Cloudflare)' : ''}</span>`;
                        inspectSubtitle.innerHTML = `
                            <span style="color:#f87171;">${errMsg}</span>
                            <div style="margin-top:12px; padding:12px; background:#0f172a; border-radius:8px; border:1px solid #3b82f6;">
                                <div style="font-weight:600; color:#38bdf8; margin-bottom:6px;">💡 แนะนำวิธีแปลสำหรับเว็บที่มีระบบกันบอท:</div>
                                <div style="font-size:12px; color:#cbd5e1; line-height:1.6;">
                                    • เว็บไซต์มังงะต้นทางมี Cloudflare บล็อกเซิร์ฟเวอร์คลาวด์ภายนอก<br>
                                    • คุณสามารถเปิดดูเว็บมังงะนั้นบนเบราว์เซอร์ของคุณ แล้วกด <b>Bookmarklet แปลสด</b> ได้ทันที 100% โดยไม่ติดระบบกันบอท<br>
                                    • หรือคัดลอกลิงก์รูปภาพ (Image Address) จากหน้าเว็บนั้นมาวางในช่องได้โดยตรง
                                </div>
                                <div style="display:flex; gap:8px; margin-top:10px; flex-wrap:wrap;">
                                    <button class="btn btn-outline" style="font-size:12px; padding:5px 12px;" onclick="openSourceWebpage()">🌐 เปิดดูหน้าเว็บต้นฉบับ</button>
                                    <button class="btn btn-primary" style="font-size:12px; padding:5px 12px;" onclick="copyBookmarkletCode()">📋 คัดลอก Bookmarklet แปลสดบนหน้าเว็บ</button>
                                </div>
                            </div>
                        `;
                        return false;
                    }
                } catch(e) {
                    inspectTitle.innerHTML = '<span style="color:#f87171;">⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อ</span>';
                    inspectSubtitle.innerHTML = `<span style="color:#f87171;">${e}</span>`;
                    return false;
                }
            }

            async function fetchAndReadWebManga(autoStartTranslate = false) {
                const ok = await checkAllWebtoonPages();
                if (ok) {
                    if (autoStartTranslate || document.getElementById('autoTranslateCheck').checked) {
                        startBatchTranslation();
                    }
                }
            }

            // Real-time Progress & Timer Engine
            function startTimer() {
                startTime = Date.now();
                clearInterval(timerInterval);
                timerInterval = setInterval(updateProgressHUD, 500);
            }

            function stopTimer() {
                clearInterval(timerInterval);
            }

            function updateProgressHUD() {
                if (isPaused) return;
                const elapsedSec = (Date.now() - startTime) / 1000;
                const minutes = Math.floor(elapsedSec / 60).toString().padStart(2, '0');
                const seconds = Math.floor(elapsedSec % 60).toString().padStart(2, '0');

                const total = fetchedWebImages.length;
                const percent = total > 0 ? Math.round((translatedCount / total) * 100) : 0;
                document.getElementById('progressBarFill').style.width = percent + '%';

                let etaText = 'กำลังประเมิน...';
                if (translatedCount > 0) {
                    const avgPerSec = elapsedSec / translatedCount;
                    const remaining = Math.max(0, Math.round(avgPerSec * (total - translatedCount)));
                    etaText = `เหลืออีก ~${remaining} วินาที (เฉลี่ย ${avgPerSec.toFixed(1)} วิ/หน้า)`;
                }

                document.getElementById('progressTitle').innerText = translatedCount >= total 
                    ? `🎉 แปลครบทั้ง ${total} หน้าเสร็จสมบูรณ์แล้ว!` 
                    : `⏳ กำลังแปลภาษาไทย (${percent}%)`;

                document.getElementById('progressSubtitle').innerText = translatedCount >= total
                    ? `✓ แปลครบทั้งหมด ${total}/${total} หน้า ในเวลา ${minutes}:${seconds} วินาที | สามารถเลื่อนอ่านด้านล่างได้ทันที!`
                    : `หน้า ${translatedCount}/${total} | ⏱ ใช้เวลาไปแล้ว: ${minutes}:${seconds} วินาที | ⏳ ${etaText}`;

                document.getElementById('floatingHudStatus').innerText = `หน้า ${translatedCount}/${total} (${percent}%)`;

                if (translatedCount >= total) {
                    stopTimer();
                }
            }

            function togglePauseResume() {
                isPaused = !isPaused;
                document.getElementById('btnPauseResume').innerText = isPaused ? '▶ ดำเนินการต่อ' : '⏸ หยุดชั่วคราว';
            }

            async function startBatchTranslation() {
                translatedCount = 0;
                isPaused = false;
                startTimer();

                // Concurrency 1 worker ensures strict memory safety on free cloud instances (512MB RAM limit)
                const concurrency = 1;
                let queueIndex = 0;

                async function worker() {
                    while (queueIndex < fetchedWebImages.length) {
                        while (isPaused) {
                            await new Promise(r => setTimeout(r, 500));
                        }
                        const idx = queueIndex++;
                        await translateSingleWebPage(idx, fetchedWebImages[idx]);
                        translatedCount++;
                        updateProgressHUD();
                    }
                }

                const workers = [];
                for (let c = 0; c < concurrency; c++) {
                    workers.push(worker());
                }
                await Promise.all(workers);
                updateProgressHUD();
            }

            async function translateSingleWebPage(idx, imgUrl) {
                if (!systemEnabled) return;
                const imgEl = document.getElementById('mangaImg_' + idx);
                const timeBadge = document.getElementById('timeBadge_' + idx);
                const btn = document.getElementById('btnTranslate_' + idx);
                const tone = document.getElementById('globalToneSelect').value;
                const fontFamily = document.getElementById('fontFamilySelect').value;
                const backdropMode = document.getElementById('backdropModeSelect').value;
                const sourceLang = document.getElementById('sourceLangSelect') ? document.getElementById('sourceLangSelect').value : 'auto';

                btn.disabled = true;
                btn.innerText = '⏳';
                timeBadge.innerHTML = '<span style="color:#fbbf24;">กำลังประมวลผล...</span>';
                const pageT0 = Date.now();

                try {
                    const res = await fetch('/api/translate-image-url', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            image_url: imgUrl, 
                            tone: tone,
                            source_lang: sourceLang,
                            font_family: fontFamily,
                            backdrop_mode: backdropMode
                        })
                    });
                    const data = await res.json();
                    const pageElapsed = ((Date.now() - pageT0) / 1000).toFixed(1);

                    if (data.status === 'success') {
                        let finalSrc = data.result_b64;
                        if (!finalSrc.startsWith('data:')) {
                            finalSrc = (finalSrc.startsWith('/9j/') ? 'data:image/jpeg;base64,' : 'data:image/png;base64,') + finalSrc;
                        }
                        imgEl.src = finalSrc;
                        imgEl.setAttribute('data-translated', finalSrc);
                        const cacheTag = data.cached ? '⚡ แคชทันใจ 0.0s' : `✓ เสร็จใน ${pageElapsed}s`;
                        timeBadge.innerHTML = `<span style="color:#34d399;">${cacheTag} (${data.bubbles_count} บอลลูน)</span>`;
                        btn.innerText = '✓';
                    } else {
                        timeBadge.innerHTML = `<span style="color:#f87171;">ข้อผิดพลาด: ${data.error}</span>`;
                        btn.innerText = '⚡';
                        btn.disabled = false;
                    }
                } catch(e) {
                    timeBadge.innerHTML = `<span style="color:#f87171;">ข้อผิดพลาด</span>`;
                    btn.disabled = false;
                }
            }

            function reTranslateAll() {
                startBatchTranslation();
            }

            function toggleOriginalView(idx) {
                const imgEl = document.getElementById('mangaImg_' + idx);
                const orig = imgEl.getAttribute('data-original');
                const trans = imgEl.getAttribute('data-translated');
                const timeBadge = document.getElementById('timeBadge_' + idx);

                if (!trans) {
                    alert('หน้านี้ยังไม่ได้แปล กรุณากดแปลก่อนครับ');
                    return;
                }

                if (imgEl.src === trans) {
                    imgEl.src = orig;
                    timeBadge.innerHTML = `<span style="color:#94a3b8;">กำลังดู: ต้นฉบับ</span>`;
                } else {
                    imgEl.src = trans;
                    timeBadge.innerHTML = `<span style="color:#34d399;">กำลังดู: แปลไทย</span>`;
                }
            }

            function escapeHtml(str) {
                if (!str) return '';
                return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
            }

            // ── Mobile / Cross-Window Image Receiver (from Bookmarklet / Share) ──
            window.addEventListener('message', function(event) {
                if (event.data && event.data.type === 'MANGATHAI_LOAD_IMAGES') {
                    const payload = event.data.data;
                    if (payload && payload.images && payload.images.length > 0) {
                        fetchedWebImages = payload.images;
                        inspectTitle.innerText = payload.title || 'ตอนมังงะ/เว็บตูน';
                        inspectPageCount.innerText = payload.images.length;
                        inspectPageCountBtn.innerText = payload.images.length;
                        inspectSubtitle.innerHTML = `✅ ตรวจพบทั้งหมด <b style="color:#34d399; font-size:15px;">${payload.images.length}</b> หน้า พร้อมแปลทันที`;
                        if (payload.tone) {
                            const toneEl = document.getElementById('mangaTone');
                            if (toneEl) toneEl.value = payload.tone;
                        }
                        if (payload.source_lang) {
                            const langEl = document.getElementById('sourceLang');
                            if (langEl) langEl.value = payload.source_lang;
                        }
                        renderPagesIntoReader(payload.images);
                        document.getElementById('webReaderSection').style.display = 'block';
                        showNotification(`✅ โหลดมังงะ ${payload.images.length} หน้า จากมือถือสำเร็จ!`, 'success');
                    }
                }
            });
        </script>
    </body>
    <script>
        // Register PWA Service Worker for iPhone/iPad installability
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/static/sw.js')
                    .then(r => console.log('SW registered:', r.scope))
                    .catch(e => console.log('SW error:', e));
            });
        }
        // Show iOS "Add to Home Screen" banner if not already installed
        const isIOS = /iphone|ipad|ipod/.test(navigator.userAgent.toLowerCase());
        const isStandalone = window.navigator.standalone === true;
        if (isIOS && !isStandalone) {
            document.getElementById('iosBanner').style.display = 'block';
        }
    </script>
    </html>
    """
    return HTMLResponse(content=html_content)


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
        result_b64 = pil_to_base64(res["result_pil"], format="JPEG", quality=85)
        response_data = {
            "status": "success",
            "cached": False,
            "elapsed_seconds": elapsed,
            "bubbles_count": len(res["bubbles"]),
            "bubbles": res["bubbles"],
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
