@echo off
setlocal
cd /d "%~dp0"
title Luu moc giai doan 2 va day len GitHub
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
echo Dang stage cac file cua giai doan 2...
git add -- backend app.py run_local.py README.md docs tests/test_api.py tests/test_factory.py tests/test_launchers.py Chot-giai-doan-2.cmd
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\check_repository.py --staged
if errorlevel 1 goto failed
git diff --cached --check
if errorlevel 1 goto failed
git diff --cached --quiet
if errorlevel 2 goto failed
if not errorlevel 1 goto push
git commit -m "refactor: split Flask backend into application modules"
if errorlevel 1 goto failed
:push
git push -u origin HEAD
if errorlevel 1 goto failed
echo.
echo DA LUU VA DAY GIAI DOAN 2 LEN GITHUB.
git log -1 --oneline
pause
exit /b 0
:failed
echo.
echo CHUA CHOT XONG. Giu cua so nay va gui dong loi phia tren.
pause
exit /b 1
