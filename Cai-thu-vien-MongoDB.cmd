@echo off
setlocal
cd /d "%~dp0"
title Cai driver MongoDB Atlas va thu vien kiem thu
if not exist ".venv\Scripts\python.exe" (
    echo Hay chay Cai-dat.cmd truoc.
    goto failed
)
if not exist ".runtime" mkdir ".runtime"
echo Dang cai driver Python de ket noi Atlas va thu vien kiem thu.
".venv\Scripts\python.exe" -m pip --log .runtime\mongodb-install.log install --index-url https://pypi.org/simple --disable-pip-version-check -r requirements-test.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed
echo.
echo DA CAI THU VIEN MONGODB.
if /i "%~1"=="--no-pause" exit /b 0
pause
exit /b 0
:failed
echo.
echo CAI THU VIEN CHUA THANH CONG. Giu cua so de xem loi.
if /i "%~1"=="--no-pause" exit /b 1
pause
exit /b 1
