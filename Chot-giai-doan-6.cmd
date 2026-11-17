@echo off
setlocal
cd /d "%~dp0"
title Luu moc thu thiet bi that va day len GitHub
git remote get-url origin | findstr /i /x /c:"https://github.com/Ngocnguyen055/IoT.git" >nul
if errorlevel 1 goto failed
call Kiem-tra.cmd --no-pause
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m scripts.check_device --require-complete
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m scripts.check_active_mongodb
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m scripts.init_db --check
if errorlevel 1 goto failed
git add -- Chay-web.cmd Kiem-tra-thiet-bi.cmd Chot-giai-doan-6.cmd scripts/check_device.py tests/test_device_observation.py Huong-dan-chay-web.md docs/device-verification.md docs/refactor-plan.md README.md
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\check_repository.py --staged
if errorlevel 1 goto failed
git diff --cached --check
if errorlevel 1 goto failed
git diff --cached --quiet
if errorlevel 2 goto failed
if not errorlevel 1 goto push
git commit -m "test: verify device uploads and finish runtime guidance"
if errorlevel 1 goto failed
:push
git push -u origin HEAD
if errorlevel 1 goto failed
echo.
echo DA LUU VA DAY GIAI DOAN 6 LEN GITHUB.
git log -1 --oneline
pause
exit /b 0
:failed
echo CHUA CHOT XONG. Giu cua so nay va gui dong loi phia tren.
pause
exit /b 1
