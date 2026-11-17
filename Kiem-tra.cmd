@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Hay chay Cai-dat.cmd truoc.
    exit /b 1
)
".venv\Scripts\python.exe" -c "import pymongo, mongomock, dns" >nul 2>nul
if errorlevel 1 (
    echo Hay chay Cai-thu-vien-MongoDB.cmd de cai thu vien kiem thu con thieu.
    goto failed
)
".venv\Scripts\python.exe" -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\check_frontend.py
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\check_repository.py
if errorlevel 1 goto failed
echo.
echo KIEM TRA PHAN MEM DAT. Du lieu kiem thu nam trong database tam.
if /i "%~1"=="--no-pause" exit /b 0
pause
exit /b 0
:failed
echo KIEM TRA CHUA DAT. Xem thong bao phia tren.
if /i "%~1"=="--no-pause" exit /b 1
pause
exit /b 1
