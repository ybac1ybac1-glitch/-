import sys,sqlite3
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
from validation import validate_cache

def make_db(path):
 c=sqlite3.connect(path); c.execute("CREATE TABLE daily(ts_code TEXT,trade_date TEXT,open REAL,high REAL,low REAL,close REAL,vol REAL,amount REAL)")
 rows=[("X","20250101",100,101,99,100,1000,100000)]*2
 c.executemany("INSERT INTO daily VALUES (?,?,?,?,?,?,?,?)",rows); c.execute("CREATE TABLE history_date_tasks(trade_date TEXT PRIMARY KEY,status TEXT,turnover_state TEXT,ohlcv_state TEXT)"); c.execute("INSERT INTO history_date_tasks VALUES(?,?,?,?)",("20250101","TURNOVER_COMPLETE","TURNOVER_COMPLETE","OHLCV_COMPLETE")); c.commit(); c.close()
def test_read_only_and_batch_scan(tmp_path):
 p=str(tmp_path/"m.sqlite3"); make_db(p)
 r=validate_cache(p,"20250101",batch_size=1)
 assert r["read_only"] and r["scanned"]==1 and r["failed"]==0
 c=sqlite3.connect(p); assert c.execute("select count(*) from daily").fetchone()[0]==2; c.close()
def test_missing_schema_is_explicit(tmp_path):
 p=str(tmp_path/"m.sqlite3"); sqlite3.connect(p).execute("create table daily(ts_code text)").connection.commit()
 r=validate_cache(p); assert r["errors"] and r["scanned"]==0
def test_empty_path_is_safe(tmp_path):
 r=validate_cache(str(tmp_path/"none.sqlite3")); assert r["failed"]==0 and r["errors"]

def test_date_normalization_and_no_bar_status(tmp_path):
 p=str(tmp_path/"m.sqlite3"); make_db(p)
 r=validate_cache(p,"20250101"); assert r["asof_date"]=="20250101"
 r2=validate_cache(p,"20250102"); assert r2["errors"] or r2["no_bar_on_asof"]==1
def test_invalid_or_future_date_is_rejected(tmp_path):
 p=str(tmp_path/"m.sqlite3"); make_db(p)
 assert validate_cache(p,"2025-01-01")["errors"]
 assert validate_cache(p,"29990101")["errors"]
def test_result_size_is_bounded(tmp_path):
 p=str(tmp_path/"m.sqlite3"); make_db(p)
 r=validate_cache(p,"20250101",batch_size=1)
 assert all("states" not in x for x in r["results"])
 assert len(r["errors"])<=20

def test_bounded_matches_and_invalid_batch(tmp_path):
 p=str(tmp_path/"m.sqlite3"); make_db(p)
 r=validate_cache(p,"20250101",batch_size=1,max_results=1)
 assert r["total_matches"]>=r["returned_matches"] and "truncated" in r
 assert validate_cache(p,"20250101",batch_size=0)["errors"]
def test_readonly_connection_rejects_write(tmp_path):
 p=str(tmp_path/"m.sqlite3"); make_db(p)
 import validation
 c=validation._connect(p)
 try:
  try: c.execute("delete from daily")
  except Exception: pass
  else: raise AssertionError("readonly connection allowed write")
 finally: c.close()

def test_verified_date_states_are_required(tmp_path):
 p=str(tmp_path/"m.sqlite3"); make_db(p)
 import validation
 for state in ["FAILED","PARTIAL_MISSING","PENDING_VERIFY"]:
  c=sqlite3.connect(p); c.execute("update history_date_tasks set status=?,ohlcv_state=?,turnover_state=?",(state,"OHLCV_COMPLETE","TURNOVER_COMPLETE")); c.commit(); c.close()
  assert validate_cache(p,"20250101")["errors"]
 c=sqlite3.connect(p); c.execute("update history_date_tasks set status='TURNOVER_COMPLETE',ohlcv_state='OHLCV_COMPLETE',turnover_state='TURNOVER_COMPLETE'"); c.commit(); c.close()
 assert validate_cache(p,"20250101")["asof_date"]=="20250101"

def test_default_date_skips_newer_unverified(tmp_path):
 p=str(tmp_path/"m.sqlite3"); make_db(p); c=sqlite3.connect(p)
 c.execute("insert into daily values (?,?,?,?,?,?,?,?)",("X","20250102",100,101,99,100,1000,100000))
 c.commit(); c.close()
 r=validate_cache(p); assert r["asof_date"]=="20250101"

def test_status_is_compact_and_results_snapshot_separate(tmp_path):
 p=str(tmp_path/"m.sqlite3"); make_db(p)
 import validation
 validation._state.update(status="COMPLETED",processed=1,total=1,result={"results":[{"ts_code":"X"}]}); validation._snapshot={"results":[{"ts_code":"X"}],"returned_matches":1}
 assert "result" not in validation.status()
 assert validation.get_results(1,1)["returned_matches"]==1

def test_processed_counts_failed_stock(tmp_path,monkeypatch):
 p=str(tmp_path/"m.sqlite3"); make_db(p)
 import validation
 original=validation.scan
 def fail(*args,**kwargs): raise RuntimeError("synthetic failure")
 monkeypatch.setattr(validation,"scan",fail)
 r=validate_cache(p,"20250101")
 assert r["processed"]==r["total"]==1 and r["failed"]==1
 monkeypatch.setattr(validation,"scan",original)
