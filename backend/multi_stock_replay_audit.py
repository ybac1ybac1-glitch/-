"""P3.8 read-only multi-stock Strategy A replay audit."""
from __future__ import annotations
import argparse,json,sqlite3,os
import pandas as pd
from history_replay_audit import audit_frame
DEFAULT_STOCKS=["000001.SZ","000858.SZ","002594.SZ","300750.SZ","300059.SZ","600519.SH","600036.SH","601318.SH","601899.SH","688981.SH"]

def _ro(path): return sqlite3.connect("file:"+os.path.abspath(path).replace("\\","/")+"?mode=ro",uri=True)
def _date(v):
 s=str(v).strip();d=pd.to_datetime(s,format="%Y%m%d" if s.isdigit() and len(s)==8 else None,errors="coerce")
 return d.normalize() if not pd.isna(d) else None

def _results_meta(path):
 if not path:return {"status":"UNVERIFIED","reason":"未提供results-db，无法比较历史持久化快照"}
 c=None
 try:
  c=_ro(path);tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
  if "scans" not in tables or "signals" not in tables:return {"status":"UNVERIFIED","reason":"结果库缺少可识别的scans/signals表"}
  cols={r[1] for r in c.execute("pragma table_info(scans)")}
  required={"id","asof_date","signal_count","valid"}
  if not required<=cols:return {"status":"UNVERIFIED","reason":"scans字段不兼容"}
  row=c.execute("select id,asof_date,signal_count,partial from scans where valid=1 order by id desc limit 1").fetchone()
  if not row:return {"status":"UNVERIFIED","reason":"结果库没有有效快照"}
  return {"status":"UNVERIFIED","reason":"结果库是扫描快照而非逐日历史快照，不能直接证明逐日一致","scan_id":row[0],"asof_date":str(row[1]),"signal_count":row[2],"partial":bool(row[3])}
 except Exception as e:return {"status":"UNVERIFIED","reason":"结果库不可读:"+str(e)}
 finally:
  if c:c.close()

def audit_database(path,stocks,asof=None,results_db=None):
 out={"status":"PASS","database":path,"stocks_requested":stocks,"requested":len(stocks),"completed":0,"unverified":0,"failed":0,"stocks_audited":0,"stocks_failed":0,"results":[],"summary":{"PASS":0,"FAIL":0,"UNVERIFIED":0},"actual_asof":None,"results_snapshot":_results_meta(results_db)}
 c=None
 try:
  try:c=_ro(path)
  except Exception as e:out.update(status="UNVERIFIED",error=str(e));return out
  tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
  if "daily" not in tables:out.update(status="UNVERIFIED",error="daily表不存在");return out
  cutoff=_date(asof) if asof else None
  for code in stocks:
   try:
    frame=pd.read_sql_query("select * from daily where ts_code=? order by trade_date",c,params=[code])
    if frame.empty:result={"symbol":code,"status":"UNVERIFIED","reason":"无行情数据"};out["unverified"]+=1
    else:
     parsed=pd.to_datetime(frame.trade_date.astype(str),errors="coerce")
     use=frame if cutoff is None else frame[parsed<=cutoff]
     if use.empty:result={"symbol":code,"status":"UNVERIFIED","reason":"截止日期早于该股票最早交易日"};out["unverified"]+=1
     else:
      actual=pd.to_datetime(use.trade_date.astype(str),errors="coerce").max().normalize();actual_s=actual.strftime("%Y-%m-%d");out["actual_asof"]=max(out["actual_asof"] or actual_s,actual_s)
      result=audit_frame(code,use,None);result["actual_asof"]=actual_s;out["completed"]+=1
      if result["status"]=="UNVERIFIED":out["unverified"]+=1
    out["results"].append(result);out["summary"][result["status"]]+=1
   except Exception as e:
    out["failed"]+=1;out["stocks_failed"]+=1;out["summary"]["UNVERIFIED"]+=1;out["results"].append({"symbol":code,"status":"UNVERIFIED","reason":str(e)})
  out["stocks_audited"]=out["completed"]
  if out["summary"]["FAIL"]:out["status"]="FAIL"
  elif out["failed"] or out["unverified"]:out["status"]="UNVERIFIED"
  return out
 finally:
  if c:c.close()

def main():
 p=argparse.ArgumentParser();p.add_argument("--db",required=True);p.add_argument("--stocks",default=",".join(DEFAULT_STOCKS));p.add_argument("--asof");p.add_argument("--results-db");p.add_argument("--json",required=True);a=p.parse_args();r=audit_database(a.db,[x.strip() for x in a.stocks.split(",") if x.strip()],a.asof,a.results_db);print(json.dumps(r,ensure_ascii=False,indent=2));json.dump(r,open(a.json,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
if __name__=="__main__":main()
