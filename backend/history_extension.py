import threading
from datetime import datetime,timedelta
import data
_HISTORY_THREAD=None
REQ={'ts_code','trade_date','open','high','low','close','pre_close','change','pct_chg','vol','amount'}
STATES={'OHLCV_COMPLETE','TURNOVER_COMPLETE','PARTIAL_MISSING','PENDING_VERIFY','FAILED'}
def _ensure(c):
 c.execute('''CREATE TABLE IF NOT EXISTS history_date_tasks(trade_date TEXT PRIMARY KEY, ohlcv_state TEXT NOT NULL, turnover_state TEXT NOT NULL, status TEXT NOT NULL, ohlcv_rows INTEGER DEFAULT 0, turnover_rows INTEGER DEFAULT 0, last_error TEXT, updated_at TEXT NOT NULL)''');c.commit()
def _target_dates(limit=360):
 end=datetime.now(); cal=data._call('trade_cal',exchange='SSE',start_date=(end-timedelta(days=700)).strftime('%Y%m%d'),end_date=end.strftime('%Y%m%d'),is_open='1')
 if cal is None or cal.empty or 'cal_date' not in cal:data._status['history_error']='trade_cal空返回';return []
 dates=sorted(set(cal.cal_date.astype(str)));data._status['history_calendar_available']=len(dates)
 if len(dates)<limit:data._status['history_error']=f'交易日历仅返回{len(dates)}日，少于目标{limit}日';return dates
 return dates[-limit:]
def _insert_missing(c,frame):
 cols=['ts_code','trade_date','open','high','low','close','pre_close','change','pct_chg','vol','amount','turnover_rate'];frame=frame.reindex(columns=cols);frame.to_sql('_history_incoming',c,if_exists='replace',index=False)
 c.execute('''INSERT INTO daily SELECT * FROM _history_incoming WHERE ts_code IS NOT NULL AND trade_date IS NOT NULL ON CONFLICT(ts_code,trade_date) DO UPDATE SET turnover_rate=CASE WHEN daily.turnover_rate IS NULL THEN excluded.turnover_rate ELSE daily.turnover_rate END''');c.execute('DROP TABLE _history_incoming')
def run(limit=360):
 s=data._status;s.update(history_running=True,history_total=0,history_completed=0,history_completed_dates=[],history_error='',history_missing_turnover=0)
 c=None
 try:
  if data.pro is None:s['history_error']='Tushare未配置';return data.status()
  c=data._db();_ensure(c);dates=_target_dates(limit);s['history_total']=len(dates)
  if len(dates)<limit:return data.status()
  for day in dates:
   old=c.execute('SELECT ohlcv_state,turnover_state,status FROM history_date_tasks WHERE trade_date=?',(day,)).fetchone()
   if old and old[2] in ('OHLCV_COMPLETE','TURNOVER_COMPLETE'):continue
   try:
    frame=data._call('daily',trade_date=day)
    if frame is None or frame.empty:raise ValueError(f'{day}: daily空数据')
    if not REQ.issubset(frame.columns):raise ValueError(f'{day}: daily字段不完整')
    ohlcv_rows=len(frame); turnover_state='PENDING_VERIFY'; turnover_rows=0; err=''
    try:
     basic=data._call('daily_basic',trade_date=day,fields='ts_code,trade_date,turnover_rate')
     if basic is not None and not basic.empty and 'turnover_rate' in basic:
      basic=basic.drop_duplicates(['ts_code','trade_date'],keep='last'); frame=frame.merge(basic[['ts_code','trade_date','turnover_rate']],on=['ts_code','trade_date'],how='left'); turnover_rows=int(frame.turnover_rate.notna().sum()); expected=set(frame.ts_code.astype(str)); provided=set(basic.loc[basic.turnover_rate.notna(),'ts_code'].astype(str));
      if provided==expected and len(basic)==len(provided): turnover_state='TURNOVER_COMPLETE'
      else: turnover_state='PARTIAL_MISSING'; err=f'daily_basic覆盖{len(provided)}/{len(expected)}，缺失或重复需复核'
     else:err='daily_basic空或缺字段';turnover_state='PENDING_VERIFY'
    except Exception as exc:err=f'daily_basic失败: {exc}';turnover_state='PARTIAL_MISSING'
    _insert_missing(c,frame);status='TURNOVER_COMPLETE' if turnover_state=='TURNOVER_COMPLETE' else 'PARTIAL_MISSING';c.execute('INSERT OR REPLACE INTO history_date_tasks VALUES(?,?,?,?,?,?,?,?)',(day,'OHLCV_COMPLETE',turnover_state,status,ohlcv_rows,turnover_rows,err,datetime.now().isoformat()));c.commit()
    if status!='TURNOVER_COMPLETE':s['history_missing_turnover']+=max(0,ohlcv_rows-turnover_rows)
   except Exception as exc:
    c.rollback();c.execute('INSERT OR REPLACE INTO history_date_tasks VALUES(?,?,?,?,?,?,?,?)',(day,'PENDING_VERIFY','PENDING_VERIFY','FAILED',0,0,str(exc),datetime.now().isoformat()));c.commit();s['history_error']=str(exc);break
  done=c.execute("SELECT COUNT(*) FROM history_date_tasks WHERE status='TURNOVER_COMPLETE'").fetchone()[0];s['history_completed']=done;s['history_completed_dates']=[r[0] for r in c.execute("SELECT trade_date FROM history_date_tasks WHERE status='TURNOVER_COMPLETE'").fetchall()]
 finally:
  if c is not None:c.close()
  s['history_running']=False
 return data.status()
def start(limit=360):
 global _HISTORY_THREAD
 if not data._task_lock.acquire(False):data._status['task_rejected']+=1;return data.status()
 if data._status.get('running') or data._status.get('turnover_running') or data._status.get('history_running'):
  data._status['task_rejected']+=1;data._task_lock.release();return data.status()
 def runner():
  try:run(limit)
  except Exception as exc:data._status['history_error']=str(exc)
  finally:data._task_lock.release()
 try:_HISTORY_THREAD=threading.Thread(target=runner,daemon=True);_HISTORY_THREAD.start()
 except Exception as exc:data._status['history_error']=str(exc);data._task_lock.release()
 return data.status()
