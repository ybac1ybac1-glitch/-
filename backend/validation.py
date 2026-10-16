"""Read-only P2.3 validation of cached daily data."""
from __future__ import annotations
import sqlite3,re
from collections import Counter
import pandas as pd
from strategy_a import scan
REQUIRED=("ts_code","trade_date","open","high","low","close","vol","amount")
def _connect(path): return sqlite3.connect(f"file:{path}?mode=ro",uri=True)
def _date(v):
 s=str(v or "").strip()
 if not re.fullmatch(r"\d{8}",s): raise ValueError("asof_date必须为YYYYMMDD")
 d=pd.to_datetime(s,format="%Y%m%d",errors="coerce")
 if pd.isna(d): raise ValueError("asof_date无效")
 return d,s
def _compact(rows):
 out=[]
 for e in rows:
  d=e.to_dict(); ev=d.get("evidence",{})
  out.append({"rule_id":d["rule_id"],"state":d["state"],"signal_date":d["signal_date"],
    "event_id":ev.get("event_id",""),"event_date":ev.get("event_date",""),
    "frozen_support":ev.get("frozen_support"),"frozen_resistance":ev.get("frozen_resistance"),
    "risk_level":d.get("risk_level",""),"missing_fields":d.get("missing_fields",[])})
 return out
def validate_cache(path,asof_date=None,batch_size=100):
 out={"asof_date":None,"scanned":0,"insufficient":0,"failed":0,"abnormal":0,"no_bar_on_asof":0,
      "rule_hits":Counter(),"results":[],"errors":[],"read_only":True,"truncated":False}
 try:c=_connect(path)
 except Exception as e:out["errors"]=[str(e)];return out
 try:
  tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  if "daily" not in tables:out["errors"]=["daily表不存在"];return out
  cols={r[1] for r in c.execute("PRAGMA table_info(daily)")}
  missing=sorted(set(REQUIRED)-cols)
  if missing:out["errors"]=["缺少字段:"+",".join(missing)];return out
  raw_dates=[r[0] for r in c.execute("SELECT DISTINCT trade_date FROM daily")]
  parsed=pd.to_datetime(pd.Series(raw_dates).astype(str),format="%Y%m%d",errors="coerce").dropna()
  if parsed.empty:out["errors"]=["没有可解析的交易日"];return out
  if asof_date is None: cutoff=parsed.max(); asof=cutoff.strftime("%Y%m%d")
  else:
   cutoff,asof=_date(asof_date)
   if cutoff>pd.Timestamp.utcnow().tz_localize(None):out["errors"]=["asof_date不能是未来日期"];return out
  out["asof_date"]=asof
  codes=[r[0] for r in c.execute("SELECT DISTINCT ts_code FROM daily ORDER BY ts_code")]
  for start in range(0,len(codes),max(1,batch_size)):
   for code in codes[start:start+batch_size]:
    try:
     frame=pd.read_sql_query("SELECT * FROM daily WHERE ts_code=? ORDER BY trade_date",c,params=[code])
     frame["_dt"]=pd.to_datetime(frame.trade_date.astype(str),format="%Y%m%d",errors="coerce")
     frame=frame[frame._dt.notna()& (frame._dt<=cutoff)].drop(columns=["_dt"])
     out["scanned"]+=1
     if frame.empty:out["insufficient"]+=1;continue
     if not (frame.trade_date.astype(str)==asof).any():
      out["no_bar_on_asof"]+=1
      out["results"].append({"ts_code":str(code),"status":"NO_BAR_ON_ASOF"});continue
     bad=((frame[["open","high","low","close"]]<=0).any(axis=1)|(frame.high<frame.low)|(frame.vol<0)).sum()
     if bad:out["abnormal"]+=1
     rows=scan(str(code),asof,frame)
     compact=_compact(rows)
     hits=[x for x in compact if x["state"] in {"CANDIDATE","CONFIRMED","INVALIDATED"}]
     for x in hits:out["rule_hits"][x["rule_id"]]+=1
     if any(x["state"]=="INSUFFICIENT_DATA" for x in compact):out["insufficient"]+=1
     if hits:out["results"].append({"ts_code":str(code),"status":"SCANNED","signals":hits})
    except Exception as e:
     out["failed"]+=1
     if len(out["errors"])<20:out["errors"].append(f"{code}: {e}")
  out["truncated"]=out["scanned"]>len(out["results"])+out["no_bar_on_asof"]
 finally:c.close()
 out["rule_hits"]=dict(out["rule_hits"]);out["representative"]=out["results"][:20]
 return out
