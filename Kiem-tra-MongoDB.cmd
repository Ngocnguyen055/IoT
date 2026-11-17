@echo off
setlocal
cd /d "%~dp0"
title Kiem tra ket noi va API tren MongoDB Atlas
if not exist ".venv\Scripts\python.exe" (
    echo Hay chay Cai-dat.cmd truoc.
    goto failed
)
".venv\Scripts\python.exe" -c "import pymongo, dns" >nul 2>nul
if errorlevel 1 (
    echo Hay chay Cai-dat.cmd truoc.
    goto failed
)
".venv\Scripts\python.exe" -m scripts.check_mongodb
if errorlevel 1 goto failed
if /i "%~1"=="--no-pause" exit /b 0
pause
exit /b 0
:failed
echo.
echo KIEM TRA ATLAS CHUA DAT. Giu cua so nay de xem loi.
if /i "%~1"=="--no-pause" exit /b 1
pause
exit /b 1
