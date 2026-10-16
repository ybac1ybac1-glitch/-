# P2.3 真实行情只读验证

## 使用

验证程序只读打开 SQLite（`mode=ro`），按 ts_code 分批读取 daily，按 asof_date 截断后调用 strategy_a.scan/replay_events。不会建立表、写入行情或调用 Tushare。

Windows CMD 示例：

```cmd
set PYTHONPATH=backend
python -c "from validation import validate_cache; import json; print(json.dumps(validate_cache(r'backend\\market_cache.sqlite3','20261015'),ensure_ascii=False,indent=2))"
```

网页 JSON 接口：`GET /strategy/a/validate?asof_date=YYYYMMDD&batch_size=100`。输出扫描股票数、数据不足、规则命中、异常和失败原因。结果是研究候选证据，不是可成交买点。Codex CI 使用临时 SQLite 和合成行情，未执行用户本机真实验证。
