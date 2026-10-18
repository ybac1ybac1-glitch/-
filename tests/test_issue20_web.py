import sys
from pathlib import Path
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
import app as app_module

@pytest.fixture()
def client(monkeypatch):
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()

def test_home_returns_200_without_nan(client, monkeypatch):
    rows = pd.DataFrame([{"ts_code":"001246.SZ","name":"测试","market":"主板","close":10.0}])
    monkeypatch.setattr(app_module, "get_stock_data", lambda: (rows, ""))
    monkeypatch.setattr(app_module, "assess", lambda daily: {"state":"震荡","trend":0,"breadth":0,"amount_change":0})
    filtered = pd.DataFrame([{"ts_code":"001246.SZ","name":"测试","wyckoff_stage":"数据不足","wyckoff_score":float("nan"),"announcement_score":None,"news_score":None,"wyckoff_reason":"数据不足，无法评分","priority":0}])
    monkeypatch.setattr(app_module, "filter_stock", lambda *args, **kwargs: filtered)
    monkeypatch.setattr(app_module, "status", lambda: {"requested":0,"success":0,"failed":0})
    response=client.get("/")
    assert response.status_code==200
    assert b"nan" not in response.data.lower()
    assert "数据不足".encode() in response.data

def test_stock_detail_empty_history_returns_200(client, monkeypatch):
    monkeypatch.setattr(app_module, "get_stock_list", lambda: pd.DataFrame([{"ts_code":"001246.SZ","name":"测试","market":"主板"}]))
    monkeypatch.setattr(app_module, "get_history", lambda *args, **kwargs: pd.DataFrame())
    monkeypatch.setattr(app_module, "fetch_ann", lambda *args: [])
    monkeypatch.setattr(app_module, "fetch_news", lambda *args: [])
    monkeypatch.setattr(app_module, "ann_analyze", lambda x: {"sentiment":"数据不足","score":None,"items":[]})
    monkeypatch.setattr(app_module, "news_analyze", lambda x: {"sentiment":"数据不足","score":None,"items":[]})
    response=client.get("/stock/001246.SZ")
    assert response.status_code==200
    assert "数据不足".encode() in response.data

def test_strategy_a_v4_status_does_not_scan(client, monkeypatch):
    monkeypatch.setattr(app_module, "a_web_status", lambda: {"status":"IDLE","processed":0})
    response=client.get("/strategy/a/v4/status")
    assert response.status_code==200
    assert response.get_json()["status"]=="IDLE"

def test_strategy_a_stock_data_rejects_invalid_days(client):
    for value in ("abc","", "-1", "61"):
        response=client.get("/strategy/a/v4/stock/001246.SZ/data?days="+value)
        assert response.status_code in (400,404)

def test_v4_home_reads_persisted_snapshot_without_writes(client, monkeypatch):
    monkeypatch.setattr(app_module, "a_web_status", lambda: {"status":"IDLE","processed":0})
    monkeypatch.setattr(app_module, "a_web_results", lambda *args, **kwargs: {"scan":{"asof_date":"2026-10-15","stock_count":1,"signal_count":1,"partial":True},"items":[],"total_matches":0,"total_signals":0})
    response=client.get("/strategy/a/v4")
    assert response.status_code==200
    assert "2026-10-15".encode() in response.data
    assert "部分样本".encode() in response.data

def test_v4_stock_detail_empty_cache_is_readable(client, monkeypatch):
    monkeypatch.setattr(app_module.os.path, "exists", lambda path: False)
    response=client.get("/strategy/a/v4/stock/001246.SZ")
    assert response.status_code in (200,404)
