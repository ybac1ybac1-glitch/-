import sys, threading, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))

def fresh(data):
 data._status.update(running=False,turnover_running=False,task_rejected=0,last_error='',turnover_error='')
 while data._task_lock.locked():
  try:data._task_lock.release()
  except RuntimeError:break
 data._thread=None; data._turnover_thread=None

def wait_done(t): t.join(2); assert not t.is_alive()

def test_update_duplicate_and_backfill_mutual_exclusion(monkeypatch):
 import data; fresh(data); gate=threading.Event(); started=threading.Event()
 def run(_=120): started.set(); gate.wait(2)
 monkeypatch.setattr(data,'_run_update',run); first=data.start_update(); assert started.wait(1)
 assert data.start_update()['task_rejected']>=1
 assert data.start_turnover_backfill()['task_rejected']>=2
 gate.set(); wait_done(data._thread); assert not data._task_lock.locked()

def test_backfill_blocks_update_and_releases(monkeypatch):
 import data; fresh(data); gate=threading.Event(); started=threading.Event()
 def run(): started.set(); gate.wait(2)
 monkeypatch.setattr(data,'_run_turnover_backfill',run); data.start_turnover_backfill(); assert started.wait(1)
 assert data.start_update()['task_rejected']>=1
 gate.set(); wait_done(data._turnover_thread); assert not data._task_lock.locked()

def test_thread_start_exception_releases_lock(monkeypatch):
 import data; fresh(data)
 class Broken:
  def __init__(self,*a,**k): pass
  def start(self): raise RuntimeError('start failed')
 monkeypatch.setattr(data.threading,'Thread',Broken); out=data.start_update(); assert 'start failed' in out['last_error']; assert not data._task_lock.locked()

def test_worker_exception_releases_lock(monkeypatch):
 import data; fresh(data)
 def boom(_=120): raise RuntimeError('worker failed')
 monkeypatch.setattr(data,'_run_update',boom); data.start_update();
 for _ in range(20):
  if not data._task_lock.locked(): break
  time.sleep(.01)
 assert not data._task_lock.locked(); assert data.start_turnover_backfill()['task_rejected']>=0
