import sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
from history_extension import verify_cached_date

def _db(path, turnover=True):
    c=sqlite3.connect(path)
    c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,pre_close real,change real,pct_chg real,vol real,amount real,turnover_rate real)")
    c.execute("insert into daily values('001246.SZ','20261016',1,1.1,.9,1.05,1,0,5,100,200,?)",(1.2 if turnover else None,))
    c.commit(); c.close()

def test_latest_cached_day_complete_only_with_turnover_and_backup(tmp_path, monkeypatch):
    import data
    monkeypatch.setattr(data, "get_stock_list", lambda: __import__('pandas').DataFrame({'ts_code':['001246.SZ']}))
    db=tmp_path/"market.sqlite3"; backup=tmp_path/"backup.sqlite3"; _db(db,True)
    result=verify_cached_date(str(db),"latest",str(backup))
    assert result["status"]=="TURNOVER_COMPLETE"
    assert backup.exists()
    c=sqlite3.connect(db); row=c.execute("select status,ohlcv_state,turnover_state from history_date_tasks where trade_date='20261016'").fetchone(); c.close()
    assert row==("TURNOVER_COMPLETE","OHLCV_COMPLETE","TURNOVER_COMPLETE")

def test_latest_cached_day_missing_turnover_is_not_complete(tmp_path, monkeypatch):
    import data
    monkeypatch.setattr(data, "get_stock_list", lambda: __import__('pandas').DataFrame({'ts_code':['001246.SZ']}))
    db=tmp_path/"market.sqlite3"; _db(db,False)
    result=verify_cached_date(str(db),"latest",str(tmp_path/"backup.sqlite3"))
    assert result["status"]=="PARTIAL_MISSING"
