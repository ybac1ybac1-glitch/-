# P2.2 Strategy A implementation report

本轮仅修复历史时点冻结和跨日状态转换，仍为单股只读扫描，不写数据库、不访问真实 Tushare。

## 历史时点规则

新增纯函数 `detect_range(history_before_event, params)`。它只读取事件发生前的有效 K 线，计算分位数上下沿、宽度、斜率、稳定性和边界测试次数，并返回冻结的阈值版本。扫描日形成的区间不会追认此前事件。

- A03：每个 Spring 候选逐日检查事件前有效区间；跌破和收回均使用该日冻结支撑。无合法区间只能 WATCH。
- A05：每个 SOS 逐日要求事件前有效区间；压力位使用冻结上沿，并保存量能证据。
- A04：状态按 Spring 候选、等待测试、测试候选、失效/超时重放；测试只在 Spring 后 1–15 个有效日发生，失效后不恢复。
- A06：只接受历史 SOS 后的后续回踩；使用冻结压力位，检查接近支撑、量能收缩和未破位；记录无 SOS、LPS 候选、失效状态。

所有 Evidence 均带 `threshold_version=A-E4-2026-03`、冻结边界和事件日期。输入始终截断到 asof_date。

## 测试

新增并运行跨日序列、未来隔离、下降趋势/宽幅反例、无先前区间 Spring、无先前区间 SOS、Spring 测试失效/超时、SOS 后 LPS 成功或破位、事件幂等测试。缺少涨跌停、停牌、复权字段时仍不产生 CONFIRMED 或可成交买点。


## 事件生命周期（本轮）

新增 `replay_events()`，为每个历史 Spring/SOS 生成独立稳定 `event_id`，保存事件日期、冻结支撑/压力、量能基准、阈值版本、当前状态、逐日 transition_history 和失效原因。Spring 状态为 CANDIDATE → WAITING_TEST → TEST_CANDIDATE / INVALIDATED / EXPIRED；SOS 状态为 CANDIDATE → WAITING_LPS → LPS_CANDIDATE / INVALIDATED / EXPIRED。事件按日期重放，后续事件不会覆盖已完成事件。`scan()` 接口保持不变，Evidence 继续使用 P1 结构。


## scan 与生命周期统一

`scan()` 现在只从 `replay_events()` 读取 A03/A04/A05/A06，并把事件 ID、事件日期、冻结边界和当日 transition 写入 Evidence；历史事件不会被最近事件覆盖。SOS 的 LPS 等待窗口为 `PARAMS['lps_wait_days']=15` 个有效交易日（E4），未达到期限保持 WAITING_LPS，只有超期才 EXPIRED。


## 验收清理

删除了旧的重复 `scan()`，当前唯一实现只调用 `replay_events()` 生成 A03–A06 Evidence。Spring/SOS 的第 1 个后续有效日先进入 WAITING 状态；第 1–15 日寻找测试/LPS，第 16 日才允许 EXPIRED。失效转换的 from 始终是事件当前状态，终态不会追加后续转换。测试改为 replay 事件列表与 scan Evidence 严格相等，不使用 WATCH 兜底断言。
