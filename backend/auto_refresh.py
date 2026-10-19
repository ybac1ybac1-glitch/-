"""Opt-in automatic after-close refresh loop."""
from __future__ import annotations
import os,threading,time
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import data
from history_extension import verify_cached_date
from strategy_a_store import start as start_scan,status as scan_status,results as scan_results
_thread=None
_stop=threading.Event()
_state={"status":"IDLE","target_date":"","raw_latest":"","validated_latest":"","persisted_scan_date":"","last_error":"","last_run":"","next_retry":""}

def _retry(reason,target=""):
    nxt=(datetime.now(ZoneInfo("Asia/Shanghai"))+timedelta(minutes=5)).isoformat()
    _state.update(status="STALE",target_date=target,last_error=reason,next_retry=nxt)
    return {"status":"STALE","target_date":target,"reason":reason,"next_retry":nxt}

def _target_date(now):
    calendar=data._calendar(10) if data.pro else []
    dates=[str(x) for x in calendar if str(x)<=now.strftime("%Y%m%d")]
    return max(dates) if dates else ""

def run_once():
    now=datetime.now(ZoneInfo("Asia/Shanghai"))
    if now.hour < 15: _state.update(status="WAITING_CLOSE"); return {"status":"WAITING_CLOSE"}
    target=_target_date(now)
    if not target: return _retry("无法取得真实A股交易日历")
    _state.update(status="UPDATING",target_date=target,last_error="")
    start_result=data.start_update(max_days=10)
    time.sleep(.2)
    if data.status().get("task_rejected") and not data.status().get("running"):
        return _retry("行情更新任务未启动",target)
    deadline=time.time()+3600
    while time.time()<deadline and data.status().get("running"): time.sleep(1)
    ds=data.status()
    if ds.get("running"): return _retry("行情更新超时",target)
    if ds.get("last_error"): return _retry("行情更新失败："+str(ds["last_error"]),target)
    raw=data.latest_trade_date()
    _state["raw_latest"]=raw
    if raw!=target: return _retry(f"目标日{target}行情尚未完整发布，当前最新{raw}",target)
    integrity=verify_cached_date(data.DB_PATH,target)
    if integrity.get("status")!="TURNOVER_COMPLETE": return _retry(integrity.get("error") or "完整性未通过",target)
    _state["validated_latest"]=target
    result_path=os.path.join(data.BASE,"strategy_a_results.sqlite3")
    saved=scan_results(result_path,1,1).get("scan")
    if saved and str(saved.get("asof_date"))==target:
        _state.update(status="COMPLETED",persisted_scan_date=target,last_run=datetime.now().isoformat())
        return {"status":"COMPLETED","target_date":target}
    response=start_scan(data.DB_PATH,result_path,target)
    if isinstance(response,tuple) and len(response)>1 and response[1]!=202: return _retry("策略A扫描未启动",target)
    _state.update(status="SCANNING",last_run=datetime.now().isoformat())
    return {"status":"SCANNING","target_date":target}

def _loop(interval):
    while not _stop.wait(interval):
        try: run_once()
        except Exception as exc: _retry(str(exc),_state.get("target_date",""))

def start_scheduler():
    global _thread
    if os.getenv("AUTO_REFRESH_ENABLED","").lower() not in ("1","true","yes"): return None
    if _thread and _thread.is_alive(): return _thread
    interval=max(300,int(os.getenv("AUTO_REFRESH_INTERVAL_SECONDS","300")))
    _thread=threading.Thread(target=_loop,args=(interval,),daemon=True,name="strategy-a-auto-refresh")
    _thread.start()
    threading.Thread(target=run_once,daemon=True,name="strategy-a-initial-refresh").start()
    return _thread

def status(): return dict(_state)
def stop_scheduler(): _stop.set()
