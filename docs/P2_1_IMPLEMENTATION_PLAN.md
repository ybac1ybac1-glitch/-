# P2.1 实施计划与接口

## 统一接口

`strategy_a.scan(symbol, asof_date, frame)` 接收截至 `asof_date` 的历史 DataFrame；调用方必须先截断未来行。返回 `Evidence` 列表，不返回 V3.1 分数，也不写策略 B 数据。P2.2 才实现 A01–A09 的计算器。

接口返回状态：`WATCH`、`CANDIDATE`、`CONFIRMED`、`INVALIDATED`、`INSUFFICIENT_DATA`、`NEEDS_INTRADAY`。缺字段输出 `missing_fields`，禁止用 0 填充。`signals.save()` 以 strategy/rule/symbol/signal_date 幂等；状态变化写 `signal_events`，禁止 invalidated 恢复确认。

## 版本和参数

|参数|值|性质|
|---|---:|---|
|A01 区间窗口|80 日、至少 40 日在区间|E4 工程起点|
|A04 测试窗口|1–15 个交易日|E4 工程起点|
|A05 量能基准|20 日中枢|E4 工程起点|
|流动性门槛|配置项，不在 P2.1 固定|E4 待校准|

每个阈值必须带 `threshold_version`，后续做敏感性测试（窗口、分位数、量能倍数）和滚动样本外验证，不能声称是书本固定标准。

## P2.2 顺序

1. 数据截断和字段质量检查；2. A01 区间与 A02 供应减弱；3. A03 Spring 候选；4. A04 测试状态机；5. A05 SOS；6. A06 LPS；7. A07/A08 背景证据；8. A09 E4 风险提示；9. 独立回测与反例。

## 未解决问题

扫描 PDF 图例仍需逐页核对；历史涨停价、停牌、ST、复权因子尚未完成时点数据接入；120 日不足以验证更长背景；真实回测不得在数据补齐前宣称有效。

本阶段不启用规则、不生成真实候选、不改变 V3.1 入口。
