@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows_autostart_install.ps1"
if errorlevel 1 echo Installation was cancelled or failed.
pause
