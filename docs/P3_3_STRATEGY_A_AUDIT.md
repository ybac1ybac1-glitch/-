# P3.3 策略 A V4 选股信号与证据审计

## 工具

`backend/strategy_a_audit.py` 以 SQLite `mode=ro` 读取当前有效扫描快照和可选日线库，不调用 Tushare，不重新扫描市场，不写入任何数据库。

Windows CMD（项目根目录）：

```cmd
set PYTHONPATH=backend
python -m strategy_a_audit --results backend\strategy_a_results.sqlite3 --market backend\market_cache.sqlite3 --json work\strategy_a_audit.json
```

结果包含规则 A01-A09 统计、状态分布、证据完整性、重复事件、不可追溯信号、异常行情和代表性样本。没有用户本机数据库时，工具只报告数据库缺失，不能复现用户本地的 92 只命中股票和 127 条信号。

## 口径

- `actual_signal_rows` 是结果表中的信号行数。
- `status_summary` 分别统计 CANDIDATE、CONFIRMED、INVALIDATED；候选不是可成交买点。
- `stock_count` 来自扫描快照的股票级命中数，不能与信号行数混用。
- 重复键按股票、规则、信号日期、事件 ID 检测；跨规则引用同一事件单独列出。
- A03-A06 缺少事件 ID、日期或冻结证据会被列入不可追溯/证据不完整。
- 价格异常、无法在日线库追溯的信号列入可疑清单。

## 审计结论边界

已验证：统计来自当前有效持久化快照，原始数据库和结果数据库使用只读连接，异常和缺失证据可被列出。

证据不足：没有用户本机真实数据库不能复现本地样本；仅凭结果快照不能证明完整历史重放没有未来函数，也不能替代人工判断停牌、ST、涨跌停、复权口径和派发结构。

建议：本阶段不修改 A01-A09 逻辑或阈值。先用工具输出定位证据缺失、重复和异常样本，再由验收决定是否进入逻辑修复阶段。
