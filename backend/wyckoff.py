"""Defensive Wyckoff analysis for real OHLCV history."""
import numpy as np
import pandas as pd


def insufficient(reason="数据不足，无法评分"):
    return {"stage": "数据不足", "score": None, "reason": reason, "signals": {}}


def _num(frame, name, default=None):
    if name not in frame:
        return None if default is None else pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[name], errors="coerce")


def analyze(df: pd.DataFrame) -> dict:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return insufficient()
    required = {"close", "high", "low", "vol"}
    if not required.issubset(df.columns):
        return insufficient("数据不足，缺少完整 OHLCV 字段")
    d = df.copy()
    if "trade_date" in d.columns:
        d["_date"] = pd.to_datetime(d["trade_date"], errors="coerce")
        d = d.sort_values("_date", kind="stable").drop(columns="_date")
    else:
        d = d.sort_index(kind="stable")
    d = d.dropna(subset=["close", "high", "low", "vol"])
    if len(d) < 20:
        return insufficient(f"数据不足，至少需要20根历史K线（当前{len(d)}根）")
    close = pd.to_numeric(d["close"], errors="coerce")
    high = pd.to_numeric(d["high"], errors="coerce")
    low = pd.to_numeric(d["low"], errors="coerce")
    vol = pd.to_numeric(d["vol"], errors="coerce")
    win = min(60, len(d)); c=close.tail(win); h=high.tail(win); l=low.tail(win); v=vol.tail(win)
    support=float(l.head(max(5,win//2)).quantile(.15)); resistance=float(h.head(max(5,win//2)).quantile(.85)); recent=float(close.iloc[-1])
    ret=close.pct_change().dropna(); volat=float(ret.tail(20).std() or 0); old=float(ret.head(max(5,len(ret)//2)).std() or volat or 1)
    baseline=float(v.head(max(20,win//2)).mean()); vol_ratio=float(v.tail(5).mean()/max(baseline,1e-9))
    peak=float(close.tail(min(60,len(close))).max()); drawdown=(peak-recent)/max(peak,1e-9)
    spring=float(low.tail(5).min()) < support*.99 and recent > support*1.01 and vol_ratio <= 1.5
    sos=recent > resistance*1.015 and vol_ratio >= 1.25 and (recent-float(low.iloc[-1]))/max(float(high.iloc[-1]-low.iloc[-1]),1e-9)>.65
    lps=recent > resistance and float(close.tail(5).min()) > resistance*.98 and vol_ratio < 1
    accumulation=drawdown>.12 and volat<old*.85 and vol_ratio<1 and (c.max()-c.min())/max(c.mean(),1e-9)<.25
    if spring: stage,base="Spring",78
    elif sos: stage,base="SOS",82
    elif lps: stage,base="LPS",86
    elif accumulation: stage,base="吸筹观察",65
    else: stage,base="吸筹观察",45
    score=float(np.clip(base+min(10,max(-12,(.98-vol_ratio)*12))+min(8,max(-8,(.9-volat/max(old,1e-9))*8)),0,100))
    reasons=[]
    if drawdown>.12: reasons.append("此前经历明显回撤")
    if accumulation: reasons.append("波动率与成交量收缩，卖压减弱")
    if spring: reasons.append("短暂跌破支撑后快速收回")
    if sos: reasons.append("突破压力位且放量，收盘位置较强")
    if lps: reasons.append("突破后缩量回踩，支撑保持有效")
    if not reasons: reasons.append("区间和量价信号尚未形成完整确认")
    return {"stage":stage,"score":round(score,1),"reason":"；".join(reasons)+"。","signals":{"support":round(support,2),"resistance":round(resistance,2),"vol_ratio":round(vol_ratio,2),"volatility":round(volat,4)}}


def analyze_stock(df):
    return analyze(df)
