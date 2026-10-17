# P3.2 策略 A V4 图形化 K 线

详情入口：`/strategy/a/v4/stock/<ts_code>`。页面使用本地 SQLite 日线数据，以 Canvas 绘制 OHLC 蜡烛和成交量柱，支持最近 60、120、250 个交易日切换、悬停提示、事件标记和数字表格核对。

JSON 接口：`/strategy/a/v4/stock/<ts_code>/data?days=60|120|250`。接口使用 SQLite `mode=ro`，按交易日升序返回真实 OHLC、涨跌幅、成交量和成交额；不存在股票返回 404，非法范围返回 400。查看详情不调用 Tushare、公告、新闻，也不触发策略扫描或写入数据库。

事件标记来自 `strategy_a_results.sqlite3` 当前有效扫描快照。仅显示已有日期、规则、状态和证据；CANDIDATE、CONFIRMED、INVALIDATED 使用不同颜色，缺少证据时不生成标记。

Windows 启动：

```cmd
set PYTHONPATH=backend
python backend\app.py
```

浏览器打开 `http://127.0.0.1:8000/strategy/a/v4`，再点击股票详情。图表脚本为项目内静态 Canvas 实现，无运行时公网依赖；当前版本未实现分钟 K、实时行情、技术指标叠加或复杂拖拽图形交互，缩放/平移可继续在后续阶段扩展。
