@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "%~dp0market_cache.sqlite3" (
  echo market_cache.sqlite3 was not found.
  exit /b 1
)
set "BACKUP=%~dp0..\work\market_cache_before_verify_%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%_%RANDOM%.sqlite3"
echo Creating a new backup and verifying the latest cached trade date...
python "%~dp0history_extension.py" --db "%~dp0market_cache.sqlite3" --trade-date latest --backup "%BACKUP%"
if errorlevel 1 (
  echo Verification failed. Existing database was not replaced.
  exit /b 1
)
echo Verification finished. Backup: "%BACKUP%"
echo Run windows_acceptance.cmd to inspect and start Flask.
pause
