@echo off
setlocal
cd /d "%~dp0"
echo 正在进行只读数据库检查和 V4 页面 smoke check...
python acceptance_check.py --root "%~dp0.." --report "%~dp0..\work\acceptance_report.txt" --smoke
set "CHECK=%ERRORLEVEL%"
if "%CHECK%"=="1" (
  echo 行情数据库不可用或结构异常，验收中止。
  pause
  exit /b 1
)
if "%CHECK%"=="2" echo 策略结果库缺失或无有效 scan：网页可启动，但策略结果保持“未验证”。
if not exist "%~dp0market_cache.sqlite3" (
  echo 未找到 backend\market_cache.sqlite3，无法启动真实数据验收。
  pause
  exit /b 1
)
echo 报告已生成：%~dp0..\work\acceptance_report.txt
echo 启动 Flask（只监听 127.0.0.1:8000）...
start "A股策略A V4 Flask" /D "%~dp0" cmd /k python app.py
echo 正在等待 Flask 就绪（最多 20 秒）...
set "READY=0"
for /L %%N in (1,1,20) do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/strategy/a/v4/status -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } } catch {} ; exit 1"
  if not errorlevel 1 (
    set "READY=1"
    goto :ready
  )
  timeout /t 1 /nobreak >nul
)
:ready
if "%READY%"=="1" (
  echo Flask 已就绪：http://127.0.0.1:8000
) else (
  echo 未验证 Flask 是否就绪，请查看新窗口和 acceptance_report.txt。
)
echo 页面地址：
echo   http://127.0.0.1:8000/
echo   http://127.0.0.1:8000/stock/001246.SZ
echo   http://127.0.0.1:8000/strategy/a/v4
echo   http://127.0.0.1:8000/strategy/a/v4/stock/001246.SZ
pause
