# P3.8.1 多股票历史审计性能与断点续跑

本版本保持逐日重放和 PASS/FAIL/UNVERIFIED 判定不变，只增加可观测性和可靠恢复。

## 运行

在仓库的 \`backend\` 目录执行：

\`\`\`cmd
python -m multi_stock_replay_audit --db market_cache.sqlite3 --results-db strategy_a_results.sqlite3 --asof 20261015 --checkpoint ..\\work\\p38_multi_audit.checkpoint.json --json ..\\work\\p38_multi_audit.json
\`\`\`

进度和心跳写入 stderr，因此即使 stdout 被重定向，仍能看到每只股票的开始、完成、耗时和状态。每完成一只股票，检查点通过同目录临时文件和原子替换写入。Ctrl+C 会保留已完成股票；再次使用相同数据库、股票列表、截止日期、策略版本和审计配置运行时，只重放未完成股票。

检查点仅表示部分输入已处理，不能作为最终 PASS 报告。若输入、策略版本或配置改变，检查点会被标记为不匹配并从头执行。最终 JSON 仅在完整运行结束时写出；中断时应检查 checkpoint 文件。

## 报告字段

\`processed\` 是本次（含恢复项）已处理股票数；\`completed\`/\`stocks_audited\` 是成功进入审计并返回非 UNVERIFIED 的股票数；\`failed\` 是审计异常数；\`unverified\` 是无行情、截止日期不足或审计本身返回 UNVERIFIED 的股票数。\`timing.per_stock\` 和 \`timing.elapsed_seconds\` 用于性能诊断。逐股票结果仍由现有 \`history_replay_audit.audit_frame\` 生成，未减少交易日、规则或状态转换检查。

## 性能说明

原始热点是逐日 \`audit_frame\` 中对每个历史前缀执行真实 scan/replay（包括区间检测和 DataFrame 前缀准备），其复杂度随交易日平方增长。本版本首先记录每股和总耗时，减少批处理层重复日期解析，并提供逐股断点恢复；没有用跳过规则或减少历史天数换取速度。后续若要改变核心回放计算，应另行做结果逐字段一致性基准。

## 安全

行情库和结果库均以 SQLite \`mode=ro\` 打开并在 finally 关闭。检查点和最终报告是独立 JSON 文件，不写入任何 SQLite 数据库。
