# Windows 一键运行

首次安装（只需一次）：

1. 确保已在项目目录配置用户环境变量 \`TUSHARE_TOKEN\`；
2. 双击 \`backend\\install_autostart.cmd\`；
3. 在确认提示中输入 \`YES\`；
4. 退出并重新登录 Windows。

安装使用当前用户的任务计划，不需要管理员权限。任务名称是 \`AStockStrategyA-V4\`，同名任务会先清理后重新注册，策略设置为 \`IgnoreNew\`，避免重复实例。Token 不写入任务命令、日志或仓库。

登录后任务使用 \`pythonw.exe\` 在后台启动 Flask，并启用自动刷新。它会检查最近交易日、增量更新缺失行情、验证 OHLCV/换手率、成功后启动同日期策略 A 扫描；失败会记录页面可见状态并等待下一次重试。电脑关机期间不会运行。

查看任务状态：双击 \`backend\\status_autostart.cmd\`。取消自启动：双击 \`backend\\uninstall_autostart.cmd\`。

原始行情库和结果库不会被脚本删除、覆盖、重建或迁移。首次真实数据验证仍建议先双击 \`verify_latest_cached_date.cmd\` 生成独立备份，再使用 \`windows_acceptance.cmd\` 检查网页。
