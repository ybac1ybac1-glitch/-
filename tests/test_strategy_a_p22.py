import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
import strategy_a

def bars(n=100, breakout=False):
    dates=pd.date_range("2025-01-02",periods=n,freq="B")
    close=np.full(n,100.0); close[:min(80,n)]=100+np.sin(np.arange(min(80,n)))*1.5
    if breakout: close[-1]=110
    open_=close.copy(); high=close+1; low=close-1; vol=np.full(n,1000.); amount=vol*close
    if breakout: high[-1]=111; low[-1]=99; vol[-1]=2500
    return pd.DataFrame({"trade_date":dates,"open":open_,"high":high,"low":low,"close":close,"vol":vol,"amount":amount})

def by_rule(rows,rule): return next(x for x in rows if x.rule_id==rule)

def test_missing_and_future_isolation():
    f=bars(); f.loc[len(f)] = [pd.Timestamp("2030-01-01"),100,101,99,100,1000,100000]
    rows=strategy_a.scan("000001.SZ","2025-05-21",f)
    assert all(pd.Timestamp(x.signal_date) <= pd.Timestamp("2025-05-21") for x in rows)
    assert by_rule(rows,"A01").state=="CANDIDATE"

def test_insufficient_fields_and_history():
    assert strategy_a.scan("X","2025-01-02",pd.DataFrame({"trade_date":[]}) )[0].state=="INSUFFICIENT_DATA"
    assert strategy_a.scan("X","2025-01-20",bars(10))[0].state=="INSUFFICIENT_DATA"

def test_sos_and_background_do_not_create_buy_signal():
    rows=strategy_a.scan("X","2025-05-21",bars(100,True))
    assert {x.rule_id for x in rows} >= {"A01","A02","A03","A04","A05","A06","A07","A08","A09"}
    assert by_rule(rows,"A07").state=="WATCH"
    assert by_rule(rows,"A08").state=="WATCH"

def test_zero_volume_is_not_fabricated():
    f=bars(); f.loc[50:55,"vol"]=0
    rows=strategy_a.scan("X","2025-05-21",f)
    assert all(x.evidence["threshold_version"]=="A-E4-2026-01" for x in rows)

def test_strategy_is_idempotent_and_namespaced():
    f=bars(); a=strategy_a.scan("X","2025-05-21",f); b=strategy_a.scan("X","2025-05-21",f)
    assert [x.to_dict() for x in a]==[x.to_dict() for x in b]
    assert all(x.strategy_id=="A_WYCKOFF_VOLUME" for x in a)
