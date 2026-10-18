# Windows 一键真实数据验收

更新 PR #21 后，在项目目录双击：

\`backend\\windows_acceptance.cmd\`

脚本以只读方式检查：

- \`backend\\market_cache.sqlite3\`
- \`backend\\strategy_a_results.sqlite3\`
- 数据库大小、行情最新交易日、daily 行数、股票数
- \`001246.SZ\` 日线数量
- 最新有效策略 A 扫描日期、股票数和信号数

脚本还会运行 V4 只读 Flask test_client smoke check，检查：

- \`/strategy/a/v4\`
- \`/strategy/a/v4/stock/001246.SZ\`

旧 V3 的 \`/\` 和 \`/stock/001246.SZ\` 会标记为 \`SKIPPED_READ_ONLY\`，因为它们的历史数据访问层可能执行可写初始化；脚本不会为了验收冒险写入行情库。

报告写入 \`work\\acceptance_report.txt\`，包含状态码、数据可见性和具体错误。退出码含义：

- \`0\`：行情库和有效策略结果均可验证；
- \`1\`：行情库缺失、不可读或结构异常，验收中止；
- \`2\`：行情库可用，但策略结果库缺失、结构异常或没有有效 scan，网页可启动但策略结果为未验证。

数据库使用 SQLite \`mode=ro\`，脚本不会调用 Tushare、盘后更新、全量扫描，也不会建立或迁移表。Flask 启动后会轮询 \`/strategy/a/v4/status\`，明确显示服务是否已就绪。
