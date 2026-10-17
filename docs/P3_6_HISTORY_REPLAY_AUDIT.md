# P3.6 逐日历史重放与未来函数审计

工具：`backend/history_replay_audit.py`。输入单只股票 DataFrame/CSV，按每个交易日截断调用真实 `strategy_a.scan()` 和 `replay_events()`，并与包含后续数据但仍以同一 asof 截止的结果比较。

报告字段：

- `trading_days_checked`、`signals_checked`
- `future_leakage_count`
- `state_transition_anomalies`
- `frozen_evidence_anomalies`
- `repeatability_anomalies`
- A01-A09 覆盖矩阵
- 具体案例与未验证项目

PASS 只表示本次合成输入审计执行且没有发现差异；无法从历史结果库证明的线上历史快照、停牌、涨跌停、复权和分钟数据仍标记 UNVERIFIED。工具不修改策略、不写数据库、不调用 Tushare。

Windows 小样本：

```cmd
set PYTHONPATH=backend
python -m history_replay_audit --csv work\sample_600001.csv --symbol 600001.SH --json work\p36_replay.json
```

本阶段不执行全市场扫描，不自动修复发现的策略问题。
