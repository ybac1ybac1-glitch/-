# V4 P0 审计报告

日期：2026-10-16。此阶段只做审计与最小安全基线，不修改现有选股逻辑。

## 当前仓库与启动

当前工作区包含 `backend/app.py`、`data.py`、`wyckoff.py`、`strategy.py`、`stock_filter.py`、`market.py`、公告/新闻模块和两个 HTML 模板。Windows 启动入口仍是 `python backend\\app.py`，监听 `127.0.0.1:8000`，调试器关闭。远端交付仓库为 `ybac1ybac1-glitch/-`；本地工作区的 `origin` 配置是另一个旧地址，后续提交应使用用户指定远端。

## 数据库与字段

`backend/data.py` 创建或迁移 SQLite 表 `daily`：`ts_code`、`trade_date`、`open`、`high`、`low`、`close`、`pre_close`、`change`、`pct_chg`、`vol`、`amount`、`turnover_rate`，主键为 `(ts_code, trade_date)`；另有 `meta(key,value)`。本次工作区没有用户本机的 `market_cache.sqlite3`，因为该文件被 `.gitignore` 排除，无法统计真实覆盖天数。Windows 本机启动后应先运行数据健康查询再决定是否补齐。

已有换手率迁移/回填代码：`_db()` 使用可重复的 `ALTER TABLE` 增量添加字段，`_run_turnover_backfill()` 只更新缺失记录的 `turnover_rate`。发现的风险是 `_turnover_lock` 已声明但未实际使用，`start_update()` 与换手率回填任务存在并发写库可能；P1 必须补上任务互斥和独立状态字段。新行情写入已采用 `(ts_code,trade_date)` UPSERT。

## 数据源与权限矩阵

| 数据/接口 | 当前代码 | P0 状态 |
|---|---|---|
| `daily` | 全市场按交易日批量 | 已验证代码路径，未用真实 Token 验证 |
| `trade_cal` | SSE 交易日 | 已验证代码路径，需真实权限确认 |
| `daily_basic`/换手率 | 按交易日批量及历史补齐 | 已验证模拟路径，真实权限待验证 |
| `adj_factor` | 未接入 | 待验证 |
| `stk_limit`/历史涨跌停价 | 未接入 | 待验证，当前策略为代理规则 |
| 历史 ST/停牌/上市状态 | 仅当前股票池名称 | 不可用/待补数据源 |
| 历史题材归属、竞价、分钟、Level2 | 未接入 | 不可用，相关 B 规则必须待确认 |
| 指数、全市场涨跌停、连板高度 | 未形成独立缓存 | 待验证 |

## V3.1 兼容性

旧首页 `/`、股票详情 `/stock/<ts_code>`、`POST /admin/update`、`GET /admin/update/status`、`POST /admin/turnover-backfill` 保留；SQLite 不在仓库中，不会被代码删除或重建。V3.1 的 `strategy.py`/`stock_filter.py` 仍是现有选股入口。V4 应使用新模块和 feature flag，不能替换该入口。

## P1 最小改造计划

新增独立 `strategy_a.py`、`strategy_b.py`、`evidence.py`、`signals.py` 和配置版本；增加 `signals`、`signal_events`、`data_health` 表，使用增量迁移和备份说明。增加 `/strategy/a`、`/strategy/b`、`/strategy/resonance`、`/data-health` 三个只读入口，保留 V3.1 首页。A/B 分开计算、存储、回测，共振只做展示交集。所有规则卡记录来源等级、阈值版本、缺失字段和状态。

验收命令：`pip install -r requirements.txt pytest`、`python -m pytest -q`；Windows 启动：`python backend\\app.py`。测试使用临时 SQLite 和模拟 Tushare 客户端，禁止生产 Token。

## 数据库备份与回滚

Windows CMD 备份：`copy backend\\market_cache.sqlite3 backend\\market_cache.sqlite3.bak`。迁移前复制备份；回滚时停止 Flask，删除迁移后的文件并将 `.bak` 改回原名。P1 只允许 `ALTER TABLE` 或新增表，禁止清空/重建 `daily`。

## 未在 P0 执行

P0 不实现双策略页面、规则评分、野人哥体系或历史回测；这些属于 P1–P4，需 P0 验收后分阶段提交。
