"""P3.8 read-only multi-stock Strategy A replay audit."""
from __future__ import annotations
import argparse,json,sqlite3,os
import pandas as pd
from history_replay_audit import audit_frame

DEFAULT_STOCKS=["000001.SZ","000858.SZ","002594.SZ","300750.SZ","300059.SZ","600519.SH","600036.SH","601318.SH","601899.SH","688981.SH"]

def _ro(path):
    return sqlite3.connect("file:"+os.path.abspath(path).replace("\\","/")+"?mode=ro",uri=True)

def audit_database(path,stocks,asof=None):
    out={"status":"PASS","database":path,"stocks_requested":stocks,"stocks_audited":0,"stocks_failed":0,"results":[],"summary":{"PASS":0,"FAIL":0,"UNVERIFIED":0}}
    c=None
    try:
        c=_ro(path); tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
        if "daily" not in tables:
            out["status"]="UNVERIFIED";out["error"]="daily表不存在";return out
        for code in stocks:
            try:
                frame=pd.read_sql_query("select * from daily where ts_code=? order by trade_date",c,params=[code])
                if frame.empty:
                    result={"symbol":code,"status":"UNVERIFIED","reason":"无行情数据"}
                else:
                    dates=[asof] if asof else None; result=audit_frame(code,frame,dates)
                out["results"].append(result);out["stocks_audited"]+=1;out["summary"][result["status"]]+=1
            except Exception as e:
                out["stocks_failed"]+=1;out["summary"]["UNVERIFIED"]+=1;out["results"].append({"symbol":code,"status":"UNVERIFIED","reason":str(e)})
        if out["summary"]["FAIL"]:out["status"]="FAIL"
        elif out["summary"]["UNVERIFIED"] or out["stocks_failed"]:out["status"]="UNVERIFIED"
        return out
    finally:
        if c:c.close()

def main():
    p=argparse.ArgumentParser();p.add_argument("--db",required=True);p.add_argument("--stocks",default=",".join(DEFAULT_STOCKS));p.add_argument("--asof");p.add_argument("--json",required=True);a=p.parse_args();r=audit_database(a.db,[x.strip() for x in a.stocks.split(",") if x.strip()],a.asof);print(json.dumps(r,ensure_ascii=False,indent=2));json.dump(r,open(a.json,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
if __name__=="__main__":main()
