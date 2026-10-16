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
def test_calendar_requires_360(monkeypatch):
 import data,history_extension
 class Fake:
  def trade_cal(self,**kw): return pd.DataFrame({'cal_date':[str(20240101+i) for i in range(10)]})
 data.pro=Fake(); data._status['history_error']=''; assert len(history_extension._target_dates(360))==10; assert '少于' in data._status['history_error']
def test_existing_row_not_overwritten(monkeypatch):
 import data,history_extension
 data.DB_PATH=tempfile.mktemp(suffix='.sqlite3'); c=data._db(); old={'ts_code':'X','trade_date':'20240102','open':1,'high':2,'low':.5,'close':1.5,'pre_close':1.4,'change':.1,'pct_chg':7,'vol':10,'amount':100,'turnover_rate':9}; data._upsert(c,pd.DataFrame([old])); c.commit(); history_extension._insert_missing(c,pd.DataFrame([{**old,'close':99,'turnover_rate':None},{**old,'ts_code':'Y','close':2,'turnover_rate':3}])); c.commit(); assert c.execute("select close,turnover_rate from daily where ts_code='X'").fetchone()==(1.5,9); assert c.execute("select close from daily where ts_code='Y'").fetchone()[0]==2
def test_date_task_persistence_skips_complete(monkeypatch):
 import data,history_extension
 data.DB_PATH=tempfile.mktemp(suffix='.sqlite3'); c=data._db(); history_extension._ensure(c); c.execute("INSERT INTO history_date_tasks VALUES('20240102','OHLCV_COMPLETE','TURNOVER_COMPLETE','TURNOVER_COMPLETE',1,1,'','now')"); c.commit(); assert c.execute("select status from history_date_tasks where trade_date='20240102'").fetchone()[0]=='TURNOVER_COMPLETE'
def test_failed_date_is_persisted_for_resume(monkeypatch):
 import data,history_extension
 data.DB_PATH=tempfile.mktemp(suffix='.sqlite3'); c=data._db(); history_extension._ensure(c); c.execute("INSERT INTO history_date_tasks VALUES('20240102','PENDING_VERIFY','PENDING_VERIFY','FAILED',0,0,'network','now')"); c.commit(); assert c.execute("select status from history_date_tasks").fetchone()[0]=='FAILED'
def test_restart_resume_skips_completed_and_retries_failed(monkeypatch):
 import data,history_extension
 data.DB_PATH=tempfile.mktemp(suffix='.sqlite3'); calls=[]; seq=['ok','fail','ok','ok']
 class Fake:
  def trade_cal(self,**kw): return pd.DataFrame({'cal_date':['20240102','20240103']})
  def daily(self,trade_date): calls.append(('daily',trade_date));
  
  def daily_basic(self,**kw): calls.append(('basic',kw['trade_date'])); return pd.DataFrame([{'ts_code':'X','trade_date':kw['trade_date'],'turnover_rate':2}])
 def daily(trade_date):
  calls.append(('daily',trade_date))
  if trade_date=='20240103' and calls.count(('daily','20240103'))==1: raise RuntimeError('mid run')
  return pd.DataFrame([{'ts_code':'X','trade_date':trade_date,'open':1,'high':2,'low':.5,'close':1.5,'pre_close':1.4,'change':.1,'pct_chg':7,'vol':10,'amount':100}])
 Fake.daily=staticmethod(daily); data.pro=Fake(); monkeypatch.setattr(history_extension,'_target_dates',lambda n:['20240102','20240103']); history_extension.run(2); c=data._db(); assert c.execute("select status from history_date_tasks where trade_date='20240102'").fetchone()[0]=='TURNOVER_COMPLETE'; c.close(); history_extension.run(2); c=data._db(); assert c.execute("select count(*) from daily").fetchone()[0]==2; assert c.execute("select close from daily where trade_date='20240102'").fetchone()[0]==1.5; c.close(); assert calls.count(('daily','20240102'))==1
def test_duplicate_daily_basic_not_complete(monkeypatch):
 import data,history_extension
 data.DB_PATH=tempfile.mktemp(suffix='.sqlite3'); calls=[]
 class Fake:
  def daily(self,trade_date): return pd.DataFrame([{'ts_code':'X','trade_date':trade_date,'open':1,'high':2,'low':.5,'close':1.5,'pre_close':1.4,'change':.1,'pct_chg':7,'vol':10,'amount':100}])
  def daily_basic(self,**kw): return pd.DataFrame([{'ts_code':'X','trade_date':kw['trade_date'],'turnover_rate':2},{'ts_code':'X','trade_date':kw['trade_date'],'turnover_rate':2}])
 data.pro=Fake(); monkeypatch.setattr(history_extension,'_target_dates',lambda n:['20240102']); history_extension.run(1); c=data._db(); assert c.execute("select turnover_state from history_date_tasks").fetchone()[0]=='PENDING_VERIFY'; c.close()
