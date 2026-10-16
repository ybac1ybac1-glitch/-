"""Auditable Strategy A (Wyckoff x volume/price), single-symbol only."""
from __future__ import annotations
import numpy as np
import pandas as pd
from evidence import Evidence, validate

STRATEGY_ID="A_WYCKOFF_VOLUME"; VERSION="A-P2.2-0.1"; THRESHOLD_VERSION="A-E4-2026-01"
PARAMS={"range_window":80,"range_min_days":40,"range_width_max":.35,"volume_contraction":.80,"spring_lookback":20,"spring_break":.02,"spring_reclaim":.995,"test_days":15,"sos_volume_ratio":1.5,"sos_close_position":.70,"lps_volume_ratio":.80,"lps_tolerance":.03}
REQUIRED=("trade_date","open","high","low","close","vol","amount")
def _ev(rule,symbol,date,state,section,evidence=None,missing=(),risk="unknown",invalidation="",confirmation=""):
 return validate(Evidence(STRATEGY_ID,rule,VERSION,"三书研究报告/策略A规范",section,"E4",symbol,str(date),state=state,confirmation_date=str(confirmation or ""),invalidation=invalidation,risk_level=risk,missing_fields=tuple(missing),evidence={"threshold_version":THRESHOLD_VERSION,"parameters":dict(PARAMS),**(evidence or {})}))
def _prepare(asof_date,frame):
 if frame is None or not isinstance(frame,pd.DataFrame): return None,["daily_ohlcv"]
 missing=[c for c in REQUIRED if c not in frame.columns]
 if missing:return None,missing
 x=frame.copy(); x["trade_date"]=pd.to_datetime(x.trade_date,errors="coerce"); x=x[x.trade_date.notna()&(x.trade_date<=pd.to_datetime(asof_date,errors="coerce"))].copy()
 for c in REQUIRED[1:]: x[c]=pd.to_numeric(x[c],errors="coerce")
 x=x.replace([np.inf,-np.inf],np.nan).dropna(subset=list(REQUIRED[1:])); x=x[(x.close>0)&(x.high>0)&(x.low>0)&(x.vol>=0)]
 return x.sort_values("trade_date").drop_duplicates("trade_date",keep="last"),[]
def scan(symbol,asof_date,frame=None):
 x,missing=_prepare(asof_date,frame)
 if x is None or x.empty:return [_ev("A00",symbol,asof_date,"INSUFFICIENT_DATA","数据质量",missing=missing or ["valid_ohlcv"])]
 date=x.trade_date.iloc[-1].date().isoformat()
 if len(x)<20:return [_ev("A00",symbol,date,"INSUFFICIENT_DATA","数据质量",missing=("at_least_20_valid_sessions",))]
 out=[]; prior=x.iloc[:-1]; w=prior.tail(PARAMS["range_window"])
 if len(w)<PARAMS["range_min_days"]:return [_ev("A01",symbol,date,"INSUFFICIENT_DATA","交易区间识别",missing=("range_history_80",))]
 support,resistance=float(w.low.min()),float(w.high.max()); width=(resistance-support)/max(support,1e-12); slope=float(np.polyfit(np.arange(len(w)),w.close,1)[0]/w.close.mean()); inrange=float(((w.close>=support)&(w.close<=resistance)).mean()); range_ok=width<=PARAMS["range_width_max"] and inrange>=.5
 out.append(_ev("A01",symbol,date,"CANDIDATE" if range_ok else "WATCH","交易区间识别",{"support":support,"resistance":resistance,"width":width,"duration":len(w),"slope":slope,"valid_sessions":len(w),"in_range_ratio":inrange},risk="medium" if range_ok else "unknown",invalidation=f"close < {support:.6g}"))
 recent,base=w.tail(10),w.head(max(10,len(w)-10)); rv,bv=recent.vol.mean(),base.vol.mean(); rr=(recent.high-recent.low).mean()/recent.close.mean(); br=(base.high-base.low).mean()/base.close.mean(); supply=rv<=bv*PARAMS["volume_contraction"] and rr<=br
 out.append(_ev("A02",symbol,date,"CANDIDATE" if supply else "WATCH","供应减弱",{"recent_volume":rv,"base_volume":bv,"range_ratio_recent":rr,"range_ratio_base":br}))
 bar=x.iloc[-1]; ps=float(prior.tail(PARAMS["spring_lookback"]).low.min()); spring=bool(bar.low<ps*(1-PARAMS["spring_break"]) and bar.close>=ps*PARAMS["spring_reclaim"])
 out.append(_ev("A03",symbol,date,"CANDIDATE" if spring else "WATCH","Spring候选",{"support":ps,"low":float(bar.low),"close":float(bar.close),"reclaimed":spring},missing=("stk_limit,halt_status",) if spring else ()))
 test=bool(spring and (x.tail(PARAMS["test_days"]).low>=ps*(1-PARAMS["lps_tolerance"])).all())
 out.append(_ev("A04",symbol,date,"CANDIDATE" if test else "WATCH","Spring后测试",{"test_confirmed":test,"window":PARAMS["test_days"]},missing=("stk_limit,halt_status",) if spring else ()))
 avg=x.iloc[:-1].tail(20).vol.mean(); cp=(bar.close-bar.low)/max(bar.high-bar.low,1e-12); sos=bool(bar.close>resistance and bar.vol>=avg*PARAMS["sos_volume_ratio"] and cp>=PARAMS["sos_close_position"])
 out.append(_ev("A05",symbol,date,"CANDIDATE" if sos else "WATCH","SOS强势突破",{"resistance":resistance,"volume_ratio":float(bar.vol/max(avg,1e-12)),"close_position":float(cp)}))
 lps=False
 if sos and len(x)>=3:
  pull=x.tail(3); lps=bool(pull.close.min()>=resistance*(1-PARAMS["lps_tolerance"]) and pull.vol.mean()<=avg*PARAMS["lps_volume_ratio"])
 out.append(_ev("A06",symbol,date,"CANDIDATE" if lps else "WATCH","LPS回踩",{"prior_sos":sos,"confirmed":lps}))
 out.append(_ev("A07",symbol,date,"WATCH","努力与结果",{"volume_effort":float(bar.vol/max(avg,1e-12)),"price_result":float((bar.close-bar.open)/max(bar.open,1e-12))}))
 out.append(_ev("A08",symbol,date,"WATCH","量价背离",{"price_up":bool(x.close.tail(5).iloc[-1]>x.close.tail(5).iloc[0]),"volume_down":bool(x.vol.tail(5).iloc[-1]<x.vol.tail(5).iloc[0])}))
 flags=int(bar.close>resistance*1.08)+int(bar.vol>avg*2.5)+int(slope>.003); out.append(_ev("A09",symbol,date,"CANDIDATE" if flags>=2 else "WATCH","派发风险",{"risk_flags":flags,"independent_conditions":flags},risk="high" if flags>=2 else "low"))
 return out
