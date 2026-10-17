import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
from strategy_a import replay_events

def synthetic(n=80):
 d=pd.bdate_range("2026-01-02",periods=n)
 return pd.DataFrame({"trade_date":d,"open":10.0,"high":11.0,"low":9.0,"close":10.0,"vol":100.0,"amount":1000.0})

def test_expiry_never_records_expired_to_expired():
 events=replay_events("002594.SZ",synthetic(80),"20260424")
 for e in events:
  hist=e.get("transition_history",[])
  for h in hist:
   assert not (h.get("from")=="EXPIRED" and h.get("to")=="EXPIRED")

def test_terminal_transition_chain_from_state_is_preserved():
 events=replay_events("002594.SZ",synthetic(120),"20260615")
 for e in events:
  prev=None
  for h in e.get("transition_history",[]):
   assert h.get("from")==prev
   prev=h.get("to")
