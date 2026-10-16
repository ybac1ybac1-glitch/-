# 历史行情扩展至 360 个交易日方案

## 权限检查方法

在用户本机设置 `TUSHARE_TOKEN` 后，先用最小请求验证：

1. `trade_cal(exchange='SSE', start_date=..., end_date=..., is_open='1')`：确认交易日历权限和返回字段 `cal_date/is_open`。
2. `daily(trade_date=最近缺失日)`：确认日线权限、返回非空、字段包含 `ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount`。
3. `daily_basic(trade_date=最近缺失日, fields='ts_code,trade_date,turnover_rate')`：确认换手率权限；失败只记录缺失，不填造。

所有请求经现有 60 次/分钟限流器；权限失败、积分不足、空返回和字段不全写入任务错误与缺失统计。

## 增量流程

任务先从交易日历取得最近 360 个已开市日期，再查询本地 `daily` 的不同交易日集合，只请求缺失日期。每个日期依次请求 `daily` 与 `daily_basic`，使用 `(ts_code,trade_date)` UPSERT；已有 OHLCV 不因换手率缺失而覆盖。单日期成功后立即提交并记录 `completed_dates`，异常可从剩余日期继续。任务与现有行情更新/换手率回填共享 `_task_lock`，不会并发写库。

本实现不在 Flask 启动或首页访问时自动执行，只能通过 `POST /admin/history-extend` 主动触发；状态通过 `GET /admin/update/status` 查看。用户应在 Windows 先备份：

```cmd
copy backend\market_cache.sqlite3 backend\market_cache.sqlite3.360.bak
```

回滚只需停止程序并恢复备份；任务不会删除、重建或清空数据库。

## 完整性验收

数据健康页应以 `COUNT(DISTINCT trade_date)` 展示全市场日期覆盖，并按 `ts_code` 统计每只股票有效日期数；另统计 OHLCV、成交额、换手率的 NULL 数量。360 日完成前，相关长期规则仍显示数据不足。真实 Token、真实数据库和大规模回填必须由用户在本机主动执行。
