@echo off
setlocal
cd /d "%~dp0"
title Cloudflare - ket noi thiet bi SOS
if not exist ".venv\Scripts\python.exe" (
    echo Hay chay Cai-dat.cmd truoc.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" connect_device.py
if errorlevel 1 pause
