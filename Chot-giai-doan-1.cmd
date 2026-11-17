@echo off
setlocal
cd /d "%~dp0"
title Luu moc giai doan 1 va day len GitHub
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
echo Dang stage cac file cua giai doan 1...
git add -- .gitignore .gitattributes README.md Kiem-tra.cmd Chot-giai-doan-1.cmd config.example.json project_config.py app.py run_local.py connect_device.py Huong-dan-chay-web.md "*.txt" docs scripts firmware/ESP32_Firmware/ESP32_Firmware.ino firmware/ESP32_Firmware/README.md firmware/ESP32_Firmware/device_config.example.h tests/test_api.py tests/test_configuration.py tests/test_backup_and_repository.py
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\check_repository.py --staged
if errorlevel 1 goto failed
git diff --cached --check
if errorlevel 1 goto failed
git diff --cached --quiet
if errorlevel 2 goto failed
if not errorlevel 1 goto push
git commit -m "test: establish phase 1 baseline and local configuration"
if errorlevel 1 goto failed
:push
git push -u origin HEAD
if errorlevel 1 goto failed
echo.
echo DA LUU VA DAY GIAI DOAN 1 LEN GITHUB.
git log -1 --oneline
pause
exit /b 0
:failed
echo.
echo CHUA CHOT XONG. Giu cua so nay va gui dong loi phia tren.
pause
exit /b 1
