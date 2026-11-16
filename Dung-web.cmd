@echo off
setlocal
set "SOS_PROJECT=%~dp0"
title Dung web SOS
powershell.exe -NoProfile -Command "$ErrorActionPreference = 'Stop'; try { $pythonExe = Join-Path $env:SOS_PROJECT '.venv\Scripts\python.exe'; $servers = @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $pythonExe -and $_.CommandLine -match 'run_local\.py(?:\s|$)' }); if ($servers.Count -eq 0) { Write-Output 'Khong tim thay web dang chay.' } else { $servers | ForEach-Object { Stop-Process -Id $_.ProcessId }; Write-Output 'Da dung web SOS.' } } catch { Write-Output ('Loi: ' + $_.Exception.Message); exit 1 }"
pause
