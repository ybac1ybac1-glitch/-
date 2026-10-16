import sys,sqlite3
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
from validation import validate_cache

def make_db(path):
 c=sqlite3.connect(path); c.execute("CREATE TABLE daily(ts_code TEXT,trade_date TEXT,open REAL,high REAL,low REAL,close REAL,vol REAL,amount REAL)")
 rows=[("X","20250101",100,101,99,100,1000,100000)]*2
 c.executemany("INSERT INTO daily VALUES (?,?,?,?,?,?,?,?)",rows); c.commit(); c.close()
def test_read_only_and_batch_scan(tmp_path):
 p=str(tmp_path/"m.sqlite3"); make_db(p)
 r=validate_cache(p,"20250101",batch_size=1)
 assert r["read_only"] and r["scanned"]==1 and r["failed"]==0
 c=sqlite3.connect(p); assert c.execute("select count(*) from daily").fetchone()[0]==2; c.close()
def test_missing_schema_is_explicit(tmp_path):
 p=str(tmp_path/"m.sqlite3"); sqlite3.connect(p).execute("create table daily(ts_code text)").connection.commit()
 r=validate_cache(p); assert r["errors"] and r["scanned"]==0
def test_empty_path_is_safe(tmp_path):
 r=validate_cache(str(tmp_path/"none.sqlite3")); assert r["failed"]==0 and r["errors"]
