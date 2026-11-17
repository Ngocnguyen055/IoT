@echo off
setlocal
cd /d "%~dp0"
title Cau hinh ket noi MongoDB Atlas
if not exist ".venv\Scripts\python.exe" (
    echo Hay chay Cai-dat.cmd truoc.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m scripts.configure_mongodb
if errorlevel 1 (
    pause
    exit /b 1
)
pause
exit /b 0
