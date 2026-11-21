@echo off
chcp 65001 >nul
title MangaThaiAI-Studio ⚡ iPhone & iPad 24H
color 0B
cls

"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\launcher_iphone.py"

pause
