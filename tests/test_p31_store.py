import sys,sqlite3,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
import strategy_a_store as s
def test_empty_store_and_paging(tmp_path):
 p=str(tmp_path/"r.sqlite3"); assert s.results(p)["scan"] is None
def test_store_persists_across_connections(tmp_path,monkeypatch):
 cache=str(tmp_path/"cache.sqlite3"); rpath=str(tmp_path/"r.sqlite3")
 def fake(*a,**k): return {"asof_date":"20250101","total_matches":2,"total_signals":2,"failed":0,"partial":False,"results":[{"ts_code":"A","signals":[{"rule_id":"A01","state":"CANDIDATE","signal_date":"20250101","event_id":"e","evidence":{}}]},{"ts_code":"B","signals":[{"rule_id":"A05","state":"CANDIDATE","signal_date":"20250101","event_id":"f","evidence":{}}] }]}
 monkeypatch.setattr(s,"validate_cache",fake); out,code=s.start(cache,rpath); 
 for _ in range(50):
  if s.status()["status"]!="RUNNING":break
  time.sleep(.01)
 assert s.results(rpath,1,1)["returned_matches"]==1
 assert s.results(rpath,2,1)["items"][0]["ts_code"]=="B"
