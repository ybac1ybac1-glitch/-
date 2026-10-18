# Windows 一键真实数据验收

更新 PR #21 后，在项目目录双击：

\`backend\\windows_acceptance.cmd\`

脚本只读检查：

- \`backend\\market_cache.sqlite3\`
- \`backend\\strategy_a_results.sqlite3\`
- 数据库大小、行情最新交易日、daily 行数、股票数
- \`001246.SZ\` 日线数量
- 最新有效策略 A 扫描日期、股票数和信号数

报告写入 \`work\\acceptance_report.txt\`。数据库使用 SQLite \`mode=ro\`，脚本不会调用 Tushare、盘后更新、全量扫描，也不会建立或迁移表。

脚本随后在新窗口启动 \`python app.py\`，监听 \`127.0.0.1:8000\`。打开报告中的四个 URL 检查页面。结果库不存在或无有效快照时，页面会显示可读错误或空状态，不会伪造结果。
