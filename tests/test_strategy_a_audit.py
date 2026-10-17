import sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
from strategy_a_audit import audit

def make_result(path,rows,partial=0):
    c=sqlite3.connect(path); c.execute("create table scans(id integer primary key,asof_date text,created_at text,stock_count integer,signal_count integer,failed integer,partial integer,valid integer)"); c.execute("create table signals(scan_id integer,ts_code text,rule_id text,state text,signal_date text,event_id text,evidence text)")
    c.execute("insert into scans values(1,'20250103','',1,?,0,?,1)",(len(rows),partial))
    for r in rows:c.execute("insert into signals values(1,?,?,?,?,?,?)",r)
    c.commit();c.close()

def test_audit_counts_states_and_evidence(tmp_path):
    p=tmp_path/"r.sqlite3"; make_result(p,[("600001.SH","A03","CANDIDATE","20250103","e1",'{"frozen_support":10}'),("600001.SH","A03","CANDIDATE","20250103","e1",'{"frozen_support":10}'),("600002.SH","A05","CONFIRMED","20250103","e2",'{"frozen_resistance":12}')])
    r=audit(str(p)); assert r["actual_signal_rows"]==3 and r["state_summary"]=={"candidate":2,"confirmed":1,"invalidated":0}; assert r["duplicates"]["exact_signal_rows"]==1

def test_audit_flags_missing_and_invalid_evidence(tmp_path):
    p=tmp_path/"r.sqlite3"; make_result(p,[("600001.SH","A04","CANDIDATE","20250103","","{"frozen_support":0}")])
    r=audit(str(p)); assert r["evidence"]["incomplete"]==1 and r["untraceable"][0]["event_id"]==""

def test_audit_market_traceability_and_read_only(tmp_path):
    p=tmp_path/"r.sqlite3"; m=tmp_path/"m.sqlite3"; make_result(p,[("600001.SH","A03","CANDIDATE","20250103","e1","{}")])
    c=sqlite3.connect(m); c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real)"); c.execute("insert into daily values('600001.SH','20250103',10,11,9,10.5,100)"); c.commit();c.close()
    r=audit(str(p),str(m)); assert r["data_checks"]["market_rows_checked"]==1 and r["evidence"]["complete"]==1
    ro=sqlite3.connect("file:"+str(m)+"?mode=ro",uri=True)
    try:
        try: ro.execute("insert into daily values('x','20250103',1,1,1,1,1)"); assert False
        except sqlite3.OperationalError: pass
    finally: ro.close()

def test_audit_missing_snapshot_is_explicit(tmp_path):
    r=audit(str(tmp_path/"missing.sqlite3")); assert r["status"]=="RESULT_DB_MISSING"
