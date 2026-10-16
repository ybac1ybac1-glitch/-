"""Read-only, bounded P2.3 cache validation."""
from __future__ import annotations
import sqlite3,re,threading
from collections import Counter
from urllib.parse import quote
import pandas as pd
from strategy_a import scan
REQUIRED=("ts_code","trade_date","open","high","low","close","vol","amount")
_task_lock=threading.Lock(); _task=None; _state={"status":"IDLE","scanned":0,"total":0,"error":"","result":None}
def _connect(path):
 c=sqlite3.connect("file:"+quote(str(path),safe="/\\:")+"?mode=ro&immutable=1",uri=True)
 c.execute("PRAGMA query_only=ON"); return c
def _date(v):
 s=str(v or "").strip()
 if not re.fullmatch(r"\d{8}",s):raise ValueError("asof_date必须为YYYYMMDD")
 d=pd.to_datetime(s,format="%Y%m%d",errors="coerce")
 if pd.isna(d):raise ValueError("asof_date无效")
 return d,s
def _compact(rows):
 out=[]
 for e in rows:
  d=e.to_dict();v=d.get("evidence",{})
  out.append({"rule_id":d["rule_id"],"state":d["state"],"signal_date":d["signal_date"],"event_id":v.get("event_id",""),"event_date":v.get("event_date",""),"frozen_support":v.get("frozen_support"),"frozen_resistance":v.get("frozen_resistance"),"risk_level":d.get("risk_level",""),"missing_fields":d.get("missing_fields",[])})
 return out
def validate_cache(path,asof_date=None,batch_size=100,max_results=200,page=1):
 if not 1<=int(batch_size)<=1000: return {"errors":["batch_size必须在1到1000之间"]}
 if not 1<=int(max_results)<=10000:return {"errors":["max_results必须在1到10000之间"]}
 out={"asof_date":None,"scanned":0,"total":0,"insufficient":0,"failed":0,"abnormal":0,"no_bar_on_asof":0,"rule_hits":Counter(),"results":[],"errors":[],"read_only":True,"truncated":False,"total_matches":0,"returned_matches":0}
 try:c=_connect(path)
 except Exception as e:out["errors"]=[str(e)];return out
 try:
  tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
  if "daily" not in tables:out["errors"]=["daily表不存在"];return out
  cols={r[1] for r in c.execute("pragma table_info(daily)")}
  miss=sorted(set(REQUIRED)-cols)
  if miss:out["errors"]=["缺少字段:"+",".join(miss)];return out
  raw=[r[0] for r in c.execute("select distinct trade_date from daily")]; parsed=pd.to_datetime(pd.Series(raw).astype(str),format="%Y%m%d",errors="coerce").dropna()
  if parsed.empty:out["errors"]=["没有可解析的交易日"];return out
  if asof_date is None:cutoff=parsed.max();asof=cutoff.strftime("%Y%m%d")
  else:
   try:cutoff,asof=_date(asof_date)
   except ValueError as e:return {"errors":[str(e)]}
   if cutoff>pd.Timestamp.now(tz="UTC").tz_localize(None):return {"errors":["asof_date不能是未来日期"]}
  out["asof_date"]=asof; codes=[r[0] for r in c.execute("select distinct ts_code from daily order by ts_code")];out["total"]=len(codes)
  all_hits=[]
  for start in range(0,len(codes),int(batch_size)):
   for code in codes[start:start+int(batch_size)]:
    try:
     frame=pd.read_sql_query("select * from daily where ts_code=? order by trade_date",c,params=[code]); frame["_dt"]=pd.to_datetime(frame.trade_date.astype(str),format="%Y%m%d",errors="coerce"); frame=frame[frame._dt.notna()&(frame._dt<=cutoff)].drop(columns="_dt");out["scanned"]+=1
     if frame.empty:out["insufficient"]+=1;continue
     if not (frame.trade_date.astype(str)==asof).any():out["no_bar_on_asof"]+=1;continue
     bad=((frame[["open","high","low","close"]]<=0).any(axis=1)|(frame.high<frame.low)|(frame.open<frame.low)|(frame.open>frame.high)|(frame.close<frame.low)|(frame.close>frame.high)|(frame.vol<0)|(frame.amount<0)).any()
     if bad:out["abnormal"]+=1;continue
     rows=scan(str(code),asof,frame); compact=_compact(rows);hits=[x for x in compact if x["state"] in {"CANDIDATE","CONFIRMED","INVALIDATED"}]
     if any(x["state"]=="INSUFFICIENT_DATA" for x in compact):out["insufficient"]+=1
     for h in hits:out["rule_hits"][h["rule_id"]]+=1;all_hits.append({"ts_code":str(code),"signals":hits})
    except Exception as e:
     out["failed"]+=1
     if len(out["errors"])<20:out["errors"].append(f"{code}: {e}")
  out["total_matches"]=sum(out["rule_hits"].values());out["truncated"]=len(all_hits)>max_results
  start=(int(page)-1)*int(max_results);out["results"]=all_hits[start:start+int(max_results)];out["returned_matches"]=len(out["results"]);out["rule_hits"]=dict(out["rule_hits"])
 finally:c.close()
 return out
def start(path,asof_date=None,batch_size=100,max_results=200):
 global _task
 if not _task_lock.acquire(False):return {"status":"REJECTED","error":"validation already running"}
 _state.update(status="RUNNING",scanned=0,total=0,error="",result=None)
 def run():
  try:_state["result"]=validate_cache(path,asof_date,batch_size,max_results);_state["status"]="FAILED" if _state["result"].get("errors") else "COMPLETED"
  except Exception as e:_state.update(status="FAILED",error=str(e))
  finally:_task_lock.release()
 _task=threading.Thread(target=run,daemon=True);_task.start();return {"status":"RUNNING"}
def status():return dict(_state)
