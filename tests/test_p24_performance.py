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

def old_event_ranges(x):
    return [strategy_a.detect_range(x.iloc[:i]) for i in range(len(x))]

def replay_with_old_ranges(symbol, frame, asof):
    original=strategy_a._event_ranges
    strategy_a._event_ranges=old_event_ranges
    try: return strategy_a.replay_events(symbol,frame,asof)
    finally: strategy_a._event_ranges=original

def test_old_new_replay_semantics_and_timing(capsys):
    repeats=3
    for n in (80,120,240,359):
        f=frame(n); asof=f.trade_date.iloc[-1]
        old_times=[]; new_times=[]; old=None; new=None
        for _ in range(repeats):
            t=time.perf_counter(); old=replay_with_old_ranges("X",f,asof); old_times.append(time.perf_counter()-t)
            t=time.perf_counter(); new=strategy_a.replay_events("X",f,asof); new_times.append(time.perf_counter()-t)
        assert new==old
        assert all(set(a)==set(b) for a,b in zip(old,new))
        old_ms=min(old_times)*1000; new_ms=min(new_times)*1000
        speed=old_ms/max(new_ms,1e-9)
        print(f"baseline n={n}: old_ms={old_ms:.3f} new_ms={new_ms:.3f} speedup={speed:.2f}x repeats={repeats}")
