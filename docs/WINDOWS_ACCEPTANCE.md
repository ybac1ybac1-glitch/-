# Windows 一键真实数据验收

如果已经用独立工具写入了新的日线（例如 20261016），先双击：

\`backend\\verify_latest_cached_date.cmd\`

该脚本：

1. 自动识别 daily 最大交易日；
2. 在创建不覆盖旧备份的新备份后检查该日 OHLCV 和换手率；
3. 只有真实数据完整时才写入 \`history_date_tasks\` 的 \`OHLCV_COMPLETE/ TURNOVER_COMPLETE\`；
4. 缺行情、异常 OHLCV 或缺换手率时写入 PARTIAL_MISSING/FAILED，绝不伪造 COMPLETE；
5. 不下载历史行情，不覆盖行情行，不调用策略扫描。

验证成功后双击：

\`backend\\windows_acceptance.cmd\`

它会读取完整性状态，运行 V4 只读 smoke check，并启动 Flask。V4 扫描会选择最新经过完整性验证且 daily 中存在的交易日；如果新日期未完成，页面会明确保持旧的完整日期或显示未验证状态，不会把旧日期冒充新行情。

两个脚本均要求数据库路径可访问，支持中文和空格路径；报告写入 \`work\\acceptance_report.txt\`。
