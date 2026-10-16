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
    events=strategy_a.replay_events("X",f,f.trade_date.iloc[-1])
    springs=[e for e in events if e["event_type"]=="SPRING"]
    assert len(springs)==1 and springs[0]["event_date"]==f.trade_date.iloc[90].date().isoformat()
    assert any(h["to"]=="TEST_CANDIDATE" and h["date"]==f.trade_date.iloc[95].date().isoformat() for h in springs[0]["transition_history"])
    assert rule(rows,"A04").evidence["events"] == springs

def test_sos_lps_are_not_same_day():
    f=bars(); f.loc[100,["close","high","vol"]]=[103,104,3000]; f.loc[105,["close","high","low","vol"]]=[101,102,100,500]
    rows=strategy_a.scan("X",f.trade_date.iloc[-1],f)
    events=strategy_a.replay_events("X",f,f.trade_date.iloc[-1])
    sos=[e for e in events if e["event_type"]=="SOS"]
    assert len(sos)>=1 and sos[0]["event_date"]==f.trade_date.iloc[100].date().isoformat()
    assert rule(rows,"A06").evidence["events"] == sos

def test_lps_without_prior_sos_is_watch():
    e=rule(strategy_a.scan("X","2025-05-21",bars()),"A06"); assert e.state=="WATCH" and not e.evidence["prior_sos"]
def test_background_rules_never_buy():
    rows=strategy_a.scan("X","2025-05-21",bars())
    assert rule(rows,"A07").state=="WATCH" and rule(rows,"A08").state=="WATCH"
def test_zero_volume_and_bad_price_are_conservative():
    f=bars(); f.loc[50:55,"vol"]=0; f.loc[60,"close"]=0
    rows=strategy_a.scan("X","2025-05-21",f)
    assert all(e.evidence["threshold_version"]=="A-E4-2026-03" for e in rows)
def test_idempotent():
    f=bars(); a=strategy_a.scan("X","2025-05-21",f); b=strategy_a.scan("X","2025-05-21",f)
    assert [e.to_dict() for e in a]==[e.to_dict() for e in b]

def test_replay_events_have_stable_independent_lifecycles():
    f=bars(); f.loc[90,["low","close","vol"]]=[95,100,500]
    f.loc[100,["close","high","vol"]]=[103,104,3000]
    events=strategy_a.replay_events("X",f,f.trade_date.iloc[-1])
    assert all({"event_id","event_date","event_type","threshold_version","current_state","transition_history"} <= set(e) for e in events)
    ids=[e["event_id"] for e in events]
    assert len(ids)==len(set(ids))
    for e in events:
        assert e["event_id"].startswith("A_WYCKOFF_VOLUME:X:")
        assert e["transition_history"][0]["date"]==e["event_date"]
        assert all(pd.Timestamp(h["date"])>=pd.Timestamp(e["event_date"]) for h in e["transition_history"])

def test_transition_chain_has_no_duplicate_or_future_states():
    f=bars(); f.loc[90,["low","close","vol"]]=[95,100,500]; f.loc[95,["low","close","vol"]]=[100,100,500]
    events=strategy_a.replay_events("X",f,f.trade_date.iloc[100])
    for e in events:
        h=e["transition_history"]
        assert all(h[i]["from"]==h[i-1]["to"] for i in range(1,len(h)))
        assert all(h[i]["to"]!=h[i]["from"] for i in range(len(h)))
        assert all(pd.Timestamp(z["date"])<=f.trade_date.iloc[100] for z in h)
        if e["current_state"] in {"INVALIDATED","EXPIRED","TEST_CANDIDATE","LPS_CANDIDATE"}:
            assert e["transition_history"][-1]["to"]==e["current_state"]

def test_spring_scan_states_at_event_and_test_dates():
    f=bars(); f.loc[90,["low","close","vol"]]=[95,100,500]; f.loc[93,["low","close","vol"]]=[100,100,500]
    spring_day=f.trade_date.iloc[90]; test_day=f.trade_date.iloc[93]
    spring=rule(strategy_a.scan("X",spring_day,f),"A03")
    tested=rule(strategy_a.scan("X",test_day,f),"A04")
    events=strategy_a.replay_events("X",f,test_day)
    se=[e for e in events if e["event_type"]=="SPRING" and e["event_date"]==spring_day.date().isoformat()]
    assert len(se)==1
    assert spring.state=="CANDIDATE"
    assert tested.state=="CANDIDATE"
    assert tested.evidence["event_id"]==se[0]["event_id"]
    assert any(h["to"]=="TEST_CANDIDATE" and h["date"]==test_day.date().isoformat() for h in se[0]["transition_history"])

def test_sos_lps_scan_states_and_event_link():
    f=bars(); f.loc[100,["close","high","low","vol"]]=[105,106,99,3000]
    f.loc[103,["close","high","low","vol"]]=[102,103,101,500]
    sos_day=f.trade_date.iloc[100]; lps_day=f.trade_date.iloc[103]
    events=strategy_a.replay_events("X",f,lps_day)
    sos=[e for e in events if e["event_type"]=="SOS" and e["event_date"]==sos_day.date().isoformat()]
    assert len(sos)==1
    assert any(h["to"]=="LPS_CANDIDATE" and h["date"]==lps_day.date().isoformat() for h in sos[0]["transition_history"])
    assert rule(strategy_a.scan("X",sos_day,f),"A05").state=="CANDIDATE"
    lps=rule(strategy_a.scan("X",lps_day,f),"A06")
    assert lps.state=="CANDIDATE"
    assert lps.evidence["event_id"]==sos[0]["event_id"]

def test_spring_timeout_15th_and_16th_boundaries():
    f=bars(110); f.loc[80,["low","close","vol"]]=[95,100,500]
    # Keep all 15 sessions after the event neutral, then add the 16th.
    fifteenth=f.trade_date.iloc[95]; sixteenth=f.trade_date.iloc[96]
    e15=[e for e in strategy_a.replay_events("X",f,fifteenth) if e["event_type"]=="SPRING"]
    e16=[e for e in strategy_a.replay_events("X",f,sixteenth) if e["event_type"]=="SPRING"]
    assert len(e15)==1 and e15[0]["current_state"]!="EXPIRED"
    assert len(e16)==1 and e16[0]["current_state"]=="EXPIRED"
    assert e16[0]["transition_history"][-1]["date"]==sixteenth.date().isoformat()

def test_sos_timeout_15th_and_16th_boundaries():
    f=bars(125); f.loc[80,["close","high","low","vol"]]=[105,106,99,3000]
    fifteenth=f.trade_date.iloc[95]; sixteenth=f.trade_date.iloc[96]
    e15=[e for e in strategy_a.replay_events("X",f,fifteenth) if e["event_type"]=="SOS"]
    e16=[e for e in strategy_a.replay_events("X",f,sixteenth) if e["event_type"]=="SOS"]
    assert len(e15)==1 and e15[0]["current_state"]!="EXPIRED"
    assert len(e16)==1 and e16[0]["current_state"]=="EXPIRED"
    assert e16[0]["transition_history"][-1]["date"]==sixteenth.date().isoformat()
