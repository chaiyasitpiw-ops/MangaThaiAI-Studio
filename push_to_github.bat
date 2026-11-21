@echo off
title MangaThaiAI-Studio - Pushing to GitHub...
color 0A
cls
echo ========================================================
echo   Pushing code to GitHub: chaiyasitpiw-ops/MangaThaiAI-Studio
echo ========================================================
echo.
cd /d "D:\code\MangaThaiAI-Studio"
git branch -M main
git push -u origin main
echo.
echo ========================================================
echo   Finished! You can now visit: https://dashboard.render.com
echo ========================================================
echo.
pause
