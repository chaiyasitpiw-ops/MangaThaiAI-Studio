@echo off
chcp 65001 >nul
title MangaThaiAI-Studio ⚡ Local Reader & 18+ Translator (No Cloudflare Block)
color 0A
cls

echo ============================================================
echo   MangaThaiAI-Studio: Real-Time Local AI Studio 2.0
echo ============================================================
echo.
echo   [1/2] กำลังตรวจสอบความพร้อมของระบบ...
cd /d "D:\code\MangaThaiAI-Studio"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] ไม่พบ .venv กรุณาติดตั้ง Python venv ก่อนใช้งาน
    pause
    exit /b 1
)

echo   [2/2] กำลังสตาร์ทเซิร์ฟเวอร์ Local บนพอร์ต 8000...
echo.
echo ============================================================
echo   ✓ เซิร์ฟเวอร์ทำงานที่: http://localhost:8000
echo   ✓ ปลดล็อก Cloudflare 100%% ไม่ติดบล็อก (NewXtoon, Toptoon, Asura)
echo   ✓ รองรับแปลภาษา: เกาหลี, รัสเซีย, อังกฤษ, จีน
echo   ✓ โหมดสำนวนแปล: 18+ ผู้ใหญ่, โชเน็น, โรแมนติก, เซย์เน็น
echo ============================================================
echo.
echo   กำลังเปิดเบราว์เซอร์ไปยัง http://localhost:8000 ...
start http://localhost:8000

".venv\Scripts\python.exe" -m uvicorn control_center.app:app --host 0.0.0.0 --port 8000 --reload
pause
