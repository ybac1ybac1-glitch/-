"""Strategy A P2.2: conservative, replayable Wyckoff/volume evidence."""
from __future__ import annotations
import numpy as np, pandas as pd
from evidence import Evidence, validate
STRATEGY_ID="A_WYCKOFF_VOLUME"; VERSION="A-P2.2-0.2"; THRESHOLD_VERSION="A-E4-2026-02"
PARAMS={"range_window":80,"range_min_days":40,"range_width_max":.35,"range_quantiles":(.10,.90),"range_test_tolerance":.03,"range_min_tests":2,"max_down_slope":-.002,"volume_contraction":.80,"spring_lookback":20,"spring_break":.02,"spring_reclaim":.995,"test_days":15,"test_volume_ratio":.85,"sos_volume_ratio":1.5,"sos_close_position":.70,"lps_volume_ratio":.80,"lps_tolerance":.03}
REQUIRED=("trade_date","open","high","low","close","vol","amount")
def _ev(rule,symbol,date,state,section,evidence=None,missing=(),risk="unknown",invalidation="",confirmation=""):
 return validate(Evidence(STRATEGY_ID,rule,VERSION,"三书研究报告/策略A规范",section,"E4",symbol,str(date),state=state,confirmation_date=str(confirmation or ""),invalidation=invalidation,risk_level=risk,missing_fields=tuple(missing),evidence={"threshold_version":THRESHOLD_VERSION,"parameters":dict(PARAMS),**(evidence or {})}))
def _prepare(asof,frame):
 if frame is None or not isinstance(frame,pd.DataFrame): return None,["daily_ohlcv"]
 miss=[c for c in REQUIRED if c not in frame.columns]
 if miss:return None,miss
 x=frame.copy(); x["trade_date"]=pd.to_datetime(x.trade_date,errors="coerce"); x=x[x.trade_date.notna()&(x.trade_date<=pd.to_datetime(asof,errors="coerce"))].copy()
 for c in REQUIRED[1:]:x[c]=pd.to_numeric(x[c],errors="coerce")
 x=x.replace([np.inf,-np.inf],np.nan).dropna(subset=list(REQUIRED[1:])); x=x[(x.close>0)&(x.high>=x.low)&(x.low>0)&(x.vol>=0)]
 return x.sort_values("trade_date").drop_duplicates("trade_date",keep="last"),[]
def scan(symbol,asof_date,frame=None):
 x,miss=_prepare(asof_date,frame)
 if x is None or x.empty:return [_ev("A00",symbol,asof_date,"INSUFFICIENT_DATA","数据质量",missing=miss or ["valid_ohlcv"])]
 date=x.trade_date.iloc[-1].date().isoformat()
 if len(x)<20:return [_ev("A00",symbol,date,"INSUFFICIENT_DATA","数据质量",missing=("at_least_20_valid_sessions",))]
 out=[]; prior=x.iloc[:-1]; w=prior.tail(PARAMS["range_window"])
 if len(w)<PARAMS["range_min_days"]:return [_ev("A01",symbol,date,"INSUFFICIENT_DATA","交易区间识别",missing=("range_history_80",))]
 lo,hi=np.quantile(w.low,PARAMS["range_quantiles"][0]),np.quantile(w.high,PARAMS["range_quantiles"][1]); width=(hi-lo)/max(np.median(w.close),1e-12)
 slope=float(np.polyfit(np.arange(len(w)),w.close,1)[0]/max(w.close.mean(),1e-12)); stable=float(((w.close>=lo)&(w.close<=hi)).mean()); tests=int(((w.low<=lo*(1+PARAMS["range_test_tolerance"])).sum()+(w.high>=hi*(1-PARAMS["range_test_tolerance"])).sum()))
 valid_range=width<=PARAMS["range_width_max"] and stable>=.70 and tests>=PARAMS["range_min_tests"] and slope>PARAMS["max_down_slope"]
 out.append(_ev("A01",symbol,date,"CANDIDATE" if valid_range else "WATCH","交易区间识别",{"support":float(lo),"resistance":float(hi),"width":float(width),"duration":len(w),"slope":slope,"stability":stable,"boundary_tests":tests,"valid_sessions":len(w)},risk="medium" if valid_range else "unknown",invalidation=f"close < {lo:.6g}"))
 recent,base=w.tail(10),w.head(max(10,len(w)-10)); rv,bv=recent.vol.mean(),base.vol.mean(); rr=(recent.high-recent.low).mean()/max(recent.close.mean(),1e-12); br=(base.high-base.low).mean()/max(base.close.mean(),1e-12); pullback=float(recent.close.iloc[-1]/recent.close.iloc[0]-1); supply=bool(rv<=bv*PARAMS["volume_contraction"] and (rr<=br or pullback<0) and recent.amount.mean()>0)
 out.append(_ev("A02",symbol,date,"CANDIDATE" if supply else "WATCH","供应减弱",{"recent_volume":rv,"base_volume":bv,"range_ratio_recent":rr,"range_ratio_base":br,"pullback":pullback,"liquid":bool(recent.amount.mean()>0)}))
 avg=x.vol.shift(1).rolling(20,min_periods=10).mean(); springs=[]; sos_dates=[]
 for i in range(PARAMS["spring_lookback"],len(x)):
  support=float(x.iloc[max(0,i-PARAMS["spring_lookback"]):i].low.quantile(.10))
  if valid_range and x.low.iloc[i]<support*(1-PARAMS["spring_break"]) and x.close.iloc[i]>=support*PARAMS["spring_reclaim"] and x.vol.iloc[i]>0:springs.append(i)
 out.append(_ev("A03",symbol,date,"CANDIDATE" if springs and springs[-1]==len(x)-1 else "WATCH","Spring候选",{"support":float(lo),"spring_dates":[x.trade_date.iloc[i].date().isoformat() for i in springs],"reclaimed":bool(springs and springs[-1]==len(x)-1)},missing=("stk_limit,halt_status,adj_factor",) if springs else ()))
 test_idx=None; test_spring=None
 for s in springs:
  for i in range(s+1,min(len(x),s+1+PARAMS["test_days"])):
   baseline=float(x.vol.iloc[max(0,s-20):s].mean()); held=x.low.iloc[i]>=float(w.low.quantile(.10))*(1-PARAMS["lps_tolerance"]); shrunk=x.vol.iloc[i]<=baseline*PARAMS["test_volume_ratio"] if baseline>0 else False
   if held and shrunk:test_idx=i; test_spring=s
   elif x.close.iloc[i]<float(w.low.quantile(.10))*(1-PARAMS["lps_tolerance"]):break
 out.append(_ev("A04",symbol,date,"CANDIDATE" if test_idx==len(x)-1 else "WATCH","Spring后测试",{"spring_date":x.trade_date.iloc[test_spring].date().isoformat() if test_spring is not None else "","test_date":x.trade_date.iloc[test_idx].date().isoformat() if test_idx is not None else "","support":float(lo),"valid":test_idx==len(x)-1},missing=("stk_limit,halt_status",) if test_idx is not None else ()))
 for i in range(20,len(x)):
  pressure=float(x.iloc[max(0,i-PARAMS["range_window"]):i].high.quantile(.90)); ratio=x.vol.iloc[i]/max(avg.iloc[i],1e-12); cp=(x.close.iloc[i]-x.low.iloc[i])/max(x.high.iloc[i]-x.low.iloc[i],1e-12)
  if x.close.iloc[i]>pressure and ratio>=PARAMS["sos_volume_ratio"] and cp>=PARAMS["sos_close_position"]:sos_dates.append(i)
 sos_idx=sos_dates[-1] if sos_dates else None
 out.append(_ev("A05",symbol,date,"CANDIDATE" if sos_idx==len(x)-1 else "WATCH","SOS强势突破",{"sos_date":x.trade_date.iloc[sos_idx].date().isoformat() if sos_idx is not None else "","pressure":float(hi),"valid_range":valid_range},missing=("stk_limit,halt_status",) if sos_idx is not None else ()))
 lps_idx=None
 if sos_idx is not None:
  for i in range(sos_idx+1,len(x)):
   support=float(x.iloc[max(0,sos_idx-PARAMS["range_window"]):sos_idx].high.quantile(.90)); vr=x.vol.iloc[i]/max(x.vol.iloc[max(0,sos_idx-20):sos_idx].mean(),1e-12)
   if x.close.iloc[i]<support*(1-PARAMS["lps_tolerance"]):break
   if x.close.iloc[i]>=support*(1-PARAMS["lps_tolerance"]) and vr<=PARAMS["lps_volume_ratio"]:lps_idx=i
 out.append(_ev("A06",symbol,date,"CANDIDATE" if lps_idx==len(x)-1 else "WATCH","LPS回踩",{"sos_date":x.trade_date.iloc[sos_idx].date().isoformat() if sos_idx is not None else "","lps_date":x.trade_date.iloc[lps_idx].date().isoformat() if lps_idx is not None else "","prior_sos":sos_idx is not None,"invalidated":bool(sos_idx is not None and lps_idx is None and len(x)>sos_idx+1)}))
 bar=x.iloc[-1]; av=float(avg.iloc[-1]) if pd.notna(avg.iloc[-1]) else 0; effort=float(bar.vol/max(av,1e-12)); result=float((bar.close-bar.open)/max(bar.open,1e-12))
 out.append(_ev("A07",symbol,date,"WATCH","努力与结果",{"volume_effort":effort,"price_result":result}))
 out.append(_ev("A08",symbol,date,"WATCH","量价背离",{"price_up":bool(x.close.tail(5).iloc[-1]>x.close.tail(5).iloc[0]),"volume_down":bool(x.vol.tail(5).iloc[-1]<x.vol.tail(5).iloc[0])}))
 flags=[]; 
 if slope>.003:flags.append("rising_trend")
 if effort>2.5 and result<0:flags.append("high_volume_down_close")
 if width>.50:flags.append("wide_range")
 out.append(_ev("A09",symbol,date,"CANDIDATE" if len(flags)>=2 else "WATCH","派发风险",{"risk_conditions":flags,"independent_conditions":len(flags)},risk="high" if len(flags)>=2 else "low"))
 return out
