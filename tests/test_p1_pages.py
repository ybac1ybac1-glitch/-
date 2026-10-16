import sqlite3,sys,tempfile,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
def test_health_missing_db(monkeypatch):
 import app,data
 data.DB_PATH=tempfile.mktemp(suffix='.sqlite3'); c=app.app.test_client(); assert c.get('/data-health').status_code==200
def test_health_old_schema(monkeypatch):
 import app,data
 data.DB_PATH=tempfile.mktemp(suffix='.sqlite3'); c=sqlite3.connect(data.DB_PATH); c.execute('CREATE TABLE daily(ts_code TEXT,trade_date TEXT,close REAL)'); c.execute("INSERT INTO daily VALUES('X','20260102',1)"); c.commit(); assert app.app.test_client().get('/data-health').status_code==200
def test_resonance_page():
 import app,data
 data.DB_PATH=tempfile.mktemp(suffix='.sqlite3'); assert app.app.test_client().get('/strategy/resonance').status_code==200
