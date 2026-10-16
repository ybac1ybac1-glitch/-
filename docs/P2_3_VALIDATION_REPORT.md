# P2.3 真实行情只读验证

## 使用

验证程序只读打开 SQLite（`mode=ro`），按 ts_code 分批读取 daily，按 asof_date 截断后调用 strategy_a.scan/replay_events。不会建立表、写入行情或调用 Tushare。

Windows CMD 示例：

```cmd
set PYTHONPATH=backend
python -c "from validation import validate_cache; import json; print(json.dumps(validate_cache(r'backend\\market_cache.sqlite3','20261015'),ensure_ascii=False,indent=2))"
```

网页 JSON 接口：`GET /strategy/a/validate?asof_date=YYYYMMDD&batch_size=100`。输出扫描股票数、数据不足、规则命中、异常和失败原因。结果是研究候选证据，不是可成交买点。Codex CI 使用临时 SQLite 和合成行情，未执行用户本机真实验证。


## 日期与结果安全

复盘日期必须为 YYYYMMDD；缺省时取 daily 中最大可解析交易日。未来日期和无效日期被拒绝。每只股票若没有 asof_date 当日 K 线，标记 NO_BAR_ON_ASOF，不以前一日冒充。当日结果仅保留命中规则的精简信号摘要、统计计数和最多 20 条错误样本，完整事件历史不进入全量 results。


## 服务安全

GET `/strategy/a/validate` 只返回后台任务状态；POST 才能启动受控任务，同一时刻只允许一个任务。`batch_size` 和 `max_results` 有范围校验。扫描结果限制最大保留数量，统计字段 `total_matches`、`returned_matches`、`truncated` 明确区分完整统计与分页结果。连接使用 SQLite `mode=ro` 和 `PRAGMA query_only=ON`。
