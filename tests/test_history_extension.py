import sqlite3,sys,tempfile
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
def test_extension_uses_missing_dates_and_preserves_existing(monkeypatch):
 import data,history_extension
 data.DB_PATH=tempfile.mktemp(suffix='.sqlite3'); c=data._db(); old={'ts_code':'X','trade_date':'20240102','open':1,'high':2,'low':.5,'close':1.5,'pre_close':1.4,'change':.1,'pct_chg':7,'vol':10,'amount':100,'turnover_rate':9}; data._upsert(c,pd.DataFrame([old]));c.commit()
 class Fake:
  def daily(self,trade_date): return pd.DataFrame([{**old,'trade_date':trade_date,'turnover_rate':None}])
  def daily_basic(self,**kw): return pd.DataFrame([{'ts_code':'X','trade_date':kw['trade_date'],'turnover_rate':3}])
 data.pro=Fake(); monkeypatch.setattr(history_extension,'_target_dates',lambda n:['20240102','20240103']); history_extension.run(2); assert c.execute('select count(*) from daily').fetchone()[0]==2; assert c.execute("select close from daily where trade_date='20240102'").fetchone()[0]==1.5

def test_no_real_token_on_status():
 import data; assert not data.status().get('token')
