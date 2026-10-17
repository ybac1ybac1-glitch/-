# P3.8 多股票历史审计

Windows CMD：

```cmd
set PYTHONPATH=backend
python -m multi_stock_replay_audit ^
  --db backend\market_cache.sqlite3 ^
  --stocks 000001.SZ,000858.SZ,002594.SZ,300750.SZ,300059.SZ,600519.SH,600036.SH,601318.SH,601899.SH,688981.SH ^
  --json work\p38_multi_audit.json
```

工具使用 SQLite mode=ro，逐股票隔离失败并输出每只股票的 PASS/FAIL/UNVERIFIED、交易日、信号、规则评估、异常案例和覆盖矩阵。缺少逐日持久化历史快照的能力继续为 UNVERIFIED，不用当前重放结果冒充历史保存结果。

等待机制仍以策略参数 `test_days=15`、`lps_wait_days=15` 为准；如果合成数据没有真实触发 Spring/SOS 的第14、15、16个交易日状态，报告会保留 UNVERIFIED。
