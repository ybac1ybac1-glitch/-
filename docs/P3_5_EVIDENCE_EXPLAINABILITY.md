# P3.5 证据持久化与可解释性

## 链路

`strategy_a._ev()` 计算并放入 Evidence.evidence；`validation._compact()` 保留完整 evidence，并增加 `evidence_version=A-EVIDENCE-1`；`strategy_a_store.py` 原样 JSON 保存；`strategy_a_audit.py` 同时读取新版嵌套 evidence 和旧版扁平字段；V4 详情页将参数、关键指标、事件字段和完整性状态以中文展示。

A01/A02 的真实计算字段来自策略中的区间/量价字典；A03-A06 的事件 ID、日期、冻结区间和 transition 来自 replay_events；A07-A09 使用策略实际输出的背景/风险字段。没有计算或没有持久化的字段不填默认值，报告为“持久化证据不足”。

## 旧库兼容

旧结果库中的扁平 evidence 仍可读取；没有 `evidence_version` 的信号显示“旧版/未标注”和历史证据不足。新扫描才产生 A-EVIDENCE-1。不会重写、删除或补算旧快照。

## 验收命令

```cmd
set PYTHONPATH=backend
python -m strategy_a_audit ^
  --results backend\strategy_a_results.sqlite3 ^
  --market backend\market_cache.sqlite3 ^
  --json work\strategy_a_audit.json
python backend\app.py
```

详情页入口：`/strategy/a/v4/stock/<ts_code>`。本阶段不改阈值、不调用 Tushare、不扫描全市场。
