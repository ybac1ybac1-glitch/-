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

## 逐规则证据要求

审计模块按策略 A 实现与 P2.1 规范区分必需字段、可选字段和不适用字段：

|规则|必需字段|可选/不适用|
|---|---|---|
|A01|valid、support、resistance、width、slope、valid_sessions|event_id、冻结边界事件字段不要求|
|A02|recent_volume、base_volume、pullback、liquid|event_id、冻结边界不要求|
|A03|有事件时 event_id、event_date、frozen_support|无事件的 WATCH 可为空|
|A04|有测试事件时 event_id、spring_date、transition|无测试的 WATCH 可为空|
|A05|有 SOS 时 event_id、event_date、frozen_resistance、frozen_volume_baseline|无事件的 WATCH 可为空|
|A06|有 LPS 事件时 event_id、sos_date、transition|无 LPS 的 WATCH 可为空|
|A07|volume_effort、price_result|不要求事件 ID|
|A08|price_up、volume_down|不要求事件 ID|
|A09|risk_conditions、independent_conditions|不要求事件 ID|

## 两层结论

持久化结果审计统计已执行：规则字段、状态、重复记录、信号/股票计数、行情追溯和 OHLC 有限性/边界检查。

策略逻辑审计仍标记为“未验证”：仅凭保存结果不能证明 A01–A09 的逐日条件、冻结区间、15 日等待、状态终态和未来数据约束全部正确；这些需要独立回放和人工核对。审计模块不会调整阈值或生成新信号。

### 持久化字段边界

审计报告同时输出 `persistence_audit.strategy_fields`、`validation_fields` 和 `persisted_fields`。策略计算字段来自 `strategy_a.py` 的规则 Evidence；validation 层负责传递结果；结果库只审计实际 JSON evidence 中保存的字段。策略计算过但未持久化的字段标记为“持久化证据不足，无法验证”，不等同于策略条件错误。

旧版 daily 表若没有 `amount`，报告会显示“数据库未提供 amount 字段”，仍可校验 OHLCV；只有 OHLCV 缺失、非有限、非正或边界非法时才标记行情异常。