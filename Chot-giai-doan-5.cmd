@echo off
setlocal
cd /d "%~dp0"
title Luu moc giai doan 5 va day len GitHub
git remote get-url origin | findstr /i /x /c:"https://github.com/Ngocnguyen055/IoT.git" >nul
if errorlevel 1 goto failed
call Kiem-tra.cmd --no-pause
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m scripts.check_active_mongodb
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m scripts.init_db --check
if errorlevel 1 goto failed
git add -- backend/app/migrations backend/app/models backend/app/database.py backend/app/validation.py backend/app/repositories/mongodb.py backend/app/mongodb_config.py project_config.py env_config.py run_local.py connect_device.py requirements.txt .env.example scripts/migrate_mongodb.py scripts/check_migration.py scripts/check_active_mongodb.py scripts/configure_env.py scripts/configure_mongodb.py scripts/check_repository.py scripts/init_db.py scripts/check_schema.py tests/test_migration.py tests/test_cutover.py tests/test_env.py tests/test_models_and_schema.py tests/test_configuration.py tests/test_launchers.py docs/refactor-plan.md docs/mongodb-atlas.md docs/mongodb-migration.md docs/models-and-configuration.md README.md Chuyen-sang-MongoDB.cmd Kiem-tra-chuyen-du-lieu.cmd Chot-giai-doan-5.cmd Khoi-tao-MongoDB.cmd Cai-thu-vien-cau-hinh.cmd
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\check_repository.py --staged
if errorlevel 1 goto failed
git diff --cached --check
if errorlevel 1 goto failed
git diff --cached --quiet
if errorlevel 2 goto failed
if not errorlevel 1 goto push
git commit -m "feat: migrate SQLite data to Atlas with verified cutover"
if errorlevel 1 goto failed
:push
git push -u origin HEAD
if errorlevel 1 goto failed
echo.
echo DA LUU VA DAY GIAI DOAN 5 LEN GITHUB.
git log -1 --oneline
pause
exit /b 0
:failed
echo.
echo CHUA CHOT XONG. Giu cua so nay va gui dong loi phia tren.
pause
exit /b 1
