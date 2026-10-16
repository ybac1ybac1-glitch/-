"""Read-only P2.3 validation of cached daily data."""
from __future__ import annotations
import sqlite3
from collections import Counter
import pandas as pd
from strategy_a import scan

REQUIRED=("ts_code","trade_date","open","high","low","close","vol","amount")
def _connect(path):
    return sqlite3.connect(f"file:{path}?mode=ro",uri=True)
def validate_cache(path,asof_date=None,batch_size=100):
    out={"asof_date":asof_date,"scanned":0,"insufficient":0,"failed":0,"abnormal":0,
         "rule_hits":Counter(),"results":[],"errors":[],"read_only":True}
    try: c=_connect(path)
    except Exception as e: out["errors"].append(str(e)); return out
    try:
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "daily" not in tables: out["errors"].append("daily表不存在"); return out
        cols={r[1] for r in c.execute("PRAGMA table_info(daily)")}
        missing=sorted(set(REQUIRED)-cols)
        if missing: out["errors"].append("缺少字段:"+",".join(missing)); return out
        codes=[r[0] for r in c.execute("SELECT DISTINCT ts_code FROM daily ORDER BY ts_code")]
        for start in range(0,len(codes),max(1,batch_size)):
            for code in codes[start:start+batch_size]:
                try:
                    q="SELECT * FROM daily WHERE ts_code=?"
                    params=[code]
                    if asof_date: q+=" AND trade_date<=?"; params.append(str(asof_date))
                    q+=" ORDER BY trade_date"
                    frame=pd.read_sql_query(q,c,params=params)
                    out["scanned"]+=1
                    if frame.empty: out["insufficient"]+=1; continue
                    bad=((frame[["open","high","low","close"]]<=0).any(axis=1)|
                         (frame.high<frame.low)| (frame.vol<0)).sum()
                    if bad: out["abnormal"]+=1
                    rows=scan(str(code),asof_date or str(frame.trade_date.max()),frame)
                    states=[e.to_dict() for e in rows]
                    for e in rows:
                        if e.state in {"CANDIDATE","CONFIRMED","INVALIDATED"}: out["rule_hits"][e.rule_id]+=1
                    if any(e.state=="INSUFFICIENT_DATA" for e in rows): out["insufficient"]+=1
                    out["results"].append({"ts_code":str(code),"states":states})
                except Exception as e:
                    out["failed"]+=1; out["errors"].append(f"{code}: {e}")
    finally: c.close()
    out["rule_hits"]=dict(out["rule_hits"])
    out["representative"]=out["results"][:20]
    return out
