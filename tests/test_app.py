import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'backend'))

def test_homepage(monkeypatch):
    import app
    import pandas as pd
    monkeypatch.setattr(app, 'get_stock_data', lambda: (pd.DataFrame(), '测试接口失败'))
    client = app.app.test_client()
    response = client.get('/')
    assert response.status_code == 200
    assert '测试接口失败'.encode() in response.data

def test_detail_without_history(monkeypatch):
    import app
    import pandas as pd
    monkeypatch.setattr(app, 'get_stock_list', lambda: pd.DataFrame([{'ts_code':'000001.SZ','name':'测试','market':'主板'}]))
    monkeypatch.setattr(app, 'get_history', lambda *args: pd.DataFrame())
    client = app.app.test_client()
    response = client.get('/stock/000001.SZ')
    assert response.status_code == 200
    assert '数据不足'.encode() in response.data
