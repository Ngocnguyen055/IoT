@echo off
setlocal
cd /d "%~dp0"
title Luu moc giai doan 3 va day len GitHub
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
echo Dang stage cac file cua giai doan 3...
git add -- frontend backend/app/__init__.py .gitignore .gitattributes Kiem-tra.cmd scripts/check_frontend.py scripts/check_repository.py tests/frontend tests/test_frontend_assets.py tests/test_backup_and_repository.py docs README.md Huong-dan-chay-web.md Chot-giai-doan-3.cmd
if errorlevel 1 goto failed
for %%D in (static templates) do (
    git ls-files -- %%D | findstr /r "." >nul
    if not errorlevel 1 (
        git add --all -- %%D
        if errorlevel 1 goto failed
    )
)
".venv\Scripts\python.exe" scripts\check_repository.py --staged
if errorlevel 1 goto failed
git diff --cached --check
if errorlevel 1 goto failed
git diff --cached --quiet
if errorlevel 2 goto failed
if not errorlevel 1 goto push
git commit -m "refactor: split dashboard frontend into browser modules"
if errorlevel 1 goto failed
:push
git push -u origin HEAD
if errorlevel 1 goto failed
echo.
echo DA LUU VA DAY GIAI DOAN 3 LEN GITHUB.
git log -1 --oneline
pause
exit /b 0
:failed
echo.
echo CHUA CHOT XONG. Giu cua so nay va gui dong loi phia tren.
pause
exit /b 1
