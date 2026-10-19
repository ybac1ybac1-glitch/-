@echo off
setlocal EnableExtensions
set AUTO_REFRESH_ENABLED=1\nset AUTO_REFRESH_INTERVAL_SECONDS=300
cd /d "%~dp0"
echo Running read-only database and V4 smoke checks...
python "%~dp0acceptance_check.py" --root "%~dp0.." --report "%~dp0..\work\acceptance_report.txt" --smoke
set "CHECK=%ERRORLEVEL%"
if "%CHECK%"=="1" goto :market_fail
if "%CHECK%"=="2" goto :result_unverified
goto :start_server

:market_fail
echo Market database is missing, unreadable, or has an invalid schema.
goto :finish_error

:result_unverified
echo Strategy result database is missing or has no valid scan. Web pages will show UNVERIFIED.
goto :start_server

:start_server
if not exist "%~dp0market_cache.sqlite3" (
  echo market_cache.sqlite3 was not found.
  goto :finish_error
)
echo Starting Flask on 127.0.0.1:8000...
start "Strategy A Flask" /D "%~dp0" "%ComSpec%" /k python app.py
echo Waiting for Flask readiness...
set "READY=0"
for /L %%N in (1,1,20) do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $x=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/strategy/a/v4/status -TimeoutSec 1; if ($x.StatusCode -eq 200) { exit 0 } } catch {} ; exit 1"
  if not errorlevel 1 (
    set "READY=1"
    goto :ready
  )
  timeout /t 1 /nobreak >nul
)
:ready
if "%READY%"=="1" (
  echo Flask is ready at http://127.0.0.1:8000
) else (
  echo Flask readiness was not verified. Check the server window and acceptance_report.txt.
)
echo URLs:
echo http://127.0.0.1:8000/
echo http://127.0.0.1:8000/stock/001246.SZ
echo http://127.0.0.1:8000/strategy/a/v4
echo http://127.0.0.1:8000/strategy/a/v4/stock/001246.SZ
goto :finish_ok

:finish_error
if /I not "%CI%"=="true" pause
exit /b 1

:finish_ok
if /I not "%CI%"=="true" pause
exit /b 0
