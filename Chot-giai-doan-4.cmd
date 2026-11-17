@echo off
setlocal
cd /d "%~dp0"
title Luu moc giai doan 4 va day len GitHub
if not exist ".venv\Scripts\python.exe" (
    echo Hay chay Cai-dat.cmd truoc.
    goto failed
)
git remote get-url origin | findstr /i /x /c:"https://github.com/Ngocnguyen055/IoT.git" >nul
if errorlevel 1 (
    echo Remote origin khong dung repo IoT da duoc chon. Chua commit/push.
    goto failed
)
echo Dang kiem tra phan mem va cac file du kien dua len Git...
call Kiem-tra.cmd --no-pause
if errorlevel 1 goto failed
call Kiem-tra-MongoDB.cmd --no-pause
if errorlevel 1 goto failed
echo Dang stage cac file cua giai doan 4...
git add -- backend project_config.py .gitignore requirements.txt requirements-test.txt Cai-dat.cmd Cai-thu-vien-MongoDB.cmd Tao-cau-hinh-MongoDB.cmd Kiem-tra-MongoDB.cmd Kiem-tra.cmd mongodb.example.json scripts tests docs README.md config.example.json Chot-giai-doan-4.cmd
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\check_repository.py --staged
if errorlevel 1 goto failed
git diff --cached --check
if errorlevel 1 goto failed
git diff --cached --quiet
if errorlevel 2 goto failed
if not errorlevel 1 goto push
git commit -m "feat: add Atlas repository and isolated MongoDB verification"
if errorlevel 1 goto failed
:push
git push -u origin HEAD
if errorlevel 1 goto failed
echo.
echo DA LUU VA DAY GIAI DOAN 4 LEN GITHUB.
git log -1 --oneline
pause
exit /b 0
:failed
echo.
echo CHUA CHOT XONG. Giu cua so nay va gui dong loi phia tren.
pause
exit /b 1
