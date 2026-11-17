@echo off
setlocal
cd /d "%~dp0"
title Cai thu vien doc .env
".venv\Scripts\python.exe" -m pip install --index-url https://pypi.org/simple --disable-pip-version-check python-dotenv==1.2.4
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed
echo DA CAI THU VIEN CAU HINH.
pause
exit /b 0
:failed
echo CAI CHUA DAT. Giu cua so nay de xem loi.
pause
exit /b 1
