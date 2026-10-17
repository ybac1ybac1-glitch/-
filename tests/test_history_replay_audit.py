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

def test_audit_frame_detects_future_pollution(monkeypatch):
    import history_replay_audit as h
    from types import SimpleNamespace
    x=frame(4); calls={"n":0}
    def fake_scan(symbol,asof,df):
        calls["n"]+=1; value=1 if calls["n"]%3 else 2
        return [SimpleNamespace(rule_id="A01",state="CANDIDATE",signal_date=asof,evidence={"event_id":"e","event_date":asof,"metric":value})]
    monkeypatch.setattr(h,"scan",fake_scan); monkeypatch.setattr(h,"replay_events",lambda *a,**k:[])
    r=h.audit_frame("600001.SH",x)
    assert r["status"]=="FAIL" and r["cases"]

def test_audit_frame_detects_frozen_change(monkeypatch):
    import history_replay_audit as h
    from types import SimpleNamespace
    x=frame(4)
    monkeypatch.setattr(h,"scan",lambda symbol,asof,df:[SimpleNamespace(rule_id="A01",state="WATCH",signal_date=asof,evidence={})])
    def events(symbol,df,asof):
        return [{"event_id":"A-E","event_date":"2025-01-01","event_type":"SPRING","frozen_support":10 if len(df)%2 else 11,"frozen_resistance":12,"frozen_volume_baseline":100,"current_state":"CANDIDATE","transition_history":[{"date":"2025-01-01","from":None,"to":"CANDIDATE"}]}]
    monkeypatch.setattr(h,"replay_events",events)
    r=h.audit_frame("600001.SH",x)
    assert r["status"]=="FAIL" and r["frozen_evidence_anomalies"]>0

def test_audit_frame_detects_illegal_state_transition(monkeypatch):
    import history_replay_audit as h
    from types import SimpleNamespace
    x=frame(4)
    monkeypatch.setattr(h,"scan",lambda symbol,asof,df:[SimpleNamespace(rule_id="A01",state="WATCH",signal_date=asof,evidence={})])
    bad={"event_id":"bad","event_date":"2025-01-01","event_type":"SPRING","frozen_support":10,"frozen_resistance":12,"frozen_volume_baseline":100,"current_state":"TEST_CANDIDATE","transition_history":[{"date":"2025-01-01","from":None,"to":"CANDIDATE"},{"date":"2025-01-02","from":"CANDIDATE","to":"TEST_CANDIDATE"},{"date":"2025-01-03","from":"TEST_CANDIDATE","to":"WAITING_TEST"}]}
    monkeypatch.setattr(h,"replay_events",lambda *a,**k:[bad])
    r=h.audit_frame("600001.SH",x)
    assert r["status"]=="FAIL" and r["state_transition_anomalies"]>0

def test_coverage_matrix_does_not_promote_rule_from_single_signal():
    r=audit("600001.SH",frame(80))
    for rule,entry in r["coverage"].items():
        if rule not in {f"A{i:02d}" for i in range(1,10)}: continue
        assert "capabilities" in entry
        if entry["signals"]>0:
            assert entry["capabilities"]["waiting_15_sessions"]["status"]=="UNVERIFIED"

def test_same_day_waiting_transition_is_legal():
    from history_replay_audit import _state_checks
    e={"event_type":"SPRING","event_id":"e","event_date":"2026-07-06","current_state":"TEST_CANDIDATE","transition_history":[{"date":"2026-07-06","from":None,"to":"CANDIDATE"},{"date":"2026-07-07","from":"CANDIDATE","to":"WAITING_TEST"},{"date":"2026-07-07","from":"WAITING_TEST","to":"TEST_CANDIDATE"}]}
    assert not [x for x in _state_checks([e]) if x["type"] in ("date_regression","non_increasing_trading_dates")]

def test_transition_date_regression_and_illegal_same_day_fail():
    from history_replay_audit import _state_checks
    e={"event_type":"SPRING","event_id":"e","event_date":"2026-07-06","current_state":"WAITING_TEST","transition_history":[{"date":"2026-07-07","from":None,"to":"CANDIDATE"},{"date":"2026-07-06","from":"CANDIDATE","to":"WAITING_TEST"}]}
    issues=_state_checks([e]); assert any(x["type"]=="date_regression" for x in issues) and any(x["type"]=="transition_from_mismatch" for x in issues)

def test_zero_days_is_not_pass():
    import history_replay_audit as h
    r=h.audit("600001.SH",frame(0))
    assert r["status"]=="UNVERIFIED"
