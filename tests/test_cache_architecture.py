import sys, pandas as pd
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
def test_homepage_does_not_call_tushare(monkeypatch):
 import app
 monkeypatch.setattr(app,'get_stock_data',lambda:(pd.DataFrame(),'本地暂无行情缓存'))
 monkeypatch.setattr(app,'pro',None)
 c=app.app.test_client(); assert c.get('/').status_code==200
