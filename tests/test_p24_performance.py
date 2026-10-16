import sys,time
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
import strategy_a

def frame(n):
 d=pd.date_range("2024-01-01",periods=n,freq="B"); c=np.full(n,100.)+np.sin(np.arange(n))
 return pd.DataFrame({"trade_date":d,"open":c,"high":c+1,"low":c-1,"close":c,"vol":1000.,"amount":c*1000})
def test_range_optimization_matches_reference():
 f=frame(120)
 old=[strategy_a.detect_range(f.iloc[:i]) for i in range(len(f))]
 new=strategy_a._event_ranges(f)
 assert old==new
def test_replay_output_stable_across_history_lengths():
 for n in (80,120,240,359):
  f=frame(n); t=time.perf_counter(); a=strategy_a.replay_events("X",f,f.trade_date.iloc[-1]); elapsed=time.perf_counter()-t
  b=strategy_a.replay_events("X",f,f.trade_date.iloc[-1])
  assert a==b
  assert elapsed < 10
def test_validation_stock_limit_is_optional():
 import validation
 assert "max_stocks" in validation.validate_cache.__code__.co_varnames
