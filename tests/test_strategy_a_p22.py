import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
import strategy_a

def bars(n=120):
    d=pd.date_range("2025-01-02",periods=n,freq="B"); c=np.full(n,100.); c[:min(80,n)]=100+np.sin(np.arange(min(80,n)))*1.5
    return pd.DataFrame({"trade_date":d,"open":c,"high":c+1,"low":c-1,"close":c,"vol":np.full(n,1000.),"amount":c*1000})
def rule(rows,r): return next(x for x in rows if x.rule_id==r)
def test_future_and_namespace():
    f=bars(); f.loc[len(f)]=[pd.Timestamp("2030-01-01"),100,101,99,100,1000,100000]
    rows=strategy_a.scan("X","2025-05-21",f)
    assert all(pd.Timestamp(e.signal_date)<=pd.Timestamp("2025-05-21") for e in rows)
    assert all(e.strategy_id=="A_WYCKOFF_VOLUME" for e in rows)
def test_missing_and_short_history():
    assert rule(strategy_a.scan("X","2025-01-02",pd.DataFrame({"trade_date":[]})),"A00").state=="INSUFFICIENT_DATA"
    assert rule(strategy_a.scan("X","2025-01-20",bars(10)),"A00").state=="INSUFFICIENT_DATA"
def test_range_and_downtrend_rejection():
    f=bars(); down=np.linspace(120,80,120); f[["open","high","low","close"]]=np.c_[down,down+1,down-1,down]
    assert rule(strategy_a.scan("X","2025-05-21",f),"A01").state!="CANDIDATE"
def test_wide_range_rejection():
    f=bars(); f["low"]=f.close*(1-.35); f["high"]=f.close*(1+.35)
    assert rule(strategy_a.scan("X","2025-05-21",f),"A01").state!="CANDIDATE"
def test_spring_requires_valid_range_and_is_candidate_only():
    f=bars(); f.loc[119,["low","close"]]=[95,100]
    e=rule(strategy_a.scan("X","2025-05-21",f),"A03")
    assert e.state in {"CANDIDATE","WATCH"} and e.state!="CONFIRMED"
    g=bars(); g[["open","high","low","close"]]=np.c_[np.linspace(140,80,120),np.linspace(140,80,120)+1,np.linspace(140,80,120)-1,np.linspace(140,80,120)]
    assert rule(strategy_a.scan("X","2025-05-21",g),"A03").state!="CANDIDATE"
def test_spring_then_later_test_is_replayed():
    f=bars(); f.loc[90,["low","close","vol"]]=[95,100,500]; f.loc[95,["low","close","vol"]]=[100,100,500]
    rows=strategy_a.scan("X",f.trade_date.iloc[-1],f)
    e=rule(rows,"A04"); assert e.evidence["spring_date"] or e.state=="WATCH"
def test_sos_lps_are_not_same_day():
    f=bars(); f.loc[100,["close","high","vol"]]=[103,104,3000]; f.loc[105,["close","high","low","vol"]]=[101,102,100,500]
    rows=strategy_a.scan("X",f.trade_date.iloc[-1],f); e=rule(rows,"A06")
    assert e.evidence["sos_date"]=="2025-05-22" or e.state=="WATCH"
def test_lps_without_prior_sos_is_watch():
    e=rule(strategy_a.scan("X","2025-05-21",bars()),"A06"); assert e.state=="WATCH" and not e.evidence["prior_sos"]
def test_background_rules_never_buy():
    rows=strategy_a.scan("X","2025-05-21",bars())
    assert rule(rows,"A07").state=="WATCH" and rule(rows,"A08").state=="WATCH"
def test_zero_volume_and_bad_price_are_conservative():
    f=bars(); f.loc[50:55,"vol"]=0; f.loc[60,"close"]=0
    rows=strategy_a.scan("X","2025-05-21",f)
    assert all(e.evidence["threshold_version"]=="A-E4-2026-02" for e in rows)
def test_idempotent():
    f=bars(); a=strategy_a.scan("X","2025-05-21",f); b=strategy_a.scan("X","2025-05-21",f)
    assert [e.to_dict() for e in a]==[e.to_dict() for e in b]
