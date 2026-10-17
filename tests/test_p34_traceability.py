import json,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
from strategy_a_audit import audit

def result_db(p):
 c=sqlite3.connect(p);c.execute("create table scans(id integer primary key,asof_date text,created_at text,stock_count integer,signal_count integer,failed integer,partial integer,valid integer)");c.execute("create table signals(scan_id integer,ts_code text,rule_id text,state text,signal_date text,event_id text,evidence text)");c.execute("insert into scans values(1,'2026-10-15','',1,1,0,0,1)");c.execute("insert into signals values(1,'600001.SH','A03','CANDIDATE','2026-10-15','e1','{\"event_id\":\"e1\",\"event_date\":\"2026-10-15\",\"frozen_support\":10}')");c.commit();c.close()

def test_date_formats_match_real_rows_and_counts(tmp_path):
 p=tmp_path/"r.sqlite3";m=tmp_path/"m.sqlite3";result_db(p)
 c=sqlite3.connect(m);c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real)");c.execute("insert into daily values('600001.SH','20261015',10,11,9,10.5,100)");c.commit();c.close()
 r=audit(str(p),str(m));assert r["data_checks"]["market_rows_checked"]==1 and r["data_checks"]["market_rows_matched"]==1 and r["data_checks"]["market_rows_missing"]==0
 json.dumps(r,ensure_ascii=False)

def test_real_missing_row_is_distinct(tmp_path):
 p=tmp_path/"r.sqlite3";m=tmp_path/"m.sqlite3";result_db(p)
 c=sqlite3.connect(m);c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real)");c.commit();c.close()
 r=audit(str(p),str(m));assert r["data_checks"]["market_rows_missing"]==1 and r["data_checks"]["market_rows_matched"]==0

def test_persisted_evidence_fields_are_json_safe(tmp_path):
 p=tmp_path/"r.sqlite3";result_db(p);r=audit(str(p));assert isinstance(r["persistence_audit"]["persisted_fields"],list);json.dumps(r)
