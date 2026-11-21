@echo off
chcp 65001 >nul
title MangaThaiAI-Studio 🚀 Deploy to Cloud 24H (Hugging Face)
color 0A
cls

"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\deploy_hf.py"

pause
