import os, sqlite3, threading, time
from datetime import datetime, timedelta
import pandas as pd
try: import tushare as ts
except Exception: ts=None
from config import TOKEN
BASE=os.path.dirname(__file__); DB_PATH=os.path.join(BASE,'market_cache.sqlite3')
MAX_REQUESTS_PER_MINUTE=int(os.getenv('TUSHARE_MAX_REQUESTS_PER_MINUTE','60'))
_lock=threading.Lock(); _update_lock=threading.Lock(); _turnover_lock=threading.Lock(); _thread=None; _turnover_thread=None; _last_request=0.0
_status={'running':False,'requested':0,'success':0,'failed':0,'completed':0,'total':0,'last_error':'','last_update':''}
pro=None
if ts and TOKEN:
 try: ts.set_token(TOKEN); pro=ts.pro_api()
 except Exception as e: _status['last_error']=str(e)

def _db():
 c=sqlite3.connect(DB_PATH); c.execute('''CREATE TABLE IF NOT EXISTS daily(ts_code TEXT,trade_date TEXT,open REAL,high REAL,low REAL,close REAL,pre_close REAL,change REAL,pct_chg REAL,vol REAL,amount REAL,turnover_rate REAL,PRIMARY KEY(ts_code,trade_date))''');
 cols={r[1] for r in c.execute('PRAGMA table_info(daily)')};
 if 'turnover_rate' not in cols: c.execute('ALTER TABLE daily ADD COLUMN turnover_rate REAL');
 c.execute('CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT)'); c.commit(); return c

def status(): return dict(_status)
def _call(method,**kwargs):
 global _last_request
 with _lock:
  gap=60/max(1,MAX_REQUESTS_PER_MINUTE); wait=gap-(time.monotonic()-_last_request)
  if wait>0: time.sleep(wait)
  _last_request=time.monotonic(); _status['requested']+=1
 try:
  x=getattr(pro,method)(**kwargs); _status['success']+=1; return x
 except Exception as e:
  _status['failed']+=1; _status['last_error']=f'{method}: {e}'; raise

def _upsert(c,frame):
 cols=['ts_code','trade_date','open','high','low','close','pre_close','change','pct_chg','vol','amount','turnover_rate']
 frame=frame.reindex(columns=cols); frame.to_sql('_incoming',c,if_exists='replace',index=False)
 c.execute('''INSERT INTO daily SELECT * FROM _incoming WHERE ts_code IS NOT NULL AND trade_date IS NOT NULL ON CONFLICT(ts_code,trade_date) DO UPDATE SET open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,pre_close=excluded.pre_close,change=excluded.change,pct_chg=excluded.pct_chg,vol=excluded.vol,amount=excluded.amount,turnover_rate=excluded.turnover_rate'''); c.execute('DROP TABLE _incoming')

def _calendar(limit=120):
 if not pro: return []
 end=datetime.now().strftime('%Y%m%d'); start=(datetime.now()-timedelta(days=240)).strftime('%Y%m%d')
 cal=_call('trade_cal',exchange='SSE',start_date=start,end_date=end,is_open='1')
 if cal is None or cal.empty or 'cal_date' not in cal: return []
 return sorted(cal['cal_date'].astype(str).tolist())[-limit:]

def latest_trade_date():
 c=_db(); x=c.execute('SELECT MAX(trade_date) FROM daily').fetchone()[0]; return x or ''

def get_stock_list():
 try: return pd.read_csv(os.path.join(BASE,'stock_list.csv'),dtype={'ts_code':str})
 except Exception: return pd.DataFrame(columns=['ts_code','symbol','name','market'])

def get_stock_data():
 c=_db(); latest=latest_trade_date()
 if not latest: return pd.DataFrame(),'尚未完成历史初始化，请先执行盘后更新'
 d=pd.read_sql_query('SELECT * FROM daily WHERE trade_date=?',c,params=(latest,)); stocks=get_stock_list(); return stocks.merge(d,on='ts_code',how='inner'),' ' if d.empty else ''

def get_history(ts_code,kind='daily',days=240):
 c=_db(); d=pd.read_sql_query('SELECT * FROM daily WHERE ts_code=? ORDER BY trade_date',c,params=(ts_code,))
 if kind=='daily' or d.empty: return d.tail(days)
 d['dt']=pd.to_datetime(d.trade_date); d=d.set_index('dt')
 rule='W-FRI' if kind=='weekly' else 'ME'; out=d.resample(rule).agg({'open':'first','high':'max','low':'min','close':'last','pre_close':'first','change':'sum','vol':'sum','amount':'sum'}).dropna(subset=['close']).reset_index().rename(columns={'dt':'trade_date'}); out['trade_date']=out.trade_date.dt.strftime('%Y%m%d'); return out.tail(days)

def _run_update(max_days=120):
 try:
  _status.update(running=True,requested=0,success=0,failed=0,completed=0,last_error='')
  if not pro: _status['last_error']='Tushare未配置'; return
  c=_db(); dates=_calendar(max_days); existing={r[0] for r in c.execute('SELECT DISTINCT trade_date FROM daily')}; todo=[d for d in dates if d not in existing]; _status['total']=len(todo)
  for i,day in enumerate(todo,1):
   try:
    frame=_call('daily',trade_date=day)
    if frame is None or frame.empty: _status['last_error']=f'{day}: 未发布行情'; break
    if not {'ts_code','trade_date','open','high','low','close','vol'}.issubset(frame.columns): raise ValueError('daily字段不完整')
    basic=_call('daily_basic',trade_date=day,fields='ts_code,trade_date,turnover_rate');
    if basic is not None and not basic.empty and 'turnover_rate' in basic: frame=frame.merge(basic[['ts_code','trade_date','turnover_rate']],on=['ts_code','trade_date'],how='left');
    _upsert(c,frame); c.commit(); _status['completed']=i; _status['last_update']=datetime.now().isoformat()
   except Exception as e: _status['last_error']=str(e); break
 finally: _status['running']=False

def start_update(max_days=120):
 global _thread
 if _status['running'] or (_thread and _thread.is_alive()): return status()
 _thread=threading.Thread(target=_run_update,args=(max_days,),daemon=True); _thread.start(); return status()


def _run_turnover_backfill():
 _status.update(turnover_running=True,turnover_completed=0,turnover_total=0,turnover_error='')
 try:
  c=_db(); dates=[r[0] for r in c.execute("SELECT DISTINCT trade_date FROM daily WHERE turnover_rate IS NULL ORDER BY trade_date").fetchall()]; _status['turnover_total']=len(dates)
  for i,day in enumerate(dates,1):
   try:
    basic=_call('daily_basic',trade_date=day,fields='ts_code,trade_date,turnover_rate')
    if basic is not None and not basic.empty and 'turnover_rate' in basic:
     for _,r in basic.dropna(subset=['ts_code','trade_date','turnover_rate']).iterrows(): c.execute('UPDATE daily SET turnover_rate=? WHERE ts_code=? AND trade_date=?',(float(r.turnover_rate),str(r.ts_code),str(r.trade_date)))
     c.commit()
    _status['turnover_completed']=i
   except Exception as e: _status['turnover_error']=str(e); break
 finally: _status['turnover_running']=False

def start_turnover_backfill():
 global _turnover_thread
 if _status.get('running') or _status.get('turnover_running') or (_turnover_thread and _turnover_thread.is_alive()): return status()
 _turnover_thread=threading.Thread(target=_run_turnover_backfill,daemon=True); _turnover_thread.start(); return status()
