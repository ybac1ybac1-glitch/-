@echo off
setlocal
cd /d "%~dp0"
if not exist market_cache.sqlite3 (
  echo 未找到 backend\market_cache.sqlite3，请先放置本地行情缓存。
  exit /b 1
)
echo 启动 Flask：http://127.0.0.1:8000
python app.py
