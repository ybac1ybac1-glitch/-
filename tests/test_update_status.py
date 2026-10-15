import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
def test_status_route_is_read_only(monkeypatch):
 import app
 expected={'running':False,'requested':0,'success':0,'failed':0,'completed':0,'total':0,'last_error':'','last_update':''}
 monkeypatch.setattr(app,'status',lambda: expected)
 def forbidden(*args,**kwargs): raise AssertionError('status route started update')
 monkeypatch.setattr(app,'start_update',forbidden)
 response=app.app.test_client().get('/admin/update/status')
 assert response.status_code==200
 body=response.get_json(); assert set(expected).issubset(body)
