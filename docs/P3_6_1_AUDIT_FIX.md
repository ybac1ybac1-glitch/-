# P3.6.1 审计修复

- 支持整数 YYYYMMDD、字符串 YYYYMMDD 和 YYYY-MM-DD，避免整数被 pandas 当作 Unix 时间戳。
- 同日连续合法状态转换不报日期异常；仅日期倒退报错。
- 原始状态异常与按 event_id/转换日期/异常类型去重后的数量分别输出。
- 空或无有效交易日输入返回 UNVERIFIED。
