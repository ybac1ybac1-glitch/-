# P3.4 策略 A V4 数据追溯与证据持久化

本阶段只修复审计准确性，不修改 A01-A09 阈值或计算逻辑。

## 追溯口径

审计对每条信号分别统计：

- `market_rows_checked`：尝试匹配的行情行数。
- `market_rows_matched`：成功按股票代码和日期匹配的行数。
- `market_rows_missing`：确实不存在对应行情的行数。

日期匹配同时兼容 `2026-10-15`、`20261015` 和斜线格式。旧版 daily 缺少 amount 时报告“数据库未提供 amount 字段”，不把合法 OHLCV 误判为缺失成交额。

## 证据链

`strategy_a.py` 计算规则 Evidence；`validation.py` 将 Evidence 压缩为结果信号字段；`strategy_a_store.py` 将压缩字段写入结果库；审计工具只判断实际持久化 JSON。报告输出 `persistence_audit.strategy_fields`、`validation_fields`、`persisted_fields`。策略计算过但未保存的字段标记“持久化证据不足，无法验证”，不能推断策略条件错误。

## 状态语义

全部 CANDIDATE 可能是正常的候选快照，也可能反映扫描日期没有后续确认数据。审计不为了制造 CONFIRMED 而修改策略；仅凭结果库不能证明历史状态转换正确。

Windows 命令：

```cmd
set PYTHONPATH=backend
python -m strategy_a_audit ^
  --results backend\strategy_a_results.sqlite3 ^
  --market backend\market_cache.sqlite3 ^
  --json work\strategy_a_audit.json
```

命令只读打开两个数据库，不调用 Tushare，也不重新扫描全市场。
