@echo off
setlocal
cd /d "%~dp0"
title Khoi tao model va schema MongoDB
".venv\Scripts\python.exe" -m scripts.init_db
if errorlevel 1 goto failed
if /i "%~1"=="--no-pause" exit /b 0
pause
exit /b 0
:failed
echo KHOI TAO CHUA DAT. Giu cua so nay va gui dong loi phia tren.
if /i "%~1"=="--no-pause" exit /b 1
pause
exit /b 1
