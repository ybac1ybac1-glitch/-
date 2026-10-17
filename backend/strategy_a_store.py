"""Persistent Strategy A V4 result store and background scan."""
from __future__ import annotations
import os,sqlite3,threading,json
from datetime import datetime
from validation import validate_cache
LOCK=threading.Lock()
STATE={"status":"IDLE","processed":0,"total":0,"failed":0,"error":"","asof_date":None,"started_at":"","finished_at":"","max_stocks":None}

def _db(path):
    os.makedirs(os.path.dirname(path) or ".",exist_ok=True)
    c=sqlite3.connect(path)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE IF NOT EXISTS scans(id INTEGER PRIMARY KEY,asof_date TEXT,created_at TEXT,stock_count INTEGER,signal_count INTEGER,failed INTEGER,partial INTEGER,valid INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS signals(scan_id INTEGER,ts_code TEXT,rule_id TEXT,state TEXT,signal_date TEXT,event_id TEXT,evidence TEXT,PRIMARY KEY(scan_id,ts_code,rule_id,state,signal_date))")
    c.execute("CREATE INDEX IF NOT EXISTS ix_signals_scan_code ON signals(scan_id,ts_code)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_signals_scan_rule ON signals(scan_id,rule_id,state)")
    c.commit()
    return c

def _latest(c):
    return c.execute("SELECT * FROM scans WHERE valid=1 ORDER BY id DESC LIMIT 1").fetchone()

def start(cache_path,result_path,asof_date=None,batch_size=100,max_stocks=None):
    if not LOCK.acquire(False):
        return {"status":"REJECTED","error":"scan already running"},409
    STATE.update(status="RUNNING",processed=0,total=0,failed=0,error="",asof_date=asof_date,max_stocks=max_stocks,started_at=datetime.now().isoformat(),finished_at="")
    def run():
        c=None
        try:
            r=validate_cache(cache_path,asof_date,batch_size=batch_size,max_stocks=max_stocks,
                progress=lambda x: STATE.update(processed=x.get("processed",0),total=x.get("total",0),failed=x.get("failed",0),asof_date=x.get("asof_date",asof_date)))
            if r.get("errors"): raise RuntimeError(";".join(r["errors"]))
            if r.get("truncated"): raise RuntimeError("扫描结果已截断，拒绝发布完整结果")
            c=_db(result_path)
            cur=c.execute("INSERT INTO scans(asof_date,created_at,stock_count,signal_count,failed,partial,valid) VALUES(?,?,?,?,?,?,0)",
                (r.get("asof_date"),datetime.now().isoformat(),r.get("total_matches",0),r.get("total_signals",0),r.get("failed",0),int(max_stocks is not None)))
            sid=cur.lastrowid
            for row in r.get("results",[]):
                for sig in row.get("signals",[]):
                    c.execute("INSERT OR REPLACE INTO signals VALUES(?,?,?,?,?,?,?)",
                        (sid,row["ts_code"],sig["rule_id"],sig["state"],sig["signal_date"],sig.get("event_id",""),json.dumps(sig,ensure_ascii=False)))
            persisted=c.execute("SELECT COUNT(*) FROM signals WHERE scan_id=?",(sid,)).fetchone()[0]
            if persisted != int(r.get("total_signals",0)):
                raise RuntimeError(f"持久化信号数不一致: {persisted}!={r.get('total_signals',0)}")
            c.execute("UPDATE scans SET valid=0 WHERE valid=1 AND id<>?",(sid,))
            c.execute("UPDATE scans SET valid=1 WHERE id=?",(sid,))
            c.commit()
            STATE.update(status="COMPLETED",finished_at=datetime.now().isoformat())
        except Exception as e:
            if c is not None:
                try: c.rollback()
                except Exception: pass
            STATE.update(status="FAILED",error=str(e),finished_at=datetime.now().isoformat())
        finally:
            if c is not None:
                try: c.close()
                except Exception: pass
            LOCK.release()
    try:
        threading.Thread(target=run,daemon=True).start()
    except Exception:
        LOCK.release()
        raise
    return {"status":"RUNNING"},202

def status(): return dict(STATE)

def results(result_path,page=1,page_size=100,rule_id=None,state=None,code=None):
    if page<1 or page_size<1 or page_size>1000: raise ValueError("invalid paging")
    c=_db(result_path)
    try:
        s=_latest(c)
        if not s:
            return {"scan":None,"page":page,"page_size":page_size,"total_matches":0,"total_signals":0,"returned_matches":0,"items":[]}
        sid=s[0]; where=["scan_id=?"]; args=[sid]
        if rule_id: where.append("rule_id=?"); args.append(rule_id)
        if state: where.append("state=?"); args.append(state)
        if code: where.append("ts_code LIKE ?"); args.append("%"+code+"%")
        w=" WHERE "+" AND ".join(where)
        total_signals=c.execute("SELECT COUNT(*) FROM signals"+w,args).fetchone()[0]
        total_matches=c.execute("SELECT COUNT(DISTINCT ts_code) FROM signals"+w,args).fetchone()[0]
        rows=c.execute("SELECT ts_code,rule_id,state,signal_date,event_id,evidence FROM signals"+w+" ORDER BY ts_code,rule_id,state,signal_date LIMIT ? OFFSET ?",args+[page_size,(page-1)*page_size]).fetchall()
        return {"scan":{"id":sid,"asof_date":s[1],"stock_count":s[3],"signal_count":s[4],"failed":s[5],"partial":bool(s[6])},"total_matches":total_matches,"total_signals":total_signals,"returned_matches":len(rows),"page":page,"page_size":page_size,"items":[{"ts_code":r[0],"rule_id":r[1],"state":r[2],"signal_date":r[3],"event_id":r[4],"evidence":json.loads(r[5])} for r in rows]}
    finally:
        c.close()
