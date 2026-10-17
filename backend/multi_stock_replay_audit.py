"""P3.8.1 read-only multi-stock Strategy A replay audit.
Resumable per-stock checkpoints are never treated as a final PASS report.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
import pandas as pd
from history_replay_audit import audit_frame

DEFAULT_STOCKS = ["000001.SZ","000858.SZ","002594.SZ","300750.SZ","300059.SZ","600519.SH","600036.SH","601318.SH","601899.SH","688981.SH"]
CHECKPOINT_SCHEMA = 1
AUDIT_CONFIG_VERSION = "P3.8.1-v1"
STRATEGY_VERSION = "A-P2.2-0.3"

def _ro(path):
    absolute = os.path.abspath(os.fspath(path)).replace("\\\\", "/")
    return sqlite3.connect("file:" + absolute + "?mode=ro", uri=True)

def _date(value):
    text = str(value).strip()
    parsed = pd.to_datetime(text, format="%Y%m%d" if text.isdigit() and len(text)==8 else "%Y-%m-%d", errors="coerce")
    return parsed.normalize() if not pd.isna(parsed) else None

def _results_meta(path):
    if not path:
        return {"status":"UNVERIFIED","reason":"未提供results-db，无法比较历史持久化快照"}
    connection = None
    try:
        connection = _ro(path)
        tables = {r[0] for r in connection.execute("select name from sqlite_master where type='table'")}
        if "scans" not in tables or "signals" not in tables:
            return {"status":"UNVERIFIED","reason":"结果库缺少可识别的scans/signals表"}
        columns = {r[1] for r in connection.execute("pragma table_info(scans)")}
        required = {"id","asof_date","signal_count","partial","valid"}
        missing = required - columns
        if missing:
            return {"status":"UNVERIFIED","reason":"scans字段缺失:"+",".join(sorted(missing))}
        row = connection.execute("select id,asof_date,signal_count,partial from scans where valid=1 order by id desc limit 1").fetchone()
        if not row:
            return {"status":"UNVERIFIED","reason":"结果库没有有效快照"}
        return {"status":"UNVERIFIED","reason":"结果库是扫描快照而非逐日历史快照，不能直接证明逐日一致","scan_id":row[0],"asof_date":str(row[1]),"signal_count":row[2],"partial":bool(row[3])}
    except Exception as exc:
        return {"status":"UNVERIFIED","reason":"结果库不可读:"+str(exc)}
    finally:
        if connection is not None:
            connection.close()

def _code_digest():
    digest = hashlib.sha256()
    for module in (sys.modules.get("history_replay_audit"), sys.modules.get("strategy_a")):
        filename = getattr(module, "__file__", None)
        if filename and os.path.exists(filename):
            with open(filename, "rb") as stream:
                digest.update(stream.read())
    return digest.hexdigest()

def _database_identity(path, stocks=()):
    absolute = os.path.abspath(os.fspath(path))
    stat = os.stat(absolute)
    connection = None
    try:
        connection = _ro(absolute)
        schema = connection.execute("pragma schema_version").fetchone()[0]
        journal = connection.execute("pragma journal_mode").fetchone()[0]
        aggregates = []
        for symbol in stocks:
            row = connection.execute("select count(*), max(rowid), max(trade_date), sum(coalesce(close,0)), sum(coalesce(vol,0)) from daily where ts_code=?", (symbol,)).fetchone()
            aggregates.append([symbol, list(row) if row else None])
        return {"size":stat.st_size,"mtime_ns":stat.st_mtime_ns,"schema_version":schema,"journal_mode":journal,"stock_aggregates":aggregates}
    finally:
        if connection is not None:
            connection.close()

def _fingerprint(path, stocks, asof, results_db):
    try:
        identity = _database_identity(path, stocks)
    except (OSError, sqlite3.Error) as exc:
        identity = {"unavailable": type(exc).__name__, "detail": str(exc)}
    payload = {"database":os.path.abspath(os.fspath(path)),"database_identity":identity,"stocks":list(stocks),"asof":asof,"results_db":os.path.abspath(os.fspath(results_db)) if results_db else None,"strategy_version":STRATEGY_VERSION,"audit_config":AUDIT_CONFIG_VERSION,"code_digest":_code_digest()}
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode("utf-8")).hexdigest()

def _atomic_json(path, value):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=str(destination.parent),prefix=destination.name+".",suffix=".tmp",delete=False)
    temporary = Path(handle.name)
    try:
        with handle:
            json.dump(value,handle,ensure_ascii=False,indent=2,sort_keys=True)
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary,destination)
    finally:
        if temporary.exists(): temporary.unlink()

def _checkpoint_payload(fingerprint, completed, interrupted=False):
    return {"schema_version":CHECKPOINT_SCHEMA,"fingerprint":fingerprint,"strategy_version":STRATEGY_VERSION,"audit_config":AUDIT_CONFIG_VERSION,"partial":True,"interrupted":bool(interrupted),"completed":completed}

def _load_checkpoint(path, fingerprint, requested):
    if not path: return [], "DISABLED"
    checkpoint = Path(path)
    if not checkpoint.exists(): return [], "NEW"
    try:
        with checkpoint.open("r",encoding="utf-8") as stream: payload=json.load(stream)
        if not isinstance(payload,dict) or payload.get("schema_version") != CHECKPOINT_SCHEMA or payload.get("fingerprint") != fingerprint: return [], "MISMATCH"
        entries=payload.get("completed")
        if not isinstance(entries,list): return [], "INVALID"
        allowed=set(requested); clean=[]; seen=set()
        for entry in entries:
            if not isinstance(entry,dict) or entry.get("symbol") not in allowed or entry["symbol"] in seen or not isinstance(entry.get("result"),dict): return [], "INVALID"
            seen.add(entry["symbol"]); clean.append(entry)
        return clean, "RESUMED" if clean else "NEW"
    except (OSError,ValueError,TypeError,KeyError):
        return [], "INVALID"

def _progress(message):
    print("[P3.8.1] "+message,file=sys.stderr,flush=True)

def audit_database(path, stocks, asof=None, results_db=None, checkpoint=None, progress=True, audit_fn: Callable | None = None):
    requested=list(stocks); fingerprint=_fingerprint(path,requested,asof,results_db)
    completed_entries, checkpoint_status = _load_checkpoint(checkpoint,fingerprint,requested)
    cached={entry["symbol"]:entry for entry in completed_entries}
    out={"status":"PASS","database":os.fspath(path),"stocks_requested":requested,"requested":len(requested),"completed":0,"unverified":0,"failed":0,"stocks_audited":0,"stocks_failed":0,"processed":0,"results":[],"summary":{"PASS":0,"FAIL":0,"UNVERIFIED":0},"actual_asof":None,"results_snapshot":_results_meta(results_db),"checkpoint":{"path":os.fspath(checkpoint) if checkpoint else None,"status":checkpoint_status,"load_status":checkpoint_status,"fingerprint":fingerprint},"timing":{"started_at":datetime.now(timezone.utc).isoformat(),"elapsed_seconds":0.0,"per_stock":{},"phase_totals":{"data_preparation_seconds":0.0,"audit_frame_seconds":0.0}}}
    started=time.perf_counter(); connection=None; evaluator=audit_fn or audit_frame
    def save_checkpoint(entries, interrupted=False):
        if checkpoint: _atomic_json(checkpoint,_checkpoint_payload(fingerprint,entries,interrupted))
    try:
        try:
            connection = _ro(path)
        except Exception as exc:
            out.update(status="UNVERIFIED", error="行情库不可读: " + str(exc))
            return out
        tables={r[0] for r in connection.execute("select name from sqlite_master where type='table'")}
        if "daily" not in tables:
            out.update(status="UNVERIFIED",error="daily表不存在"); return out
        cutoff=_date(asof) if asof is not None else None
        if asof is not None and cutoff is None:
            out.update(status="UNVERIFIED",error="asof格式或日期无效，必须为YYYYMMDD或YYYY-MM-DD"); return out
        if progress: _progress(f"进入逐日重放阶段，共 {len(requested)} 只股票")
        entries=list(completed_entries)
        for position, code in enumerate(requested, start=1):
            execution_error = False
            prep_elapsed = 0.0
            audit_elapsed = 0.0
            if code in cached:
                result = cached[code]["result"]
                elapsed = float(cached[code].get("elapsed_seconds", 0.0))
                prep_elapsed = float(cached[code].get("data_preparation_seconds", 0.0))
                audit_elapsed = float(cached[code].get("audit_frame_seconds", 0.0))
                if progress:
                    _progress(f"[{position}/{len(requested)}] {code} 已从检查点恢复，已完成 {len(entries)}")
            else:
                one_started = time.perf_counter()
                if progress:
                    _progress(f"[{position}/{len(requested)}] 开始 {code}，已完成 {len(entries)}")
                try:
                    frame = pd.read_sql_query(
                        "select * from daily where ts_code=? order by trade_date",
                        connection, params=[code],
                    )
                    if frame.empty:
                        result = {"symbol": code, "status": "UNVERIFIED", "reason": "无行情数据"}
                    else:
                        parsed = pd.to_datetime(frame["trade_date"].astype(str), errors="coerce")
                        use = frame if cutoff is None else frame.loc[parsed <= cutoff]
                        if use.empty:
                            result = {"symbol": code, "status": "UNVERIFIED", "reason": "截止日期早于该股票最早交易日"}
                        else:
                            actual = pd.to_datetime(use["trade_date"].astype(str), errors="coerce").max().normalize()
                            prep_elapsed = time.perf_counter() - one_started
                            audit_started = time.perf_counter()
                            result = dict(evaluator(code, use, None))
                            result["actual_asof"] = actual.strftime("%Y-%m-%d")
                            audit_elapsed = time.perf_counter()
                    elapsed = time.perf_counter() - one_started
                except KeyboardInterrupt:
                    save_checkpoint(entries, interrupted=True)
                    _progress(f"收到中断，已保存 {len(entries)} 只股票的检查点")
                    raise
                except Exception as exc:
                    elapsed = time.perf_counter() - one_started
                    execution_error = True
                    result = {"symbol": code, "status": "UNVERIFIED", "reason": "审计执行异常: " + str(exc)}
                    out["failed"] += 1
                    out["stocks_failed"] += 1
                if not execution_error:
                    entry = {"symbol": code, "result": result, "elapsed_seconds": elapsed, "data_preparation_seconds": prep_elapsed, "audit_frame_seconds": audit_elapsed}
                    entries.append(entry)
                    cached[code] = entry
                    save_checkpoint(entries)
                if progress:
                    state = "异常" if execution_error else result.get("status", "UNVERIFIED")
                    _progress(f"[{position}/{len(requested)}] 完成 {code}，已完成 {len(entries)}，耗时 {elapsed:.2f}s，{state}")
            out["timing"]["per_stock"][code] = {"total_seconds": elapsed, "data_preparation_seconds": prep_elapsed, "audit_frame_seconds": audit_elapsed}
            out["timing"]["phase_totals"]["data_preparation_seconds"] += prep_elapsed
            out["timing"]["phase_totals"]["audit_frame_seconds"] += audit_elapsed
            out["results"].append(result)
            out["processed"] += 1
            status = result.get("status", "UNVERIFIED")
            if execution_error:
                continue
            out["completed"] += 1
            out["summary"].setdefault(status, 0)
            out["summary"][status] += 1
            if status == "UNVERIFIED":
                out["unverified"] += 1
            elif status == "FAIL":
                out["status"] = "FAIL"
            out["stocks_audited"] += 1
            actual = result.get("actual_asof")
            if actual and (out["actual_asof"] is None or actual > out["actual_asof"]):
                out["actual_asof"] = actual
        if out["summary"].get("FAIL",0): out["status"]="FAIL"
        elif out["failed"] or out["unverified"]: out["status"]="UNVERIFIED"
        out["timing"]["elapsed_seconds"]=time.perf_counter()-started; out["checkpoint"]["status"]="COMPLETE"; return out
    finally:
        if connection is not None: connection.close()

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--db",required=True); parser.add_argument("--stocks",default=",".join(DEFAULT_STOCKS)); parser.add_argument("--asof"); parser.add_argument("--results-db"); parser.add_argument("--checkpoint",help="逐股票 JSON 检查点路径"); parser.add_argument("--json",required=True); args=parser.parse_args(argv)
    stocks=[item.strip() for item in args.stocks.split(",") if item.strip()]
    report=audit_database(args.db,stocks,args.asof,args.results_db,checkpoint=args.checkpoint,progress=True)
    print(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)); _atomic_json(args.json,report)

if __name__=="__main__": main()
