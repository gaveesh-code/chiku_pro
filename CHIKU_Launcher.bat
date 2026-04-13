@echo off
title Starting CHIKU PRO Ecosystem...

echo [1/2] Making sure Ollama is running in the background...
start /b ollama serve

echo [2/2] Launching CHIKU PRO...
timeout /t 3 >nul
cd /d "%~dp0"

echo [UI] Opening Neural Command Center...
start "" "%~dp0chiku_ui.html"

python main.py

pause
