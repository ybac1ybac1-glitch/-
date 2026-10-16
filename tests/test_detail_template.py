import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
def test_detail_renders_dict_items_without_tushare(monkeypatch):
 import app, pandas as pd
 monkeypatch.setattr(app,'get_stock_list',lambda:pd.DataFrame([{'ts_code':'688835.SH','name':'测试','market':'科创板'}]))
 monkeypatch.setattr(app,'get_history',lambda *a,**k:pd.DataFrame([{'trade_date':'20260101','open':1,'high':2,'low':.8,'close':1.5,'vol':10}]))
 monkeypatch.setattr(app,'fetch_ann',lambda *a:[]); monkeypatch.setattr(app,'fetch_news',lambda *a:[])
 r=app.app.test_client().get('/stock/688835.SH'); assert r.status_code==200; assert '暂无可用公告数据'.encode() in r.data
