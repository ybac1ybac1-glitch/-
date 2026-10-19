import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
import auto_refresh

def test_auto_refresh_does_not_scan_when_latest_is_incomplete(monkeypatch):
    calls=[]
    monkeypatch.setattr(auto_refresh.data,"start_update",lambda max_days: calls.append("update"))
    monkeypatch.setattr(auto_refresh.data,"status",lambda: {"running":False})
    monkeypatch.setattr(auto_refresh.data,"latest_trade_date",lambda:"20261016")
    monkeypatch.setattr(auto_refresh,"verify_cached_date",lambda *a,**k: {"status":"PARTIAL_MISSING","error":"turnover missing"})
    monkeypatch.setattr(auto_refresh,"start_scan",lambda *a,**k: calls.append("scan"))
    result=auto_refresh.run_once()
    assert result["status"]=="UNVERIFIED"
    assert calls==["update"]

def test_auto_refresh_starts_scan_only_after_complete(monkeypatch):
    calls=[]
    monkeypatch.setattr(auto_refresh.data,"start_update",lambda max_days: calls.append("update"))
    monkeypatch.setattr(auto_refresh.data,"status",lambda: {"running":False})
    monkeypatch.setattr(auto_refresh.data,"latest_trade_date",lambda:"20261016")
    monkeypatch.setattr(auto_refresh,"verify_cached_date",lambda *a,**k: {"status":"TURNOVER_COMPLETE","trade_date":"20261016"})
    monkeypatch.setattr(auto_refresh,"start_scan",lambda *a,**k: (calls.append("scan") or ({"status":"RUNNING"},202)))
    result=auto_refresh.run_once()
    assert result["status"]=="SCAN_STARTED"
    assert calls==["update","scan"]


def test_refresh_waits_until_after_three_pm_independent_of_browser(monkeypatch):
    class FakeDateTime:
        @classmethod
        def now(cls, tz=None):
            from datetime import datetime
            return datetime(2026,10,19,14,59,tzinfo=tz)
    monkeypatch.setattr(auto_refresh,"datetime",FakeDateTime)
    result=auto_refresh.run_once()
    assert result["status"]=="WAITING_CLOSE"
