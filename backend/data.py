import os, sqlite3, threading, time
from datetime import datetime,timedelta
import pandas as pd
try: import tushare as ts
except Exception: ts=None
from config import TOKEN
BASE=os.path.dirname(__file__); DB_PATH=os.path.join(BASE,'market_cache.sqlite3')
MAX_REQUESTS_PER_MINUTE=int(os.getenv('TUSHARE_MAX_REQUESTS_PER_MINUTE','60'))
_lock=threading.Lock(); _update_lock=threading.Lock(); _stats={'requested':0,'success':0,'failed':0,'last_error':''}; _last_request=0.0
pro=None
if ts and TOKEN:
 try: ts.set_token(TOKEN); pro=ts.pro_api()
 except Exception as e: _stats['last_error']=str(e)

def _db():
 c=sqlite3.connect(DB_PATH); c.execute('CREATE TABLE IF NOT EXISTS daily(ts_code TEXT,trade_date TEXT,open REAL,high REAL,low REAL,close REAL,pre_close REAL,change REAL,pct_chg REAL,vol REAL,amount REAL,PRIMARY KEY(ts_code,trade_date))'); c.execute('CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT)'); c.commit(); return c

def stats(): return dict(_stats)
def _call(method,*args,**kwargs):
 global _last_request
 with _lock:
  now=time.monotonic(); min_interval=60.0/max(1,MAX_REQUESTS_PER_MINUTE)
  if now-_last_request<min_interval: time.sleep(min_interval-(now-_last_request))
  _last_request=time.monotonic(); _stats['requested']+=1
 try:
  result=getattr(pro,method)(*args,**kwargs); _stats['success']+=1; return result
 except Exception as e:
  _stats['failed']+=1; _stats['last_error']=f'{method}: {e}'; raise

def latest_trade_date(now=None):
 d=(now or datetime.now()).date()-timedelta(days=1)
 while d.weekday()>=5: d-=timedelta(days=1)
 return d.strftime('%Y%m%d')

def get_stock_list():
 p=os.path.join(BASE,'stock_list.csv')
 try: return pd.read_csv(p,dtype={'ts_code':str})
 except Exception: return pd.DataFrame(columns=['ts_code','symbol','name','market'])

def get_stock_data():
 c=_db(); latest=c.execute('SELECT MAX(trade_date) FROM daily').fetchone()[0];
 if not latest: return pd.DataFrame(), '本地暂无行情缓存，请先执行盘后更新'
 d=pd.read_sql_query('SELECT * FROM daily WHERE trade_date=?',c,params=(latest,)); stocks=get_stock_list(); return stocks.merge(d,on='ts_code',how='inner'), ''

def get_history(ts_code,kind='daily',days=240):
 c=_db(); end=c.execute('SELECT MAX(trade_date) FROM daily').fetchone()[0]
 if not end: return pd.DataFrame()
 start=(datetime.strptime(end,'%Y%m%d')-timedelta(days=days*2)).strftime('%Y%m%d')
 return pd.read_sql_query('SELECT * FROM daily WHERE ts_code=? AND trade_date>=? ORDER BY trade_date',c,params=(ts_code,start))

def update_market(max_days=30):
 if not _update_lock.acquire(False): return {'running':True,**stats()}
 try:
  if pro is None: _stats['last_error']='Tushare未配置或初始化失败'; return {'error':_stats['last_error'],**stats()}
  c=_db(); existing={r[0] for r in c.execute('SELECT DISTINCT trade_date FROM daily')}; target=[]; d=datetime.strptime(latest_trade_date(),'%Y%m%d')
  for _ in range(max_days):
   s=d.strftime('%Y%m%d')
   if s not in existing: target.append(s)
   d-=timedelta(days=1)
   while d.weekday()>=5: d-=timedelta(days=1)
  total=len(target)
  for idx,day in enumerate(reversed(target),1):
   try:
    frame=_call('daily',trade_date=day)
    required={'ts_code','trade_date','open','high','low','close','vol'}
    if not required.issubset(frame.columns): raise ValueError('daily返回字段不完整')
    frame.to_sql('daily',c,if_exists='append',index=False)
    c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('last_update',?)",(datetime.now().isoformat(),)); c.commit()
   except Exception as e:
    _stats['last_error']=str(e); break
  return {'running':False,'total':total,'completed':idx-1 if total else 0,**stats()}
 finally: _update_lock.release()
