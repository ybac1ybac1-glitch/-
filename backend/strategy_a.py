"""Replayable Strategy A with event-time frozen ranges."""
from __future__ import annotations
import numpy as np,pandas as pd
from evidence import Evidence,validate
STRATEGY_ID="A_WYCKOFF_VOLUME"; VERSION="A-P2.2-0.3"; THRESHOLD_VERSION="A-E4-2026-03"
PARAMS={"range_window":80,"range_min_days":40,"range_width_max":.35,"range_quantiles":(.10,.90),"range_test_tolerance":.03,"range_min_tests":2,"max_down_slope":-.002,"volume_contraction":.80,"spring_lookback":20,"spring_break":.02,"spring_reclaim":.995,"test_days":15,"test_volume_ratio":.85,"sos_volume_ratio":1.5,"sos_close_position":.70,"lps_volume_ratio":.80,"lps_tolerance":.03,"lps_wait_days":15}
REQUIRED=("trade_date","open","high","low","close","vol","amount")
def _ev(rule,symbol,date,state,section,evidence=None,missing=(),risk="unknown",invalidation="",confirmation=""):
 return validate(Evidence(STRATEGY_ID,rule,VERSION,"三书研究报告/策略A规范",section,"E4",symbol,str(date),state=state,confirmation_date=str(confirmation or ""),invalidation=invalidation,risk_level=risk,missing_fields=tuple(missing),evidence={"threshold_version":THRESHOLD_VERSION,"parameters":dict(PARAMS),**(evidence or {})}))
def _prepare(asof,frame):
 if frame is None or not isinstance(frame,pd.DataFrame):return None,["daily_ohlcv"]
 miss=[c for c in REQUIRED if c not in frame.columns]
 if miss:return None,miss
 x=frame.copy();x["trade_date"]=pd.to_datetime(x.trade_date,errors="coerce");x=x[x.trade_date.notna()&(x.trade_date<=pd.to_datetime(asof,errors="coerce"))].copy()
 for c in REQUIRED[1:]:x[c]=pd.to_numeric(x[c],errors="coerce")
 x=x.replace([np.inf,-np.inf],np.nan).dropna(subset=list(REQUIRED[1:]));x=x[(x.close>0)&(x.high>=x.low)&(x.low>0)&(x.vol>=0)]
 return x.sort_values("trade_date").drop_duplicates("trade_date",keep="last"),[]
def detect_range(history_before_event,params=None):
 p={**PARAMS,**(params or {})}; h=history_before_event.copy() if isinstance(history_before_event,pd.DataFrame) else pd.DataFrame()
 if len(h)<p["range_min_days"]:return {"valid":False,"reason":"insufficient_history","valid_sessions":len(h)}
 h=h.tail(p["range_window"]); q=p["range_quantiles"]; lo,hi=float(h.low.quantile(q[0])),float(h.high.quantile(q[1]))
 width=(hi-lo)/max(float(h.close.median()),1e-12); slope=float(np.polyfit(np.arange(len(h)),h.close,1)[0]/max(h.close.mean(),1e-12))
 stability=float(((h.close>=lo)&(h.close<=hi)).mean()); tests=int((h.low<=lo*(1+p["range_test_tolerance"])).sum()+(h.high>=hi*(1-p["range_test_tolerance"])).sum())
 valid=width<=p["range_width_max"] and stability>=.70 and tests>=p["range_min_tests"] and slope>p["max_down_slope"]
 return {"valid":bool(valid),"support":lo,"resistance":hi,"width":width,"slope":slope,"stability":stability,"boundary_tests":tests,"valid_sessions":len(h),"threshold_version":THRESHOLD_VERSION}
def _detect_range_arrays(close,high,low,end,params=None):
 p={**PARAMS,**(params or {})}; n=end
 if n<p["range_min_days"]: return {"valid":False,"reason":"insufficient_history","valid_sessions":n}
 start=max(0,n-p["range_window"]); lo_a=low[start:n]; hi_a=high[start:n]; cl=close[start:n]
 q=p["range_quantiles"]; lo,hi=float(np.quantile(lo_a,q[0])),float(np.quantile(hi_a,q[1]))
 width=(hi-lo)/max(float(np.median(cl)),1e-12); slope=float(np.polyfit(np.arange(len(cl)),cl,1)[0]/max(cl.mean(),1e-12))
 stability=float(((cl>=lo)&(cl<=hi)).mean()); tests=int((lo_a<=lo*(1+p["range_test_tolerance"])).sum()+(hi_a>=hi*(1-p["range_test_tolerance"])).sum())
 return {"valid":bool(width<=p["range_width_max"] and stability>=.70 and tests>=p["range_min_tests"] and slope>p["max_down_slope"]),"support":lo,"resistance":hi,"width":width,"slope":slope,"stability":stability,"boundary_tests":tests,"valid_sessions":len(cl),"threshold_version":THRESHOLD_VERSION}
def _event_ranges(x):
 close=x.close.to_numpy(dtype=float); high=x.high.to_numpy(dtype=float); low=x.low.to_numpy(dtype=float)
 return [_detect_range_arrays(close,high,low,i) for i in range(len(x))]
def _event_id(symbol, rule, event_date):
 return f"{STRATEGY_ID}:{symbol}:{rule}:{event_date}:{VERSION}"

def replay_events(symbol, frame, asof_date=None):
 """Replay every Spring/SOS event independently through each known session."""
 x, miss = _prepare(asof_date or "9999-12-31", frame)
 if x is None or x.empty: return []
 ranges = _event_ranges(x); events = []
 for i in range(PARAMS["spring_lookback"], len(x)):
  r = ranges[i]; support = r.get("support")
  if not (r.get("valid") and support): continue
  if x.low.iloc[i] < support*(1-PARAMS["spring_break"]) and x.close.iloc[i] >= support*PARAMS["spring_reclaim"] and x.vol.iloc[i] > 0:
   d=x.trade_date.iloc[i].date().isoformat(); baseline=float(x.vol.iloc[max(0,i-20):i].mean())
   e={"event_id":_event_id(symbol,"A03",d),"event_date":d,"event_type":"SPRING","frozen_support":support,"frozen_resistance":r.get("resistance"),"frozen_volume_baseline":baseline,"threshold_version":THRESHOLD_VERSION,"current_state":"CANDIDATE","transition_history":[{"date":d,"from":None,"to":"CANDIDATE","reason":"break_and_reclaim"}],"invalidation_reason":""}
   for j in range(i+1,min(len(x),i+1+PARAMS["test_days"])):
    jd=x.trade_date.iloc[j].date().isoformat()
    if e["current_state"]=="CANDIDATE":
     e["current_state"]="WAITING_TEST"; e["transition_history"].append({"date":jd,"from":"CANDIDATE","to":"WAITING_TEST","reason":"await_test"})
    if x.close.iloc[j] < support*(1-PARAMS["lps_tolerance"]):
     e["current_state"]="INVALIDATED"; e["invalidation_reason"]="support_broken"; e["transition_history"].append({"date":jd,"from":"WAITING_TEST","to":"INVALIDATED","reason":"support_broken"}); break
    if x.low.iloc[j] >= support*(1-PARAMS["lps_tolerance"]) and baseline>0 and x.vol.iloc[j] <= baseline*PARAMS["test_volume_ratio"]:
     e["current_state"]="TEST_CANDIDATE"; e["transition_history"].append({"date":jd,"from":"WAITING_TEST","to":"TEST_CANDIDATE","reason":"low_volume_test"}); break
   else:
    if len(x)>i+1+PARAMS["test_days"] and e["current_state"] in {"CANDIDATE","WAITING_TEST"}:
     e["current_state"]="EXPIRED"; e["transition_history"].append({"date":x.trade_date.iloc[min(len(x)-1,i+PARAMS["test_days"]+1)].date().isoformat(),"from":e["current_state"],"to":"EXPIRED","reason":"test_timeout"})
   events.append(e)
 for i in range(20,len(x)):
  r=ranges[i]; pressure=r.get("resistance"); av=x.vol.iloc[max(0,i-20):i].mean()
  if not (r.get("valid") and pressure and av>0): continue
  cp=(x.close.iloc[i]-x.low.iloc[i])/max(x.high.iloc[i]-x.low.iloc[i],1e-12)
  if x.close.iloc[i] <= pressure or x.vol.iloc[i] < av*PARAMS["sos_volume_ratio"] or cp < PARAMS["sos_close_position"]: continue
  d=x.trade_date.iloc[i].date().isoformat()
  e={"event_id":_event_id(symbol,"A05",d),"event_date":d,"event_type":"SOS","frozen_support":r.get("support"),"frozen_resistance":pressure,"frozen_volume_baseline":float(av),"threshold_version":THRESHOLD_VERSION,"current_state":"CANDIDATE","transition_history":[{"date":d,"from":None,"to":"CANDIDATE","reason":"pressure_break"}],"invalidation_reason":""}
  for j in range(i+1,len(x)):
   jd=x.trade_date.iloc[j].date().isoformat()
   if e["current_state"]=="CANDIDATE": e["current_state"]="WAITING_LPS"; e["transition_history"].append({"date":jd,"from":"CANDIDATE","to":"WAITING_LPS","reason":"await_lps"})
   if x.close.iloc[j] < pressure*(1-PARAMS["lps_tolerance"]):
    e["current_state"]="INVALIDATED"; e["invalidation_reason"]="breakout_support_lost"; e["transition_history"].append({"date":jd,"from":"WAITING_LPS","to":"INVALIDATED","reason":"support_broken"}); break
   vr=x.vol.iloc[j]/max(av,1e-12)
   if x.low.iloc[j]<=pressure*(1+PARAMS["lps_tolerance"]) and x.close.iloc[j]>=pressure*(1-PARAMS["lps_tolerance"]) and vr<=PARAMS["lps_volume_ratio"]:
    e["current_state"]="LPS_CANDIDATE"; e["transition_history"].append({"date":jd,"from":"WAITING_LPS","to":"LPS_CANDIDATE","reason":"low_volume_retest"}); break
  else:
   if len(x)>i+1 and e["current_state"]=="WAITING_LPS" and len(x)-1-i>PARAMS["lps_wait_days"]: e["current_state"]="EXPIRED"; e["transition_history"].append({"date":x.trade_date.iloc[min(len(x)-1,i+PARAMS["lps_wait_days"]+1)].date().isoformat(),"from":"WAITING_LPS","to":"EXPIRED","reason":"lps_timeout"})
  events.append(e)
 return events

def scan(symbol,asof_date,frame=None):
    """Generate Evidence from the single replay_events source of truth."""
    x,miss=_prepare(asof_date,frame)
    if x is None or x.empty:return [_ev("A00",symbol,asof_date,"INSUFFICIENT_DATA","数据质量",missing=miss or ["valid_ohlcv"])]
    date=x.trade_date.iloc[-1].date().isoformat()
    if len(x)<20:return [_ev("A00",symbol,date,"INSUFFICIENT_DATA","数据质量",missing=("at_least_20_valid_sessions",))]
    rng=detect_range(x.iloc[:-1]); out=[_ev("A01",symbol,date,"CANDIDATE" if rng.get("valid") else "WATCH","交易区间识别",rng)]
    w=x.iloc[:-1].tail(PARAMS["range_window"]); recent,base=w.tail(10),w.head(max(10,len(w)-10)); rv,bv=recent.vol.mean(),base.vol.mean(); rr=(recent.high-recent.low).mean()/max(recent.close.mean(),1e-12); br=(base.high-base.low).mean()/max(base.close.mean(),1e-12); pull=float(recent.close.iloc[-1]/recent.close.iloc[0]-1); supply=rv<=bv*PARAMS["volume_contraction"] and (rr<=br or pull<0) and recent.amount.mean()>0
    out.append(_ev("A02",symbol,date,"CANDIDATE" if supply else "WATCH","供应减弱",{"recent_volume":rv,"base_volume":bv,"range_ratio_recent":rr,"range_ratio_base":br,"pullback":pull,"liquid":bool(recent.amount.mean()>0)}))
    events=replay_events(symbol,x,date)
    def event_ev(rule,etype,section):
        es=[e for e in events if e["event_type"]==etype]
        transitions=[]
        for e in es:
            for h in e["transition_history"]:
                if h["date"]==date: transitions.append((e,h))
        current=[e for e in es if e["event_date"]==date]
        chosen=current[-1] if current else (es[-1] if es else None)
        if rule=="A03":
            state="CANDIDATE" if current else "WATCH"; ev={"event_id":chosen["event_id"] if chosen else "","event_date":chosen["event_date"] if chosen else "","events":es,"frozen_support":chosen.get("frozen_support") if chosen else None}
        elif rule=="A05":
            state="CANDIDATE" if current else "WATCH"; ev={"event_id":chosen["event_id"] if chosen else "","event_date":chosen["event_date"] if chosen else "","events":es,"frozen_resistance":chosen.get("frozen_resistance") if chosen else None}
        elif rule=="A04":
            state="CANDIDATE" if any(h.get("to")=="TEST_CANDIDATE" for _,h in transitions) else ("INVALIDATED" if any(h.get("to")=="INVALIDATED" for _,h in transitions) else "WATCH")
            e,h=transitions[-1] if transitions else (chosen,None); ev={"event_id":e["event_id"] if e else "","event_date":e["event_date"] if e else "","spring_date":e["event_date"] if e else "","transition":h,"events":es,"frozen_support":e.get("frozen_support") if e else None}
        else:
            state="CANDIDATE" if any(h.get("to")=="LPS_CANDIDATE" for _,h in transitions) else ("INVALIDATED" if any(h.get("to")=="INVALIDATED" for _,h in transitions) else "WATCH")
            e,h=transitions[-1] if transitions else (chosen,None); ev={"event_id":e["event_id"] if e else "","event_date":e["event_date"] if e else "","sos_date":e["event_date"] if e else "","prior_sos":bool(e),"transition":h,"events":es,"frozen_resistance":e.get("frozen_resistance") if e else None,"lps_wait_days":PARAMS["lps_wait_days"]}
        return _ev(rule,symbol,date,state,section,ev,missing=("stk_limit,halt_status,adj_factor",) if es else ())
    out += [event_ev("A03","SPRING","Spring候选"),event_ev("A04","SPRING","Spring后测试"),event_ev("A05","SOS","SOS强势突破"),event_ev("A06","SOS","LPS回踩")]
    bar=x.iloc[-1]; avg=x.vol.shift(1).rolling(20,min_periods=10).mean(); av=float(avg.iloc[-1]) if pd.notna(avg.iloc[-1]) else 0; effort=float(bar.vol/max(av,1e-12)); result=float((bar.close-bar.open)/max(bar.open,1e-12))
    out += [_ev("A07",symbol,date,"WATCH","努力与结果",{"volume_effort":effort,"price_result":result}),_ev("A08",symbol,date,"WATCH","量价背离",{"price_up":bool(x.close.tail(5).iloc[-1]>x.close.tail(5).iloc[0]),"volume_down":bool(x.vol.tail(5).iloc[-1]<x.vol.tail(5).iloc[0])})]
    flags=[]; 
    if rng.get("slope",0)>.003:flags.append("rising_trend")
    if effort>2.5 and result<0:flags.append("high_volume_down_close")
    if rng.get("width",0)>.50:flags.append("wide_range")
    out.append(_ev("A09",symbol,date,"CANDIDATE" if len(flags)>=2 else "WATCH","派发风险",{"risk_conditions":flags,"independent_conditions":len(flags)}))
    return out
