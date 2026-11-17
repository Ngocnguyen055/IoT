@echo off
setlocal
cd /d "%~dp0"
title Kiem tra phan trang va truy van Atlas
set "PYTHONDONTWRITEBYTECODE=1"
".venv\Scripts\python.exe" -m scripts.check_alert_history
if errorlevel 1 goto failed
if /i "%~1"=="--no-pause" exit /b 0
pause
exit /b 0
:failed
echo KIEM TRA CHUA DAT. Giu cua so nay va gui dong loi phia tren.
if /i "%~1"=="--no-pause" exit /b 1
pause
exit /b 1
