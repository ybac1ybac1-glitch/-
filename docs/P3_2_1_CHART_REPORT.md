# P3.2.1 专业 K 线图表

本 PR 在现有 Canvas 方案上增强桌面复盘：右侧真实价格轴、底部交易日轴、顶部 OHLC/涨跌幅/成交量/成交额栏、十字光标、MA5/MA10/MA20、滚轮缩放、拖动平移和 60/120/250 日切换。

数据仍来自本地 `market_cache.sqlite3`，通过 SQLite `mode=ro` 查询；不调用 Tushare，不修改行情库和结果库，不触发策略扫描。成交量展示保留 SQLite 原始单位并明确标注，未擅自换算“手/股”。价格保持数据库现有不复权口径。

事件和冻结线继续使用已保存信号证据；只有有限数值且事件日期在当前可见数据范围内才绘制。MA 按升序交易日的收盘价计算，前 N 日不足时不绘制。

本实现不引入第三方图表库，无 CDN、无额外许可证和 Node.js 运行时依赖；Canvas 是浏览器原生 API。Node.js 仅在 CI 中用于 JavaScript 语法测试。

Windows 启动：

```cmd
set PYTHONPATH=backend
python backend\app.py
```

访问 `http://127.0.0.1:8000/strategy/a/v4` 后进入股票详情。当前未加入实时行情、分钟 K 线、复权切换和复杂动画。
