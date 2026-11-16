@echo off
setlocal
cd /d "%~dp0"
title Cai thu vien cho web SOS

if exist ".venv\Scripts\python.exe" goto install

set "SOS_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%SOS_PYTHON%" goto create
where python >nul 2>nul
if errorlevel 1 goto no_python
set "SOS_PYTHON=python"

:create
"%SOS_PYTHON%" -m venv --copies .venv
if errorlevel 1 goto failed

:install
if not exist ".runtime" mkdir ".runtime"
echo Dang cai Flask tu kho Python chinh thuc. Can ket noi Internet.
".venv\Scripts\python.exe" -m pip --log .runtime\pip-install.log install --index-url https://pypi.org/simple --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed
echo.
echo CAI DAT XONG. Bam dup Chay-web.cmd de mo website.
if /i "%~1"=="--no-pause" exit /b 0
pause
exit /b 0

:no_python
echo Chua tim thay Python. Cai Python tu https://www.python.org/downloads/windows/
echo Roi chay lai file nay.
goto failed

:failed
echo.
echo CAI DAT CHUA THANH CONG. Giu cua so nay de xem thong bao loi.
pause
exit /b 1
