"""P3.8 read-only multi-stock Strategy A replay audit."""
from __future__ import annotations
import argparse,json,sqlite3,os
import pandas as pd
from history_replay_audit import audit_frame
from strategy_a import replay_events
DEFAULT_STOCKS=["000001.SZ","000858.SZ","002594.SZ","300750.SZ","300059.SZ","600519.SH","600036.SH","601318.SH","601899.SH","688981.SH"]

def _ro(path): return sqlite3.connect("file:"+os.path.abspath(path).replace("\\","/")+"?mode=ro",uri=True)
def _date(v):
 s=str(v).strip()
 d=pd.to_datetime(s,format="%Y%m%d" if s.isdigit() and len(s)==8 else None,errors="coerce")
 return d.normalize() if not pd.isna(d) else None

def _results_meta(path):
 if not path:return {"status":"UNVERIFIED","reason":"未提供results-db，无法比较历史持久化快照"}
 c=None
 try:
  c=_ro(path);tables={r[0] for r in c.execute("select name from sqlite_master where type='table')}
  if "scans" not in tables or "signals" not in tables:return {"status":"UNVERIFIED","reason":"结果库缺少可识别的scans/signals表"}
  row=c.execute("select id,asof_date,signal_count,partial from scans where valid=1 order by id desc limit 1").fetchone()
  if not row:return {"status":"UNVERIFIED","reason":"结果库没有有效快照"}
  return {"status":"UNVERIFIED","reason":"结果库是扫描快照而非逐日历史快照，不能直接证明逐日一致","scan_id":row[0],"asof_date":row[1],"signal_count":row[2],"partial":bool(row[3])}
 finally:
  if c:c.close()

def audit_database(path,stocks,asof=None,results_db=None):
 out={"status":"PASS","database":path,"stocks_requested":stocks,"asof_requested":asof,"actual_asof":None,"stocks_audited":0,"stocks_failed":0,"results":[],"summary":{"PASS":0,"FAIL":0,"UNVERIFIED":0},"results_snapshot":_results_meta(results_db)}
 c=None
 try:
  try:c=_ro(path)
  except Exception as e:out.update(status="UNVERIFIED",error=str(e));return out
  tables={r[0] for r in c.execute("select name from sqlite_master where type='table')")}
  if "daily" not in tables:out.update(status="UNVERIFIED",error="daily表不存在");return out
  cutoff=_date(asof) if asof else None
  for code in stocks:
   try:
    frame=pd.read_sql_query("select * from daily where ts_code=? order by trade_date",c,params=[code])
    if frame.empty:result={"symbol":code,"status":"UNVERIFIED","reason":"无行情数据"}
    else:
     parsed=pd.to_datetime(frame.trade_date.astype(str),errors="coerce")
     if cutoff:
      valid=parsed[parsed<=cutoff]
      if valid.empty: result={"symbol":code,"status":"UNVERIFIED","reason":"截止日期早于该股票最早交易日"}
      else:
       actual=valid.max().normalize();out["actual_asof"]=max(out["actual_asof"] or actual,actual)
       result=audit_frame(code,frame[parsed<=cutoff],None)
     else:result=audit_frame(code,frame,None)
    result["symbol"]=code;out["results"].append(result);out["stocks_audited"]+=1;out["summary"][result["status"]]+=1
   except Exception as e:
    out["stocks_failed"]+=1;out["summary"]["UNVERIFIED"]+=1;out["results"].append({"symbol":code,"status":"UNVERIFIED","reason":str(e)})
  if out["summary"]["FAIL"]:out["status"]="FAIL"
  elif out["summary"]["UNVERIFIED"] or out["stocks_failed"]:out["status"]="UNVERIFIED"
  return out
 finally:
  if c:c.close()

def main():
 p=argparse.ArgumentParser();p.add_argument("--db",required=True);p.add_argument("--stocks",default=",".join(DEFAULT_STOCKS));p.add_argument("--asof");p.add_argument("--results-db");p.add_argument("--json",required=True);a=p.parse_args();r=audit_database(a.db,[x.strip() for x in a.stocks.split(",") if x.strip()],a.asof,a.results_db);print(json.dumps(r,ensure_ascii=False,indent=2));json.dump(r,open(a.json,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
if __name__=="__main__":main()
