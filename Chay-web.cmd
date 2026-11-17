@echo off
setlocal
cd /d "%~dp0"
title Web SOS - giu cua so nay mo
if not exist ".venv\Scripts\python.exe" goto install
".venv\Scripts\python.exe" -c "import flask, pymongo, dns, dotenv" >nul 2>nul
if not errorlevel 1 goto run

:install
call "%~dp0Cai-dat.cmd" --no-pause
if errorlevel 1 exit /b 1

:run
".venv\Scripts\python.exe" run_local.py
if errorlevel 1 pause
