import threading
from datetime import datetime,timedelta
import pandas as pd
import data

def _target_dates(limit=360):
 cal=data._calendar(limit)
 return sorted(set(str(x) for x in cal))[-limit:]

def run(limit=360):
 s=data._status; s.update(history_running=True,history_total=0,history_completed=0,history_completed_dates=[],history_error='',history_missing_turnover=0)
 try:
  if data.pro is None: s['history_error']='Tushare未配置'; return data.status()
  c=data._db(); dates=_target_dates(limit); existing={r[0] for r in c.execute('SELECT DISTINCT trade_date FROM daily')}; todo=[d for d in dates if d not in existing]; s['history_total']=len(todo)
  for i,day in enumerate(todo,1):
   try:
    frame=data._call('daily',trade_date=day)
    req={'ts_code','trade_date','open','high','low','close','pre_close','change','pct_chg','vol','amount'}
    if frame is None or frame.empty: raise ValueError(f'{day}: daily空数据')
    if not req.issubset(frame.columns): raise ValueError(f'{day}: daily字段不完整')
    try:
     basic=data._call('daily_basic',trade_date=day,fields='ts_code,trade_date,turnover_rate')
     if basic is not None and not basic.empty and 'turnover_rate' in basic:
      frame=frame.merge(basic[['ts_code','trade_date','turnover_rate']],on=['ts_code','trade_date'],how='left')
     else: s['history_missing_turnover']+=len(frame)
    except Exception as exc:
     s['history_missing_turnover']+=len(frame); s['history_error']=f'{day}: daily_basic失败: {exc}'
    data._upsert(c,frame); c.commit(); s['history_completed']=i; s['history_completed_dates'].append(day)
   except Exception as exc:
    s['history_error']=str(exc); break
 finally: s['history_running']=False
 return data.status()

def start(limit=360):
 if not data._task_lock.acquire(False): data._status['task_rejected']+=1; return data.status()
 if data._status.get('running') or data._status.get('turnover_running') or data._status.get('history_running'):
  data._status['task_rejected']+=1; data._task_lock.release(); return data.status()
 def runner():
  try: run(limit)
  except Exception as exc: data._status['history_error']=str(exc)
  finally: data._task_lock.release()
 try: data._thread=threading.Thread(target=runner,daemon=True); data._thread.start()
 except Exception as exc: data._status['history_error']=str(exc); data._task_lock.release()
 return data.status()
