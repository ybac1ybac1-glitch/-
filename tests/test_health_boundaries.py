import sqlite3,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
def test_one_trade_date_not_240(monkeypatch):
 import app,data
 path=tempfile.mktemp(suffix='.sqlite3'); data.DB_PATH=path; c=sqlite3.connect(path); c.execute('CREATE TABLE daily(ts_code TEXT,trade_date TEXT,open REAL,high REAL,low REAL,close REAL,pre_close REAL,change REAL,pct_chg REAL,vol REAL,amount REAL,turnover_rate REAL)'); c.executemany('INSERT INTO daily VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',[('X', '20260102',1,1,1,1,1,0,0,1,200000,1)]*5000); c.commit(); monkeypatch.setattr(app,'render_template',lambda *a,**kw:kw); r=app.data_health(); assert r['global_days']==1; assert r['requirements']['240'] is False
