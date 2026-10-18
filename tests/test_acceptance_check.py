import sys,sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
from acceptance_check import inspect_market,inspect_results,write_report

def test_acceptance_missing_databases(tmp_path):
    assert inspect_market(tmp_path/"market_cache.sqlite3")["exists"] is False
    assert inspect_results(tmp_path/"strategy_a_results.sqlite3")["exists"] is False

def test_acceptance_real_fixture_is_read_only(tmp_path):
    root=tmp_path; backend=root/"backend"; backend.mkdir()
    market=backend/"market_cache.sqlite3"; c=sqlite3.connect(market)
    c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real,amount real)")
    c.execute("insert into daily values('001246.SZ','20261015',1,2,.8,1.5,100,200)")
    c.commit(); c.close()
    result=backend/"strategy_a_results.sqlite3"; c=sqlite3.connect(result)
    c.execute("create table scans(id integer primary key,asof_date text,stock_count integer,signal_count integer,valid integer)")
    c.execute("insert into scans values(1,'20261015',1,1,1)"); c.commit(); c.close()
    before_market=market.read_bytes(); before_result=result.read_bytes()
    report=write_report(root,root/"work"/"acceptance_report.txt")
    assert report["market"]["max_trade_date"]=="20261015"
    assert report["market"]["001246_rows"]==1
    assert report["results"]["latest_scan"]["signal_count"]==1
    assert market.read_bytes()==before_market and result.read_bytes()==before_result
    assert (root/"work"/"acceptance_report.txt").exists()

def test_acceptance_exit_codes_distinguish_market_and_results(tmp_path):
    import subprocess,sys
    script=Path(__file__).parents[1]/"backend"/"acceptance_check.py"
    missing=subprocess.run([sys.executable,str(script),"--root",str(tmp_path),"--report",str(tmp_path/"r.txt")])
    assert missing.returncode==1
    backend=tmp_path/"backend"; backend.mkdir()
    db=backend/"market_cache.sqlite3"; c=sqlite3.connect(db)
    c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real,amount real)")
    c.execute("insert into daily values('001246.SZ','20261015',1,2,.8,1.5,100,200)"); c.commit(); c.close()
    partial=subprocess.run([sys.executable,str(script),"--root",str(tmp_path),"--report",str(tmp_path/"r2.txt")])
    assert partial.returncode==2

def test_smoke_http_500_is_fail_not_pass():
    from acceptance_check import _check
    assert _check(500, True, "v4 error")["status"]=="FAIL"

def test_report_preserves_unverified_without_valid_scan(tmp_path, monkeypatch):
    import acceptance_check
    root=tmp_path; backend=root/"backend"; backend.mkdir()
    db=backend/"market_cache.sqlite3"; c=sqlite3.connect(db)
    c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real,amount real)")
    c.execute("insert into daily values('001246.SZ','20261015',1,2,.8,1.5,100,200)"); c.commit(); c.close()
    monkeypatch.setattr(acceptance_check, "smoke_v4", lambda *args: {"/strategy/a/v4":{"status":"FAIL","http_status":500,"reason":"server error"}})
    report=acceptance_check.write_report(root,root/"work"/"r.txt",smoke=True)
    assert report["conclusion"]=="FAIL"
    assert "500" in (root/"work"/"r.txt").read_text(encoding="utf-8")
