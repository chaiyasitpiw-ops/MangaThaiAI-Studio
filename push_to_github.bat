@echo off
chcp 65001 >nul
title MangaThaiAI-Studio - 1-Click Auto Deploy
color 0A
cls
echo ========================================================
echo   MangaThaiAI-Studio: Auto Deploy to GitHub and Render
echo ========================================================
echo.
cd /d "D:\code\MangaThaiAI-Studio"
echo [1/3] Checking changed files...
git status -s
echo.
echo [2/3] Staging and committing changes...
git add .
git commit -m "Auto update: sync local changes to cloud" 2>nul
echo.
echo [3/3] Pushing to GitHub (main branch)...
git branch -M main
git push -u origin main
echo.
echo ========================================================
echo   SUCCESS! Latest code pushed to GitHub.
echo   Render is now automatically deploying your updates.
echo.
echo   - Web App URL: https://mangathaiai-studio.onrender.com
echo   - Dashboard:   https://dashboard.render.com
echo ========================================================
echo.
pause
