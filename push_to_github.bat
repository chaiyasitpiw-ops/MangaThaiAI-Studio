@echo off
chcp 65001 >nul
title MangaThaiAI-Studio 🚀 Push to GitHub
color 0B
cls

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║       🚀 อัปโหลดโค้ดขึ้น GitHub เพื่อ Deploy Cloud     ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo  1. กรุณาสร้าง Repository เปล่าที่: https://github.com/new
echo     - Repository name: MangaThaiAI-Studio
echo     - เลือก Public
echo     - ไม่ต้องติ๊ก Add README (เพราะเรามีพร้อมแล้ว)
echo.
set /p REPO_URL="2. วางลิงก์ GitHub ของคุณ (เช่น https://github.com/chaiyasitpiw-ops/MangaThaiAI-Studio.git): "

if "%REPO_URL%"=="" (
    echo ❌ ไม่ได้ใส่ลิงก์
    pause
    exit /b
)

git remote remove origin 2>nul
git remote add origin %REPO_URL%
git branch -M main
echo.
echo  ⏳ กำลังส่งข้อมูลขึ้น GitHub...
git push -u origin main

if errorlevel 1 (
    echo.
    echo  ❌ ไม่สามารถ Push ได้ — หาก GitHub ถามรหัสผ่าน ให้ใช้ Personal Access Token (PAT)
) else (
    echo.
    echo  ✅ ส่งโค้ดขึ้น GitHub สำเร็จเรียบร้อยแล้ว!
    echo  👉 ตอนนี้ไปที่ https://dashboard.render.com เพื่อกดเชื่อมต่อและ Deploy ได้เลย
)

echo.
pause
