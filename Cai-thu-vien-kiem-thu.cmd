@echo off
setlocal
cd /d "%~dp0"
title Cai thu vien kiem thu Python
if not exist ".venv\Scripts\python.exe" (
    echo Hay chay Cai-dat.cmd truoc.
    goto failed
)
if not exist ".runtime" mkdir ".runtime"
echo Dang cai thu vien can cho bo kiem thu Python.
".venv\Scripts\python.exe" -m pip --log .runtime\test-install.log install --index-url https://pypi.org/simple --disable-pip-version-check -r requirements-test.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed
echo.
echo DA CAI THU VIEN KIEM THU.
if /i "%~1"=="--no-pause" exit /b 0
pause
exit /b 0
:failed
echo.
echo CAI THU VIEN CHUA THANH CONG. Giu cua so de xem loi.
if /i "%~1"=="--no-pause" exit /b 1
pause
exit /b 1
