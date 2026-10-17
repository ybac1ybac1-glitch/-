# P3.1 策略 A V4 首版网页

入口：`/strategy/a/v4`。POST `/strategy/a/v4/start` 启动后台只读复盘，结果保存到独立 `backend/strategy_a_results.sqlite3`；GET 页面、状态和分页只读取保存结果，不触发全市场扫描。`max_stocks` 仅用于部分样本性能测试，正式默认全市场。用户 Windows 启动：在项目根目录运行 `set PYTHONPATH=backend` 后启动 Flask；首次点击开始复盘，完成后可反复打开页面。
