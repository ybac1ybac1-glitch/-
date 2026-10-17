import sys,sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
import app as appmod

def test_v4_page_and_status_are_read_only(monkeypatch):
    appmod.app.config["TESTING"]=True
    monkeypatch.setattr(appmod,"a_web_results",lambda *a,**k: {"scan":None,"items":[]})
    monkeypatch.setattr(appmod,"a_web_status",lambda: {"status":"IDLE","processed":0,"total":0,"failed":0})
    c=appmod.app.test_client()
    assert c.get("/strategy/a/v4").status_code==200
    assert c.get("/strategy/a/v4/status").get_json()["status"]=="IDLE"

def test_v4_start_status_codes(monkeypatch):
    appmod.app.config["TESTING"]=True
    monkeypatch.setattr(appmod,"start_a_web",lambda *a,**k: ({"status":"RUNNING"},202))
    c=appmod.app.test_client()
    assert c.post("/strategy/a/v4/start",json={"max_stocks":3}).status_code==202
    monkeypatch.setattr(appmod,"start_a_web",lambda *a,**k: ({"status":"REJECTED"},409))
    assert c.post("/strategy/a/v4/start").status_code==409
    assert c.post("/strategy/a/v4/start",json={"max_stocks":0}).status_code==400

def test_v4_results_filters_and_paging(monkeypatch):
    appmod.app.config["TESTING"]=True
    calls=[]
    def fake(*args):
        calls.append(args)
        return {"scan":{"asof_date":"20250102"},"total_matches":3,"total_signals":3,"returned_matches":1,"page":args[1],"page_size":args[2],"items":[{"ts_code":"600001.SH","rule_id":"A03","state":"CANDIDATE"}]}
    monkeypatch.setattr(appmod,"a_web_results",fake)
    c=appmod.app.test_client()
    r=c.get("/strategy/a/v4/results?page=2&page_size=1&rule_id=A03&state=CANDIDATE&code=600")
    assert r.status_code==200 and r.get_json()["page"]==2 and calls[-1][3:]==("A03","CANDIDATE","600")

def test_v4_detail_reads_local_sqlite_only(tmp_path,monkeypatch):
    cache=tmp_path/"market_cache.sqlite3"; result=tmp_path/"strategy_a_results.sqlite3"
    c=sqlite3.connect(cache); c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,vol real,amount real)"); c.execute("insert into daily values('600001.SH','20250102',1,2,.8,1.5,100,200)"); c.commit(); c.close()
    c=sqlite3.connect(result); c.execute("create table scans(id integer primary key,asof_date text,created_at text,stock_count integer,signal_count integer,failed integer,partial integer,valid integer)"); c.execute("create table signals(scan_id integer,ts_code text,rule_id text,state text,signal_date text,event_id text,evidence text)"); c.execute("insert into scans values(1,'20250102','',1,1,0,0,1)"); c.execute("insert into signals values(1,'600001.SH','A03','CANDIDATE','20250102','e1','{}')"); c.commit(); c.close()
    monkeypatch.setattr(appmod.os.path,"dirname",lambda _:str(tmp_path))
    monkeypatch.setattr(appmod.os.path,"exists",lambda p:True)
    c=appmod.app.test_client(); r=c.get("/strategy/a/v4/stock/600001.SH")
    assert r.status_code==200 and b"600001.SH" in r.data and b"A03" in r.data

def test_v4_detail_missing_is_404(tmp_path,monkeypatch):
    monkeypatch.setattr(appmod.os.path,"dirname",lambda _:str(tmp_path))
    monkeypatch.setattr(appmod.os.path,"exists",lambda p:False)
    assert appmod.app.test_client().get("/strategy/a/v4/stock/600001.SH").status_code==404
