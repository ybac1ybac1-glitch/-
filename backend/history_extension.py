import threading
from datetime import datetime,timedelta
import data
_HISTORY_THREAD=None
REQ={'ts_code','trade_date','open','high','low','close','pre_close','change','pct_chg','vol','amount'}

def _target_dates(limit=360):
 end=datetime.now(); start=(end-timedelta(days=700)).strftime('%Y%m%d'); finish=end.strftime('%Y%m%d')
 cal=data._call('trade_cal',exchange='SSE',start_date=start,end_date=finish,is_open='1')
 if cal is None or cal.empty or 'cal_date' not in cal: data._status['history_error']='trade_cal空返回'; return []
 dates=sorted(set(cal.cal_date.astype(str))); data._status['history_calendar_available']=len(dates)
 if len(dates)<limit: data._status['history_error']=f'交易日历仅返回{len(dates)}日，少于目标{limit}日'; return dates
 return dates[-limit:]

def _insert_missing(c,frame):
 cols=['ts_code','trade_date','open','high','low','close','pre_close','change','pct_chg','vol','amount','turnover_rate']; frame=frame.reindex(columns=cols); frame.to_sql('_history_incoming',c,if_exists='replace',index=False)
 c.execute('''INSERT INTO daily SELECT * FROM _history_incoming WHERE ts_code IS NOT NULL AND trade_date IS NOT NULL ON CONFLICT(ts_code,trade_date) DO UPDATE SET turnover_rate=CASE WHEN daily.turnover_rate IS NULL THEN excluded.turnover_rate ELSE daily.turnover_rate END'''); c.execute('DROP TABLE _history_incoming')

def run(limit=360):
 s=data._status; s.update(history_running=True,history_total=0,history_completed=0,history_completed_dates=[],history_error='',history_missing_turnover=0)
 try:
  if data.pro is None: s['history_error']='Tushare未配置'; return data.status()
  c=data._db(); dates=_target_dates(limit); s['history_total']=len(dates)
  if len(dates)<limit:return data.status()
  for i,day in enumerate(dates,1):
   try:
    frame=data._call('daily',trade_date=day)
    if frame is None or frame.empty: raise ValueError(f'{day}: daily空数据')
    if not REQ.issubset(frame.columns): raise ValueError(f'{day}: daily字段不完整')
    basic=data._call('daily_basic',trade_date=day,fields='ts_code,trade_date,turnover_rate')
    if basic is not None and not basic.empty and 'turnover_rate' in basic: frame=frame.merge(basic[['ts_code','trade_date','turnover_rate']],on=['ts_code','trade_date'],how='left')
    else:s['history_missing_turnover']+=len(frame); s['history_error']=f'{day}: daily_basic空或缺字段，换手率待验证'
    _insert_missing(c,frame); c.commit(); s['history_completed']=i; s['history_completed_dates'].append(day)
   except Exception as exc:s['history_error']=str(exc); break
 finally:s['history_running']=False
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
