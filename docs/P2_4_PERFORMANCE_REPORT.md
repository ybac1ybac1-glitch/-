# P2.4 性能诊断与优化

本 PR 使用合成 OHLCV 对 80/120/240/359 根 K 线执行 replay_events，并用旧版逐前缀 DataFrame.copy 路径与数组化区间路径做一致性比较。优化仅改变区间计算实现，不改变 A01–A09、冻结边界、事件 ID、状态转换或未来数据约束。

优化点：`_event_ranges()` 直接使用 NumPy 数组计算分位数、斜率、稳定性和边界测试，避免每个历史前缀创建 DataFrame。`detect_range()` 作为公开/测试纯函数保留；数组实现输出字段与旧实现逐项一致。

P2.3 验证器新增 `max_stocks`（默认 None 表示全量）和 `console_progress`（默认 False），开启时每 100 只输出 processed、total、耗时、平均每股耗时和预计剩余时间。该限制只用于本机性能诊断。

CI 不访问用户数据库或 Token。真实 359 日、5615 只股票的耗时必须在用户本机使用 `validate_cache(..., max_stocks=10/50/100)` 实测；本 PR 不宣称已完成真实市场扫描。


## 最终基准验收

新增测试中的旧版基准严格复现 PR #6 前的逐前缀 `DataFrame.iloc` + `detect_range` 路径，并通过临时替换 `_event_ranges` 调用同一 `replay_events` 状态机。对 80、120、240、359 根 K 线逐项比较事件 ID、事件日期、状态、transition_history、冻结支撑/阻力、冻结量能基准及全部 Evidence 字段；测试失败即阻断合并。每个长度旧版和新版各重复 3 次，取最小耗时，输出实际毫秒数和 speedup 倍数。测试环境为 GitHub Actions Ubuntu runner、Python 3.11、pytest、numpy/pandas，具体数值见 Actions 日志；未使用真实行情数据库或 Token。
