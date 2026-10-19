"""Opt-in automatic after-close refresh loop."""
from __future__ import annotations
import os,threading,time
from datetime import datetime
import data
from history_extension import verify_cached_date
from strategy_a_store import start as start_scan
_thread=None
_stop=threading.Event()
_state={"status":"IDLE","last_error":"","last_run":"","next_retry":""}
_last_scanned_date=None

def run_once():
    global _last_scanned_date
    _state.update(status="UPDATING",last_error="")
    data.start_update(max_days=5)
    deadline=time.time()+3600
    while time.time()<deadline:
        if not data.status().get("running"): break
        time.sleep(1)
    latest=data.latest_trade_date()
    if not latest:
        _state.update(status="UNVERIFIED",last_error="没有可用最新行情")
        return {"status":"UNVERIFIED","reason":"没有可用最新行情"}
    result=verify_cached_date(data.DB_PATH,latest)
    if result.get("status")!="TURNOVER_COMPLETE":
        reason=result.get("error") or result.get("status")
        _state.update(status="UNVERIFIED",last_error=reason,next_retry=datetime.now().isoformat())
        return {"status":"UNVERIFIED","trade_date":latest,"reason":reason}
    if latest==_last_scanned_date:
        _state.update(status="SKIPPED_DUPLICATE",last_run=datetime.now().isoformat())
        return {"status":"SKIPPED_DUPLICATE","trade_date":latest}
    response=start_scan(data.DB_PATH,os.path.join(data.BASE,"strategy_a_results.sqlite3"),latest)
    _last_scanned_date=latest
    _state.update(status="SCAN_STARTED",last_run=datetime.now().isoformat())
    return {"status":"SCAN_STARTED","trade_date":latest,"scan":response}

def _loop(interval):
    while not _stop.wait(interval):
        try: run_once()
        except Exception as exc:
            _state.update(status="FAILED",last_error=str(exc),next_retry=datetime.now().isoformat())

def start_scheduler():
    global _thread
    if os.getenv("AUTO_REFRESH_ENABLED","").lower() not in ("1","true","yes"): return None
    if _thread and _thread.is_alive(): return _thread
    interval=max(300,int(os.getenv("AUTO_REFRESH_INTERVAL_SECONDS","1800")))
    _thread=threading.Thread(target=_loop,args=(interval,),daemon=True,name="strategy-a-auto-refresh")
    _thread.start()
    threading.Thread(target=run_once,daemon=True,name="strategy-a-initial-refresh").start()
    return _thread

def status(): return dict(_state)
def stop_scheduler(): _stop.set()
