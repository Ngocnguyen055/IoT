@echo off
setlocal
cd /d "%~dp0"
title Kiem tra chuyen du lieu tren Atlas tam
".venv\Scripts\python.exe" -m scripts.check_migration
if errorlevel 1 goto failed
if /i "%~1"=="--no-pause" exit /b 0
pause
exit /b 0
:failed
echo KIEM TRA CHUA DAT. Giu cua so nay de xem loi.
if /i "%~1"=="--no-pause" exit /b 1
pause
exit /b 1
