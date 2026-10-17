import sqlite3,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
from multi_stock_replay_audit import audit_database

def test_batch_failure_isolated(tmp_path):
 p=tmp_path/"m.sqlite3";c=sqlite3.connect(p);c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real,amount real)")
 for i in range(30):c.execute("insert into daily values('000001.SZ',?,?,?,?,?,?,?)",(f"202601{i+1:02d}",10,11,9,10,100,1000))
 c.commit();c.close()
 r=audit_database(str(p),["000001.SZ","MISSING.SZ"]);assert r["stocks_audited"]==2 and r["completed"]==2 and r["unverified"]>=1 and r["summary"]["UNVERIFIED"]>=1

def test_missing_db_unverified(tmp_path):
 r=audit_database(str(tmp_path/"missing.sqlite3"),["000001.SZ"]);assert r["status"]=="UNVERIFIED"

def test_read_only_batch_does_not_write(tmp_path):
 p=tmp_path/"m.sqlite3";c=sqlite3.connect(p);c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real,amount real)");c.commit();c.close()
 before=p.stat().st_size;audit_database(str(p),["000001.SZ"]);assert p.stat().st_size==before

def test_asof_cuts_through_all_prior_days(tmp_path):
 p=tmp_path/"m.sqlite3";c=sqlite3.connect(p);c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real,amount real)")
 for i in range(30):c.execute("insert into daily values('000001.SZ',?,?,?,?,?,?,?)",(f"202601{i+1:02d}",10,11,9,10,100,1000))
 c.commit();c.close()
 r=audit_database(str(p),["000001.SZ"],"20260115")
 assert r["results"][0]["trading_days_checked"]==15 and r["actual_asof"] is not None

def test_results_db_missing_and_empty_are_unverified(tmp_path):
 p=tmp_path/"m.sqlite3";c=sqlite3.connect(p);c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real,amount real)");c.commit();c.close()
 r=audit_database(str(p),["000001.SZ"],results_db=str(tmp_path/"missing-results.sqlite3"));assert r["results_snapshot"]["status"]=="UNVERIFIED";assert r["actual_asof"] is None

def test_results_db_valid_snapshot_is_read_only(tmp_path):
 p=tmp_path/"m.sqlite3";rdb=tmp_path/"r.sqlite3";c=sqlite3.connect(p);c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real,amount real)");c.commit();c.close()
 c=sqlite3.connect(rdb);c.execute("create table scans(id integer primary key,asof_date text,signal_count integer,partial integer,valid integer)");c.execute("create table signals(scan_id integer)");c.execute("insert into scans values(1,'2026-01-01',0,0,1)");c.commit();c.close()
 r=audit_database(str(p),["000001.SZ"],results_db=str(rdb));assert r["results_snapshot"]["scan_id"]==1

def test_results_schema_missing_partial_is_reported(tmp_path):
 p=tmp_path/"m.sqlite3";rdb=tmp_path/"r.sqlite3";c=sqlite3.connect(p);c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real,amount real)");c.commit();c.close()
 c=sqlite3.connect(rdb);c.execute("create table scans(id integer primary key,asof_date text,signal_count integer,valid integer)");c.execute("create table signals(scan_id integer)");c.commit();c.close()
 r=audit_database(str(p),["000001.SZ"],results_db=str(rdb));assert "partial" in r["results_snapshot"]["reason"]

def test_invalid_asof_is_rejected_not_treated_as_none(tmp_path):
 p=tmp_path/"m.sqlite3";c=sqlite3.connect(p);c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real,amount real)");c.commit();c.close()
 r=audit_database(str(p),["000001.SZ"],asof="20261345");assert r["status"]=="UNVERIFIED" and "asof" in r["error"]

def test_valid_results_db_json_and_counter_consistency(tmp_path):
 p=tmp_path/"m.sqlite3";rdb=tmp_path/"r.sqlite3";c=sqlite3.connect(p);c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real,amount real)")
 for i in range(3):c.execute("insert into daily values('000001.SZ',?,?,?,?,?,?,?)",(f"2026010{i+1}",10,11,9,10,100,1000))
 c.commit();c.close()
 c=sqlite3.connect(rdb);c.execute("create table scans(id integer primary key,asof_date text,signal_count integer,partial integer,valid integer)");c.execute("create table signals(scan_id integer)");c.execute("insert into scans values(1,'2026-01-03',0,0,1)");c.commit();c.close()
 r=audit_database(str(p),["000001.SZ"],asof="2026-01-03",results_db=str(rdb));json.dumps(r);assert r["requested"]==1 and r["completed"]==1 and r["failed"]==0 and r["stocks_audited"]==1

def _make_daily(path, symbols=("A.SZ","B.SZ")):
 c=sqlite3.connect(path);c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real,amount real)")
 for symbol in symbols:
  c.execute("insert into daily values(?,?,?,?,?,?,?,?)",(symbol,"2026-01-01",10,11,9,10,100,1000))
 c.commit();c.close()

def test_progress_is_stderr_and_checkpoint_is_atomic(tmp_path, capsys):
 db=tmp_path/"m.sqlite3"; checkpoint=tmp_path/"checkpoint.json"; _make_daily(db)
 calls=[]
 def fake(symbol, frame, _):
  calls.append(symbol); return {"symbol":symbol,"status":"PASS","trading_days_checked":1}
 report=audit_database(str(db),["A.SZ","B.SZ"],checkpoint=checkpoint,audit_fn=fake)
 captured=capsys.readouterr()
 assert "[1/2]" in captured.err and "A.SZ" in captured.err and "PASS" in captured.err
 assert report["processed"]==2 and checkpoint.exists()
 payload=json.loads(checkpoint.read_text(encoding="utf-8"))
 assert payload["partial"] is True and len(payload["completed"])==2

def test_ctrl_c_checkpoint_and_resume_skips_completed(tmp_path):
 db=tmp_path/"m.sqlite3"; checkpoint=tmp_path/"checkpoint.json"; _make_daily(db)
 calls=[]; interrupted={"value":False}
 def first(symbol, frame, _):
  calls.append(symbol)
  if symbol=="B.SZ" and not interrupted["value"]:
   interrupted["value"]=True; raise KeyboardInterrupt
  return {"symbol":symbol,"status":"PASS","trading_days_checked":1}
 try:
  audit_database(str(db),["A.SZ","B.SZ"],checkpoint=checkpoint,audit_fn=first,progress=False)
 except KeyboardInterrupt:
  pass
 assert checkpoint.exists() and calls==["A.SZ","B.SZ"]
 calls2=[]
 def second(symbol, frame, _):
  calls2.append(symbol); return {"symbol":symbol,"status":"PASS","trading_days_checked":1}
 resumed=audit_database(str(db),["A.SZ","B.SZ"],checkpoint=checkpoint,audit_fn=second,progress=False)
 assert calls2==["B.SZ"] and resumed["processed"]==2 and resumed["checkpoint"]["status"]=="COMPLETE"

def test_checkpoint_fingerprint_mismatch_does_not_reuse(tmp_path):
 db=tmp_path/"m.sqlite3"; checkpoint=tmp_path/"checkpoint.json"; _make_daily(db)
 def fake(symbol, frame, _): return {"symbol":symbol,"status":"PASS","trading_days_checked":1}
 audit_database(str(db),["A.SZ"],asof="2026-01-01",checkpoint=checkpoint,audit_fn=fake,progress=False)
 calls=[]
 audit_database(str(db),["A.SZ"],asof="2026-01-02",checkpoint=checkpoint,audit_fn=lambda s,f,x:(calls.append(s) or {"symbol":s,"status":"PASS"}),progress=False)
 assert calls==["A.SZ"]

def test_failed_stock_is_checkpointed_and_isolated(tmp_path):
 db=tmp_path/"m.sqlite3"; checkpoint=tmp_path/"checkpoint.json"; _make_daily(db)
 def fake(symbol, frame, _):
  if symbol=="B.SZ": raise RuntimeError("synthetic failure")
  return {"symbol":symbol,"status":"PASS"}
 report=audit_database(str(db),["A.SZ","B.SZ"],checkpoint=checkpoint,audit_fn=fake,progress=False)
 assert report["processed"]==2 and report["failed"]==1 and report["stocks_audited"]==1


def test_normal_fail_conclusion_counts_completed_not_failed(tmp_path):
 db=tmp_path/"m.sqlite3"; checkpoint=tmp_path/"checkpoint.json"; _make_daily(db)
 def fake(symbol, frame, _): return {"symbol":symbol,"status":"FAIL","trading_days_checked":1}
 report=audit_database(str(db),["A.SZ"],checkpoint=checkpoint,audit_fn=fake,progress=False)
 assert report["requested"]==1 and report["processed"]==1
 assert report["completed"]==1 and report["failed"]==0
 assert report["summary"]["FAIL"]==1 and report["stocks_audited"]==1

def test_execution_exception_is_not_checkpointed_and_retries(tmp_path):
 db=tmp_path/"m.sqlite3"; checkpoint=tmp_path/"checkpoint.json"; _make_daily(db)
 calls=[]; fail_once={"value":True}
 def fake(symbol, frame, _):
  calls.append(symbol)
  if fail_once["value"]:
   fail_once["value"]=False; raise RuntimeError("transient")
  return {"symbol":symbol,"status":"PASS","trading_days_checked":1}
 first=audit_database(str(db),["A.SZ"],checkpoint=checkpoint,audit_fn=fake,progress=False)
 assert first["processed"]==1 and first["failed"]==1 and first["completed"]==0
 second=audit_database(str(db),["A.SZ"],checkpoint=checkpoint,audit_fn=fake,progress=False)
 assert calls==["A.SZ","A.SZ"] and second["completed"]==1 and second["failed"]==0

def test_database_content_identity_invalidates_checkpoint(tmp_path):
 db=tmp_path/"m.sqlite3"; checkpoint=tmp_path/"checkpoint.json"; _make_daily(db)
 calls=[]
 def fake(symbol, frame, _): calls.append(symbol); return {"symbol":symbol,"status":"PASS"}
 audit_database(str(db),["A.SZ"],checkpoint=checkpoint,audit_fn=fake,progress=False)
 connection=sqlite3.connect(db)
 connection.execute("insert into daily values(?,?,?,?,?,?,?,?)",("A.SZ","2026-01-02",10,11,9,10,100,1000))
 connection.commit(); connection.close()
 calls.clear()
 resumed=audit_database(str(db),["A.SZ"],checkpoint=checkpoint,audit_fn=fake,progress=False)
 assert calls==["A.SZ"] and resumed["checkpoint"]["status"]=="MISMATCH"

def test_checkpoint_counter_invariants(tmp_path):
 db=tmp_path/"m.sqlite3"; checkpoint=tmp_path/"checkpoint.json"; _make_daily(db,("A.SZ","B.SZ"))
 def fake(symbol, frame, _):
  if symbol=="B.SZ": raise RuntimeError("failed")
  return {"symbol":symbol,"status":"UNVERIFIED"}
 report=audit_database(str(db),["A.SZ","B.SZ","C.SZ"],checkpoint=checkpoint,audit_fn=fake,progress=False)
 assert report["requested"]==3
 assert report["processed"]==3
 assert report["completed"]==1
 assert report["failed"]==1
 assert report["unverified"]==1
 assert report["processed"]==report["completed"]+report["failed"]+report["unverified"]
