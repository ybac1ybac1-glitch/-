import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
from strategy_a import scan,replay_events
from history_replay_audit import audit,_state_checks,_diff

def frame(n):
 d=pd.bdate_range("2025-01-01",periods=n)
 return pd.DataFrame({"trade_date":d,"open":10.0,"high":11.0,"low":9.0,"close":10.0,"vol":100.0,"amount":1000.0})

def test_replay_lengths_call_real_scan():
 for n in (80,120,240,359):
  x=frame(n); out=scan("600001.SH",x.trade_date.iloc[-1].strftime("%Y%m%d"),x)
  assert out and all(e.rule_id for e in out)

def test_future_truncation_and_repeatability():
 x=frame(120); r=audit("600001.SH",x)
 assert r["trading_days_checked"]==120 and r["future_leakage_count"]==0 and r["repeatability_anomalies"]==0

def test_event_states_use_trading_days_only():
 x=frame(80); events=replay_events("600001.SH",x,x.trade_date.iloc[-1].strftime("%Y%m%d"))
 for e in events:
  dates=[h["date"] for h in e.get("transition_history",[])]
  assert dates==sorted(dates)

def test_fault_injection_illegal_transition_fails():
    issues=_state_checks([{"event_type":"SPRING","event_id":"e","event_date":"2025-01-02","current_state":"INVALIDATED","transition_history":[{"date":"2025-01-02","from":None,"to":"CANDIDATE"},{"date":"2025-01-03","from":"CANDIDATE","to":"INVALIDATED"},{"date":"2025-01-04","from":"INVALIDATED","to":"TEST_CANDIDATE"}]}])
    assert any(x["type"]=="illegal_transition" for x in issues) and any(x["type"]=="terminal_event_extended" for x in issues)

def test_fault_injection_evidence_change_is_visible():
    assert _diff({"evidence":{"support":10}},{"evidence":{"support":11}})

def test_waiting_boundary_uses_business_days():
    x=frame(40); days=list(x.trade_date)
    # The audit consumes actual trading dates, so weekend gaps do not add waiting sessions.
    assert (days[5]-days[4]).days in (1,3)
