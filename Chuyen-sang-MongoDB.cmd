@echo off
setlocal
cd /d "%~dp0"
title Chuyen du lieu web SOS sang MongoDB Atlas
if not exist ".venv\Scripts\python.exe" (
    echo Hay chay Cai-dat.cmd truoc.
    goto failed
)
".venv\Scripts\python.exe" -c "import pymongo, dns" >nul 2>nul
if errorlevel 1 (
    echo Hay chay Cai-dat.cmd truoc.
    goto failed
)
".venv\Scripts\python.exe" -m scripts.migrate_mongodb
if errorlevel 1 goto failed
if /i "%~1"=="--no-pause" exit /b 0
pause
exit /b 0
:failed
echo.
echo CHUA CHUYEN XONG. Giu cua so nay va gui dong loi phia tren.
if /i "%~1"=="--no-pause" exit /b 1
pause
exit /b 1
