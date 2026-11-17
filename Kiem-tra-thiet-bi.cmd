@echo off
setlocal
cd /d "%~dp0"
title Kiem tra du lieu moi tu thiet bi SOS
if /i "%~1"=="--start" (
    ".venv\Scripts\python.exe" -m scripts.check_device --start
) else (
    ".venv\Scripts\python.exe" -m scripts.check_device
)
if errorlevel 1 goto failed
pause
exit /b 0
:failed
echo CHUA DOC DUOC DU LIEU THIET BI. Giu cua so nay de xem thong bao.
pause
exit /b 1
