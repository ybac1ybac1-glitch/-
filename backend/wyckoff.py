"""Wyckoff structure analysis. Designed to work with Tushare OHLCV frames."""
import numpy as np
import pandas as pd


def _num(s, default=0.0):
    return pd.to_numeric(s, errors="coerce").fillna(default)


def analyze(df: pd.DataFrame) -> dict:
    if df is None or df.empty or "close" not in df:
        return {"stage": "吸筹观察", "score": 35.0, "reason": "历史K线不足，等待更多数据确认。", "signals": {}}
    d = df.copy().sort_values("trade_date" if "trade_date" in df else df.index.name or df.index)
    close = _num(d["close"]); high = _num(d.get("high", close)); low = _num(d.get("low", close)); vol = _num(d.get("vol", pd.Series(1, index=d.index)), 1)
    n = len(d); win = min(60, n); c = close.tail(win); h = high.tail(win); l = low.tail(win); v = vol.tail(win)
    support = float(l.head(max(5, win // 2)).quantile(.15)); resistance = float(h.head(max(5, win // 2)).quantile(.85))
    recent = float(close.iloc[-1]); prior = float(close.iloc[-min(21, n)])
    ret = close.pct_change().dropna(); volat = float(ret.tail(20).std() or 0); old_volat = float(ret.head(max(5, len(ret)//2)).std() or volat or 1)
    vol_ratio = float(v.iloc[-5:].mean() / max(v.head(max(20, win//2)).mean(), 1e-9))
    drawdown = (float(close.tail(min(60,n)).max()) - recent) / max(float(close.tail(min(60,n)).max()), 1e-9)
    spring = n >= 10 and float(low.iloc[-5:].min()) < support * 0.99 and recent > support * 1.01 and vol_ratio <= 1.5
    sos = recent > resistance * 1.015 and vol_ratio >= 1.25 and (recent - float(low.iloc[-1])) / max(float(high.iloc[-1]-low.iloc[-1]), 1e-9) > .65
    lps = n >= 8 and close.iloc[-1] > resistance and float(close.tail(5).min()) > resistance * .98 and vol_ratio < 1.0
    accumulation = drawdown > .12 and volat < old_volat * .85 and vol_ratio < 1.0 and (c.max()-c.min())/max(c.mean(),1e-9) < .25
    if spring: stage, base = "Spring", 78
    elif sos: stage, base = "SOS", 82
    elif lps: stage, base = "LPS", 86
    elif accumulation: stage, base = "吸筹观察", 65
    else: stage, base = "吸筹观察", 45
    score = base + min(10, max(-12, (0.98-vol_ratio)*12)) + min(8, max(-8, (0.9-volat/max(old_volat,1e-9))*8))
    score = float(np.clip(score, 0, 100))
    reasons = []
    if drawdown > .12: reasons.append("此前经历明显回撤")
    if accumulation: reasons.append("波动率与成交量收缩，卖压减弱")
    if spring: reasons.append("短暂跌破支撑后快速收回")
    if sos: reasons.append("突破压力位且放量，收盘位置较强")
    if lps: reasons.append("突破后缩量回踩，支撑保持有效")
    if not reasons: reasons.append("区间和量价信号尚未形成完整确认")
    return {"stage": stage, "score": round(score, 1), "reason": "；".join(reasons) + "。", "signals": {"support": round(support,2), "resistance": round(resistance,2), "vol_ratio": round(vol_ratio,2), "volatility": round(volat,4)}}


def analyze_stock(df):
    return analyze(df)
