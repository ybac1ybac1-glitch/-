"""Opt-in automatic after-close refresh loop.

Disabled by default. Set AUTO_REFRESH_ENABLED=1 to enable on a machine that has
Tushare configured; the loop never runs during tests or without explicit opt-in.
"""
from __future__ import annotations
import os, threading, time
from datetime import datetime
import data
from history_extension import verify_cached_date
from strategy_a_store import start as start_scan

_thread=None
_stop=threading.Event()

def run_once():
    data.start_update(max_days=5)
    deadline=time.time()+3600
    while data.status().get("running") and time.time()<deadline: time.sleep(1)
    latest=data.latest_trade_date()
    if not latest: _state.update(status="UNVERIFIED",last_error="没有可用最新行情"); return {"status":"UNVERIFIED","reason":"没有可用最新行情"}
    result=verify_cached_date(data.DB_PATH,latest)
    if result.get("status")!="TURNOVER_COMPLETE":
        return {"status":"UNVERIFIED","trade_date":latest,"reason":result.get("error") or result.get("status")}
    return {"status":"SCAN_STARTED","trade_date":latest,"scan":start_scan(data.DB_PATH,os.path.join(data.BASE,"strategy_a_results.sqlite3"),latest)}

def _loop(interval):
    while not _stop.wait(interval):
        try: run_once()
        except Exception: pass

def start_scheduler():
    global _thread
    if os.getenv("AUTO_REFRESH_ENABLED","").lower() not in ("1","true","yes"): return None
    if _thread and _thread.is_alive(): return _thread
    interval=max(300,int(os.getenv("AUTO_REFRESH_INTERVAL_SECONDS","1800")))
    _thread=threading.Thread(target=_loop,args=(interval,),daemon=True,name="strategy-a-auto-refresh")
    _thread.start()
    return _thread

def status(): return dict(_state)\n\ndef stop_scheduler():
    _stop.set()
