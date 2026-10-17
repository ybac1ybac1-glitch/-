import sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
from multi_stock_replay_audit import audit_database

def test_batch_failure_isolated(tmp_path):
 p=tmp_path/"m.sqlite3";c=sqlite3.connect(p);c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real,amount real)")
 for i in range(30):c.execute("insert into daily values('000001.SZ',?,?,?,?,?,?,?)",(f"202601{i+1:02d}",10,11,9,10,100,1000))
 c.commit();c.close()
 r=audit_database(str(p),["000001.SZ","MISSING.SZ"]);assert r["stocks_audited"]==1 and r["completed"]==1 and r["unverified"]>=1 and r["summary"]["UNVERIFIED"]>=1

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
