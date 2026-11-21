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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="มังงะไทย">
        <meta name="theme-color" content="#6366f1">
        <link rel="manifest" href="/static/manifest.json">
        <link rel="apple-touch-icon" href="/static/icon-192.png">
        <title>MangaThaiAI-Studio | Real-Time Manga & Webtoon Studio</title>
        <!-- Google Fonts: Mali (Comic), Kanit (Action), Chakra Petch (Gaming Status) -->
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;700&family=Kanit:wght@400;600;700&family=Mali:wght@500;600;700&family=Prompt:wght@400;500;600&display=swap" rel="stylesheet">
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
                /* iOS safe area */
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
                gap: 10px;
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
                min-height: 44px; /* iOS touch target */
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
                border-radius: 12px;
                padding: 20px;
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
                gap: 6px;
                min-height: 44px; /* iOS touch target */
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

            /* Mobile optimizations */
            @media (max-width: 600px) {
                body { padding: 12px; padding-bottom: 80px; }
                h1 { font-size: 18px !important; }
                .card { padding: 14px; }
                .tabs { gap: 6px; padding-bottom: 6px; }
                .tab-btn { padding: 8px 12px; font-size: 12px; }
                #readerStreamWrapper { max-width: 100% !important; }
                .floating-hud { width: calc(100% - 32px); border-radius: 16px; padding: 10px 14px; }
                #floatingSideNav { display: none !important; }
                select.input-text, .input-text { font-size: 16px; } /* Prevent iOS zoom */
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
                        <b style="color:#a5b4fc; font-size:14px;">ติดตั้งแอปบน iPhone/iPad ของคุณ!</b>
                        <p style="margin:4px 0 0; font-size:12px; color:#94a3b8; line-height:1.6;">
                            กด <b style="color:#fff;">Share</b> (ไอคอนกล่องลูกศรขึ้น) → เลือก <b style="color:#fff;">"Add to Home Screen"</b><br>
                            → คุณจะได้ไอคอน ⚡ MangaThaiAI บนหน้าจอหลัก พร้อมใช้งานแบบแอปเต็มหน้าจอ!
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
                    <span class="badge badge-online">● Laptop Control Center</span>
                </div>
            </header>

            <!-- Navigation Tabs -->
            <div class="tabs">
                <button class="tab-btn active" onclick="switchTab('tab-webreader')">🌐 โหมดอ่านและแปลเว็บตูน (Webtoon Reader)</button>
                <button class="tab-btn" onclick="switchTab('tab-fonts')">🎨 ตัวอย่างฟอนต์การ์ตูน & บอลลูน (Font Gallery)</button>
                <button class="tab-btn" onclick="switchTab('tab-bookmarklet')">📌 บุ๊กมาร์กแปลสด (Bookmarklet)</button>
                <button class="tab-btn" onclick="switchTab('tab-showcase')">🎭 เทียบสำนวนมังงะ (Natural vs Stiff)</button>
            </div>

            <!-- ================= TAB 1: WEB READER ================= -->
            <div id="tab-webreader" class="tab-content">
                <!-- Input Card -->
                <div id="webUrlCard" class="card">
                    <h2 style="margin-top:0; font-size:17px; display:flex; align-items:center; gap:8px;">
                        <span>🌐</span> วาง URL ตอนมังงะ/เว็บตูนเพื่อแปลและอ่านเป็นภาษาไทยทันที
                    </h2>
                    <div style="display:flex; gap:10px; flex-wrap:wrap;">
                        <input type="text" id="webUrlInput" class="input-text" style="flex:1; min-width:300px;" 
                               placeholder="ตัวอย่าง: https://asurascans.com/comics/overgeared-1bb35e56/chapter/343">
                        <button class="btn btn-success" onclick="fetchAndReadWebManga()">
                            🚀 ดึงข้อมูล & เปิดอ่าน
                        </button>
                    </div>

                    <!-- Reader Preferences Bar -->
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:12px; margin-top:16px; padding-top:16px; border-top:1px solid #1e293b;">
                        <!-- Font Selection -->
                        <div>
                            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">🎨 ฟอนต์ตัวอักษร:</label>
                            <select id="fontFamilySelect" class="input-text" style="width:100%;" onchange="onSettingChanged()">
                                <option value="mali" selected>✍️ Mali Comic (ลายเส้นมังงะ เข้าถึงอารมณ์ [แนะนำ])</option>
                                <option value="kanit">⚔️ Kanit Shonen (แอ็กชันดุดัน คมชัด หนักแน่น)</option>
                                <option value="chakrapetch">🎮 Chakra Petch (ระบบเกม/สเตตัส ล้ำยุค)</option>
                            </select>
                        </div>

                        <!-- Backdrop / Bubble Mode -->
                        <div>
                            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">✨ รูปแบบพื้นหลังบอลลูน:</label>
                            <select id="backdropModeSelect" class="input-text" style="width:100%;" onchange="onSettingChanged()">
                                <option value="natural" selected>🎨 ลายเส้นมังงะแท้ 100% (ไร้กรอบ ไร้เหลี่ยม สะอาดตา [แนะนำ])</option>
                                <option value="soft_white">⚪ รองพื้นขาวนุ่มนวล (Soft White)</option>
                                <option value="none">✨ ตัวหนังสือเพียวๆ</option>
                            </select>
                        </div>

                        <!-- Manga Tone Preset -->
                        <div>
                            <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:4px;">🎭 โทนสำนวนบทพูด:</label>
                            <select id="globalToneSelect" class="input-text" style="width:100%;" onchange="onSettingChanged()">
                                <option value="shonen" selected>⚔️ โชเน็น / แอ็กชัน (แก, ข้า, ลุย, ดุดัน)</option>
                                <option value="shojo">🌸 โรแมนติก / ตาหวาน (นาย, ฉัน, ละมุน ซึนเดเระ)</option>
                                <option value="seinen">🕵️ สืบสวน / สุขุม (จริงจัง ลุ่มลึก เป็นธรรมชาติ)</option>
                                <option value="comedy">🤣 การ์ตูนแก๊ก / ตลก (คำสร้อย กวนๆ ฮาๆ)</option>
                            </select>
                        </div>
                    </div>

                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; flex-wrap:wrap; gap:8px;">
                        <label style="display:flex; align-items:center; gap:8px; cursor:pointer; font-size:13px; color:#a5b4fc; font-weight:600;">
                            <input type="checkbox" id="autoTranslateCheck" checked> ⚡ แปลภาษาไทยอัตโนมัติทันทีที่เปิดตอน (Auto Stream)
                        </label>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span class="badge" style="background:#064e3b; color:#6ee7b7; font-size:11px;">🛡️ ปิดกั้นโฆษณาเว็บพนัน & ป๊อปอัป 100%</span>
                        </div>
                        <div style="font-size:12px; color:var(--text-muted);">
                            💡 ทางลัดทดสอบด่วน: 
                            <a href="javascript:void(0)" style="color:#38bdf8; font-weight:600; text-decoration:none;" onclick="loadAsuraUrl()">👉 Overgeared ตอน 343 (Asura Scans)</a> | 
                            <a href="javascript:void(0)" style="color:#818cf8; text-decoration:none;" onclick="loadTestUrl()">มังงะตัวอย่าง</a>
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

                    <!-- Reader Controls Bar (View Mode, Width Slider & Click-Scroll Navigation) -->
                    <div class="card" style="padding:10px 18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:16px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:13px; font-weight:600; color:#cbd5e1;">📱 จัดวางหน้า:</span>
                            <button id="btnModeSeamless" class="btn btn-success" style="font-size:12px; padding:5px 12px;" onclick="setReaderMode('seamless')">เว็บตูนไร้รอยต่อ</button>
                            <button id="btnModeCard" class="btn btn-outline" style="font-size:12px; padding:5px 12px;" onclick="setReaderMode('card')">การ์ดแยกหน้า</button>
                        </div>
                        <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
                            <label style="display:flex; align-items:center; gap:6px; cursor:pointer; font-size:12px; color:#38bdf8; font-weight:600;" title="คลิกครึ่งบนเพื่อเลื่อนขึ้น / คลิกครึ่งล่างเพื่อเลื่อนลง">
                                <input type="checkbox" id="clickScrollCheck" checked onchange="toggleClickScroll(this.checked)">
                                🖱️ โหมดคลิกขึ้น-ลง (คลิกจอด้านบน/ล่าง)
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

            <!-- ================= TAB 2: FONT GALLERY ================= -->
            <div id="tab-fonts" class="tab-content" style="display:none;">
                <div class="card">
                    <h2 style="margin-top:0; font-size:18px;">🎨 แกลเลอรีเปรียบเทียบฟอนต์การ์ตูน & บอลลูนคำพูด (Font & Styling Showcase)</h2>
                    <p style="color:var(--text-muted); font-size:14px;">
                        ระบบออกแบบมาเพื่อแก้ปัญหาตัวหนังสือแข็งทื่อ ด้วย 3 ฟอนต์ระดับพรีเมียมที่สอดรับกับแต่ละฉากและอารมณ์:
                    </p>

                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:20px; margin-top:20px;">
                        <!-- Font 1: Mali Comic -->
                        <div style="background:#090d16; border:1px solid #334155; border-radius:12px; padding:20px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <b style="color:#6ee7b7; font-size:16px;">1. Mali Comic (ลายเส้นมังงะ)</b>
                                <span class="badge" style="background:#064e3b; color:#a7f3d0;">ยอดนิยมที่สุด</span>
                            </div>
                            <p style="color:var(--text-muted); font-size:13px; margin:8px 0 16px;">
                                ลายเส้นเขียนมือโค้งมนเป็นธรรมชาติ เข้าถึงอารมณ์ตัวละคร เหมือนเปิดอ่านหนังสือการ์ตูนรวมเล่ม
                            </p>
                            <!-- Visual Preview Box -->
                            <div style="background:#fff; color:#0f172a; padding:16px; border-radius:18px; border:2px solid #334155; text-align:center; box-shadow:0 4px 15px rgba(0,0,0,0.5);">
                                <div style="font-family:'Mali', cursive; font-size:18px; font-weight:700; line-height:1.4;">
                                    "เฮ้ย! รอก่อนสิฟะ!<br>อย่าเพิ่งไปทางนั้นนะโว้ย!"
                                </div>
                            </div>
                        </div>

                        <!-- Font 2: Kanit Shonen -->
                        <div style="background:#090d16; border:1px solid #334155; border-radius:12px; padding:20px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <b style="color:#60a5fa; font-size:16px;">2. Kanit Shonen (แอ็กชันดุดัน)</b>
                                <span class="badge" style="background:#1e3a8a; color:#bfdbfe;">เว็บตูนต่อสู้</span>
                            </div>
                            <p style="color:var(--text-muted); font-size:13px; margin:8px 0 16px;">
                                ตัวหนา คมชัด สไตล์มันฮวาเกาหลีแอ็กชัน (Solo Leveling, Overgeared) ตะโกนลั่นสนามรบ
                            </p>
                            <div style="background:#fff; color:#0f172a; padding:16px; border-radius:18px; border:2px solid #334155; text-align:center; box-shadow:0 4px 15px rgba(0,0,0,0.5);">
                                <div style="font-family:'Kanit', sans-serif; font-size:18px; font-weight:700; line-height:1.35;">
                                    "ข้าไม่ยอมแพ้หรอก!<br>รับดาบเล่มนี้ของข้าไปซะ!"
                                </div>
                            </div>
                        </div>

                        <!-- Font 3: Chakra Petch -->
                        <div style="background:#090d16; border:1px solid #334155; border-radius:12px; padding:20px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <b style="color:#fcd34d; font-size:16px;">3. Chakra Petch (กล่องระบบเกม)</b>
                                <span class="badge" style="background:#451a03; color:#fde68a;">เควสต์ & สเตตัส</span>
                            </div>
                            <p style="color:var(--text-muted); font-size:13px; margin:8px 0 16px;">
                                รูปทรงดิจิทัลไซเบอร์ ใช้แสดงข้อความแจ้งเตือน หน้าต่างสถานะ เควสต์ของราชา
                            </p>
                            <div style="background:#0b1221; color:#f8fafc; padding:16px; border-radius:10px; border:2px solid #38bdf8; text-align:center; box-shadow:0 0 20px rgba(56,189,248,0.3);">
                                <div style="font-family:'Chakra Petch', sans-serif; font-size:16px; font-weight:700; line-height:1.4; color:#38bdf8;">
                                    [ เควสต์ของราชา (2) : เคลียร์สำเร็จ ]<br>
                                    <span style="color:#f8fafc; font-size:14px;">ได้รับสูตรสร้างไอเทม: ดาบแห่งราชา!</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ================= TAB 3: BOOKMARKLET ================= -->
            <div id="tab-bookmarklet" class="tab-content" style="display:none;">
                <div class="card">
                    <h2 style="margin-top:0; font-size:18px;">📌 ติดตั้ง Bookmarklet แปลมังงะสดบนทุกเว็บไซต์ (One-Click In-Browser Translator)</h2>
                    <p style="color:var(--text-muted); font-size:14px; line-height:1.6;">
                        คุณสามารถแปลมังงะสดได้โดยตรงขณะเปิดหน้าเว็บมังงะใด ๆ ในโลก เพียงลากปุ่มด้านล่างนี้ไปวางที่แถบบุ๊กมาร์ก (Bookmarks Bar) ของเบราว์เซอร์:
                    </p>
                    <div style="background:#090d16; border:2px dashed #4f46e5; border-radius:12px; padding:24px; text-align:center; margin:20px 0;">
                        <a id="bookmarkletAnchor" 
                           href="javascript:(function(){var s=document.createElement('script');s.src=(window.location.origin||'http://localhost:8000')+'/static/bookmarklet.js?t='+Date.now();document.body.appendChild(s);})();" 
                           class="btn btn-success" 
                           style="font-size:16px; padding:12px 24px; text-decoration:none; display:inline-block; cursor:grab;"
                           title="ลากปุ่มนี้ไปวางที่ Bookmarks Bar ของเบราว์เซอร์">
                            📌 แปลมังงะไทยสด (MangaThaiAI)
                        </a>
                        <div style="margin-top:16px; display:flex; justify-content:center; gap:10px; flex-wrap:wrap;">
                            <button class="btn btn-outline" style="font-size:12px;" onclick="copyBookmarkletCode()">
                                📋 คัดลอกโค้ดสำหรับ Safari บน iPhone/iPad
                            </button>
                        </div>
                        <p style="margin-top:12px; font-size:12px; color:var(--text-muted); line-height:1.6;">
                            💻 <b>บนคอมพิวเตอร์:</b> คลิกเมาส์ค้างที่ปุ่มสีเขียวแล้วลากไปวางที่แถบบุ๊กมาร์ก (Bookmarks Bar)<br>
                            📱 <b>บน iPhone / iPad:</b> กดปุ่ม "คัดลอกโค้ด" ด้านบน → ไปที่ Safari บุ๊กมาร์กหน้าเว็บอะไรก็ได้ → กดแก้ไข (Edit Bookmark) → วางโค้ดนี้ลงในช่อง URL
                        </p>
                    </div>
                </div>
            </div>

            <!-- ================= TAB 4: SHOWCASE ================= -->
            <div id="tab-showcase" class="tab-content" style="display:none;">
                <div class="card">
                    <h2 style="margin-top:0; font-size:18px;">🎭 ผลการทดสอบเปรียบเทียบ: สำนวนมังงะธรรมชาติ (MangaThaiAI) vs แปลแข็งทื่อ (Google Translate)</h2>
                    <div style="display:flex; flex-direction:column; gap:16px; margin-top:16px;">
                        <div class="card" style="margin:0; background:#0b1120;">
                            <b>Overgeared ตอน 343: ข้อความเควสต์</b>
                            <div style="margin-top:6px; color:#cbd5e1; font-size:13px;">
                                QUEST CLEAR CONDITIONS: GIVE THE NECESSARY HELP TO 5,000 CITIZENS
                            </div>
                            <div style="margin-top:8px; color:#6ee7b7; font-weight:600;">
                                ✅ แปลไทยแบบมังงะ: "เงื่อนไขการเคลียร์ภารกิจ: มอบความช่วยเหลือแก่ประชาชน 5,000 คน!"
                            </div>
                            <div style="margin-top:4px; color:#f87171; font-size:12px;">
                                ❌ แปลแข็งดั้งเดิม: "เงื่อนไขที่ชัดเจนในการค้นหา: ให้ความช่วยเหลือที่จำเป็นแก่พลเมือง 5,000 คน"
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Floating Glass Theater HUD (Appears when scrolling or in theater mode) -->
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
            let systemEnabled = true; // ON/OFF power state

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

            // Anti-Gambling Popup Blocker Shield
            window.open = function() {
                console.log('Blocked external popup attempt');
                return null;
            };

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

            // Click-to-Scroll Event Handler: Click upper screen to scroll up, lower to scroll down
            document.addEventListener('click', function(e) {
                if (!isClickScrollEnabled) return;
                if (e.target.closest('button, input, select, a, .page-floating-bar, .floating-hud, #floatingSideNav, header, .card')) {
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

            // Keyboard Navigation (Space, ArrowDown, ArrowUp, J, K, PageDown, PageUp)
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

            function switchTab(tabId) {
                document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                document.getElementById(tabId).style.display = 'block';
                event.target.classList.add('active');
            }

            function loadAsuraUrl() {
                document.getElementById('webUrlInput').value = 'https://asurascans.com/comics/overgeared-1bb35e56/chapter/343';
                fetchAndReadWebManga();
            }

            function loadTestUrl() {
                document.getElementById('webUrlInput').value = 'http://localhost:8000/static/sample_manga.png';
                fetchAndReadWebManga();
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
                // If images are already loaded, user can re-translate
            }

            async function fetchAndReadWebManga() {
                if (!systemEnabled) {
                    showNotification('❌ ระบบปิดอยู่ กรุณาเปิดสวิตช์ก่อน', 'warning');
                    return;
                }
                const url = document.getElementById('webUrlInput').value.trim();
                if (!url) {
                    alert('กรุณาใส่ URL หน้าเว็บมังงะ');
                    return;
                }
                const container = document.getElementById('pagesContainer');
                const section = document.getElementById('webReaderSection');

                container.innerHTML = '<p style="color:#fbbf24; text-align:center; padding:40px; font-size:16px;">⏳ กำลังเชื่อมต่อและดึงหน้ามังงะจากหน้าเว็บ Asura Scans...</p>';
                section.style.display = 'block';

                try {
                    const res = await fetch('/api/fetch-webpage-manga', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: url })
                    });
                    const data = await res.json();
                    fetchedWebImages = data.images;

                    if (!data.images.length) {
                        container.innerHTML = '<p style="color:#f87171; text-align:center; padding:30px;">ไม่พบรูปภาพมังงะใน URL นี้</p>';
                        return;
                    }

                    container.innerHTML = '';
                    data.images.forEach((imgUrl, idx) => {
                        const pageDiv = document.createElement('div');
                        pageDiv.className = 'webtoon-page';
                        pageDiv.id = 'pageCard_' + idx;
                        pageDiv.innerHTML = `
                            <div class="page-floating-bar">
                                <span style="font-weight:600; color:#cbd5e1;">หน้า ${idx + 1}</span>
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

                    if (document.getElementById('autoTranslateCheck').checked) {
                        startBatchTranslation();
                    }
                } catch(e) {
                    container.innerHTML = '<p style="color:#f87171; text-align:center; padding:30px;">เกิดข้อผิดพลาดในการดึงข้อมูล: ' + e + '</p>';
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
                    ? `✓ แปลครบทั้ง ${total} หน้าเสร็จสมบูรณ์แล้ว!` 
                    : `⏳ กำลังแปลภาษาไทย (${percent}%)`;

                document.getElementById('progressSubtitle').innerText = 
                    `หน้า ${translatedCount}/${total} | ⏱ ใช้เวลาไปแล้ว: ${minutes}:${seconds} วินาที | ⏳ ${etaText}`;

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

                // 3 Concurrent Streaming Workers for 50% faster completion
                const concurrency = 3;
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
                if (!systemEnabled) return; // Skip if system is OFF
                const imgEl = document.getElementById('mangaImg_' + idx);
                const timeBadge = document.getElementById('timeBadge_' + idx);
                const btn = document.getElementById('btnTranslate_' + idx);
                const tone = document.getElementById('globalToneSelect').value;
                const fontFamily = document.getElementById('fontFamilySelect').value;
                const backdropMode = document.getElementById('backdropModeSelect').value;

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
                            font_family: fontFamily,
                            backdrop_mode: backdropMode
                        })
                    });
                    const data = await res.json();
                    const pageElapsed = ((Date.now() - pageT0) / 1000).toFixed(1);

                    if (data.status === 'success') {
                        imgEl.src = 'data:image/png;base64,' + data.result_b64;
                        imgEl.setAttribute('data-translated', 'data:image/png;base64,' + data.result_b64);
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


@app.post("/api/fetch-webpage-manga")
async def fetch_webpage_manga(req: FetchWebpageRequest):
    return await crawler.extract_manga_images_from_url(req.url)


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
    tone: str = "shonen"
    font_family: str = "mali"
    backdrop_mode: str = "natural"


@app.post("/api/translate-image-url")
async def translate_image_url(req: TranslateImageUrlRequest):
    t0 = time.time()
    try:
        # Check high-performance disk cache
        cache_key = hashlib.md5(
            f"{req.image_url}_{req.tone}_{req.font_family}_{req.backdrop_mode}".encode("utf-8")
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

        if "sample_manga.png" in req.image_url:
            local_path = INPUT_DIR / "sample_manga.png"
            if not local_path.exists():
                from scripts.create_sample_manga import generate_sample_manga
                local_path = generate_sample_manga(str(local_path))
            res = pipeline.process_page(
                local_path,
                tone=req.tone,
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
                    font_family=req.font_family,
                    backdrop_mode=req.backdrop_mode,
                )
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

        elapsed = round(time.time() - t0, 2)
        response_data = {
            "status": "success",
            "cached": False,
            "elapsed_seconds": elapsed,
            "bubbles_count": len(res["bubbles"]),
            "bubbles": res["bubbles"],
            "cleaned_b64": bgr_to_base64(res["cleaned_bgr"]),
            "result_b64": pil_to_base64(res["result_pil"]),
        }

        # Save to disk cache for instantaneous reloads
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(response_data, f, default=str)
        except Exception as e:
            logger.warning(f"Could not cache result: {e}")

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
