import sys,tempfile,sqlite3
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
def test_old_db_migrates_turnover_without_data_loss(monkeypatch):
 import data
 data.DB_PATH=tempfile.mktemp(suffix='.sqlite3'); c=sqlite3.connect(data.DB_PATH); c.execute('CREATE TABLE daily(ts_code TEXT,trade_date TEXT,open REAL,high REAL,low REAL,close REAL,pre_close REAL,change REAL,pct_chg REAL,vol REAL,amount REAL,PRIMARY KEY(ts_code,trade_date))'); c.execute("INSERT INTO daily VALUES ('600000.SH','20240102',1,1,1,1,1,0,0,100,200000)"); c.commit(); data._db(); cols=[r[1] for r in sqlite3.connect(data.DB_PATH).execute('PRAGMA table_info(daily)')]; assert 'turnover_rate' in cols; assert sqlite3.connect(data.DB_PATH).execute('SELECT COUNT(*) FROM daily').fetchone()[0]==1
def test_daily_basic_merge(monkeypatch):
 import data
 calls=[]
 class Fake:
  def daily(self,**kw): calls.append('daily'); return pd.DataFrame([{'ts_code':'600000.SH','trade_date':'20240102','open':1,'high':1,'low':1,'close':1,'pre_close':1,'change':0,'pct_chg':0,'vol':100,'amount':200000}])
  def daily_basic(self,**kw): calls.append('daily_basic'); return pd.DataFrame([{'ts_code':'600000.SH','trade_date':'20240102','turnover_rate':2.5}])
 data.pro=Fake(); data.DB_PATH=tempfile.mktemp(suffix='.sqlite3'); c=data._db(); data._upsert(c,Fake().daily()); data._upsert(c,Fake().daily().assign(turnover_rate=2.5)); c.commit(); assert c.execute('SELECT turnover_rate FROM daily').fetchone()[0]==2.5
