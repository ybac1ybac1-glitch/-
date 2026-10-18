@echo off
setlocal
cd /d "%~dp0"
echo 正在进行只读数据库检查，不会调用 Tushare、更新行情或扫描策略...
python acceptance_check.py --root "%~dp0.." --report "%~dp0..\work\acceptance_report.txt"
if errorlevel 1 (
  echo 验收检查失败，请查看上面的中文提示。
  pause
  exit /b 1
)
if not exist "%~dp0market_cache.sqlite3" (
  echo 未找到 backend\market_cache.sqlite3，无法启动真实数据验收。
  pause
  exit /b 1
)
echo 检查报告已生成：%~dp0..\work\acceptance_report.txt
echo 将启动 Flask，浏览器请访问下列地址：
echo   http://127.0.0.1:8000/
echo   http://127.0.0.1:8000/stock/001246.SZ
echo   http://127.0.0.1:8000/strategy/a/v4
echo   http://127.0.0.1:8000/strategy/a/v4/stock/001246.SZ
start "A股策略A V4 Flask" cmd /k "cd /d %~dp0 && python app.py"
echo Flask 已在新窗口启动。此窗口可以关闭。
pause
