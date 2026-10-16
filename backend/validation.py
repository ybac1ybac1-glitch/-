"""Read-only, bounded P2.3 cache validation."""
from __future__ import annotations
import sqlite3,re,threading
from collections import Counter
from urllib.parse import quote
import pandas as pd
from strategy_a import scan
REQUIRED=("ts_code","trade_date","open","high","low","close","vol","amount"); MAX_STORED=100000
_task_lock=threading.Lock(); _snapshot_lock=threading.Lock(); _snapshot=None; _state={"status":"IDLE","processed":0,"scanned":0,"total":0,"failed":0,"abnormal":0,"no_bar_on_asof":0,"asof_date":None,"error":"","result":None}
def _connect(path):
 c=sqlite3.connect("file:"+quote(str(path),safe="/\\:")+"?mode=ro",uri=True);c.execute("PRAGMA query_only=ON");return c
def _date(v):
 s=str(v or "").strip()
 if not re.fullmatch(r"\d{8}",s):raise ValueError("asof_date必须为YYYYMMDD")
 d=pd.to_datetime(s,format="%Y%m%d",errors="coerce")
 if pd.isna(d):raise ValueError("asof_date无效")
 return d,s
def _resolve_asof(c,tables,raw,requested=None):
 if "history_date_tasks" not in tables: raise ValueError("UNVERIFIED: 缺少history_date_tasks")
 if requested is not None:
  cutoff,asof=_date(requested)
  if cutoff>pd.Timestamp.now(tz="UTC").tz_localize(None): raise ValueError("asof_date不能是未来日期")
  row=c.execute("select status,ohlcv_state,turnover_state from history_date_tasks where trade_date=?",(asof,)).fetchone()
  if not row: raise ValueError(f"{asof}: UNVERIFIED，无完整性记录")
  status,ohlcv,turnover=row
  if status in ("FAILED","PARTIAL_MISSING","PENDING_VERIFY") or ohlcv!="OHLCV_COMPLETE" or turnover!="TURNOVER_COMPLETE": raise ValueError(f"{asof}: 历史完整性未验证")
  if asof not in {str(x) for x in raw}: raise ValueError(f"{asof}: daily无行情")
  return cutoff,asof
 rows=c.execute("select trade_date,status,ohlcv_state,turnover_state from history_date_tasks order by trade_date desc").fetchall()
 for day,status,ohlcv,turnover in rows:
  if status not in ("FAILED","PARTIAL_MISSING","PENDING_VERIFY") and ohlcv=="OHLCV_COMPLETE" and turnover=="TURNOVER_COMPLETE" and str(day) in {str(x) for x in raw}:
   return pd.to_datetime(str(day),format="%Y%m%d"),str(day)
 raise ValueError("没有经过完整性验证且存在行情的交易日")

def _compact(rows):
 out=[]
 for e in rows:
  d=e.to_dict();v=d.get("evidence",{})
  out.append({"rule_id":d["rule_id"],"state":d["state"],"signal_date":d["signal_date"],"event_id":v.get("event_id",""),"event_date":v.get("event_date",""),"frozen_support":v.get("frozen_support"),"frozen_resistance":v.get("frozen_resistance"),"risk_level":d.get("risk_level",""),"missing_fields":d.get("missing_fields",[])})
 return out
def validate_cache(path,asof_date=None,batch_size=100,max_results=200,page=1,progress=None):
 if not 1<=int(batch_size)<=1000:return {"errors":["batch_size必须在1到1000之间"]}
 if not 1<=int(max_results)<=10000:return {"errors":["max_results必须在1到10000之间"]}
 out={"asof_date":None,"processed":0,"scanned":0,"total":0,"insufficient":0,"failed":0,"abnormal":0,"no_bar_on_asof":0,"rule_hits":Counter(),"results":[],"errors":[],"read_only":True,"truncated":False,"total_matches":0,"total_signals":0,"returned_matches":0}
 try:c=_connect(path)
 except Exception as e:out["errors"]=[str(e)];return out
 try:
  tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
  if "daily" not in tables:out["errors"]=["daily表不存在"];return out
  cols={r[1] for r in c.execute("pragma table_info(daily)")}
  miss=sorted(set(REQUIRED)-cols)
  if miss:out["errors"]=["缺少字段:"+",".join(miss)];return out
  raw=[r[0] for r in c.execute("select distinct trade_date from daily")];parsed=pd.to_datetime(pd.Series(raw).astype(str),format="%Y%m%d",errors="coerce").dropna()
  if parsed.empty:out["errors"]=["没有可解析的交易日"];return out
  try: cutoff,asof=_resolve_asof(c,tables,raw,asof_date)
  except ValueError as e:return {"errors":[str(e)]}
  out["asof_date"]=asof
  codes=[r[0] for r in c.execute("select distinct ts_code from daily order by ts_code")];out["total"]=len(codes)
  stored=[];out["truncated"]=False
  for start_i in range(0,len(codes),int(batch_size)):
   for code in codes[start_i:start_i+int(batch_size)]:
    out["processed"]+=1
    try:
     frame=pd.read_sql_query("select * from daily where ts_code=? order by trade_date",c,params=[code]);frame["_dt"]=pd.to_datetime(frame.trade_date.astype(str),format="%Y%m%d",errors="coerce");frame=frame[frame._dt.notna()&(frame._dt<=cutoff)].drop(columns="_dt");out["scanned"]+=1
     if frame.empty:out["insufficient"]+=1;continue
     if not (frame.trade_date.astype(str)==asof).any():out["no_bar_on_asof"]+=1;continue
     bad=((frame[["open","high","low","close"]]<=0).any(axis=1)|(frame.high<frame.low)|(frame.open<frame.low)|(frame.open>frame.high)|(frame.close<frame.low)|(frame.close>frame.high)|(frame.vol<0)|(frame.amount<0)).any()
     if bad:out["abnormal"]+=1;continue
     compact=_compact(scan(str(code),asof,frame));hits=[x for x in compact if x["state"] in {"CANDIDATE","CONFIRMED","INVALIDATED"}]
     if any(x["state"]=="INSUFFICIENT_DATA" for x in compact):out["insufficient"]+=1
     for h in hits:out["rule_hits"][h["rule_id"]]+=1
     if hits:
      out["total_matches"]+=1;out["total_signals"]+=len(hits)
      if len(stored)<MAX_STORED:stored.append({"ts_code":str(code),"signals":hits})
      else:out["truncated"]=True
    except Exception as e:
     out["failed"]+=1
     if len(out["errors"])<20:out["errors"].append(f"{code}: {e}")
    if progress:progress(out)
  stored.sort(key=lambda x:x["ts_code"]); out["truncated"]=len(stored)>=MAX_STORED and out["total_matches"]>len(stored); out["results"]=stored; out["returned_matches"]=len(stored); out["rule_hits"]=dict(out["rule_hits"])
  with _snapshot_lock:
   global _snapshot; _snapshot=dict(out)
 finally:c.close()
 return out
def get_results(page=1,page_size=100):
 if int(page)<1 or int(page_size)<1 or int(page_size)>10000: return {"errors":["page/page_size无效"]}
 with _snapshot_lock: snap=dict(_snapshot) if _snapshot else None
 if not snap:return {"status":_state["status"],"results":[],"returned_matches":0}
 rows=snap.get("results",[]); off=(int(page)-1)*int(page_size); snap["results"]=rows[off:off+int(page_size)]; snap["returned_matches"]=len(snap["results"]); snap["page"]=int(page); snap["page_size"]=int(page_size); return snap

def start(path,asof_date=None,batch_size=100,max_results=200):
 if not _task_lock.acquire(False):return {"status":"REJECTED","error":"validation already running"},409
 global _snapshot
 with _snapshot_lock: _snapshot=None
 _state.update(status="RUNNING",processed=0,scanned=0,total=0,failed=0,abnormal=0,no_bar_on_asof=0,error="",result=None,asof_date=asof_date)
 def progress(o):_state.update(processed=o["processed"],scanned=o["scanned"],total=o["total"],failed=o["failed"],abnormal=o["abnormal"],no_bar_on_asof=o["no_bar_on_asof"],asof_date=o["asof_date"])
 def run():
  try:
   r=validate_cache(path,asof_date,batch_size,max_results,progress=progress);_state["result"]=r;_state["status"]="FAILED" if r.get("errors") else "COMPLETED"
  except Exception as e:_state.update(status="FAILED",error=str(e))
  finally:_task_lock.release()
 threading.Thread(target=run,daemon=True).start();return {"status":"RUNNING"},202
def status():
 d=dict(_state); d.pop("result",None); return d
