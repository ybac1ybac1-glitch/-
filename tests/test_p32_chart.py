import sys,sqlite3,shutil,subprocess,tempfile,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
import app as appmod

def make_db(path):
    c=sqlite3.connect(path); c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,pct_chg real,vol real,amount real)")
    for i in range(1,6):
        d=f"2025010{i}"; c.execute("insert into daily values(?,?,?,?,?,?,?,?,?)",("600001.SH",d,i,i+2,i-1,i+1,.5*i,100*i,1000*i))
    c.commit(); c.close()

def test_kline_json_sorted_ranges_and_values(tmp_path,monkeypatch):
    cache=tmp_path/"market_cache.sqlite3"; make_db(cache)
    monkeypatch.setattr(appmod.os.path,"dirname",lambda _:str(tmp_path))
    r=appmod.app.test_client().get("/strategy/a/v4/stock/600001.SH/data?days=60")
    assert r.status_code==200
    d=r.get_json(); assert [x["trade_date"] for x in d["bars"]]==sorted(x["trade_date"] for x in d["bars"])
    assert d["bars"][0]["open"]==1 and d["bars"][-1]["vol"]==500
    assert appmod.app.test_client().get("/strategy/a/v4/stock/600001.SH/data?days=90").status_code==400

def test_kline_missing_symbol_is_clear_404(tmp_path,monkeypatch):
    cache=tmp_path/"market_cache.sqlite3"; make_db(cache)
    monkeypatch.setattr(appmod.os.path,"dirname",lambda _:str(tmp_path))
    r=appmod.app.test_client().get("/strategy/a/v4/stock/600002.SH/data?days=60")
    assert r.status_code==404 and "error" in r.get_json()

def test_chart_template_javascript_parses():
    text=Path(__file__).parents[1].joinpath("backend","templates","strategy_a_v4_stock.html").read_text(encoding="utf-8")
    script=re.search(r"<script>(.*?)</script>",text,re.S).group(1)
    script=re.sub(r"\\{\\{.*?\\}\\}","null",script)
    node=shutil.which("node")
    if not node: return
    with tempfile.NamedTemporaryFile("w",suffix=".js",encoding="utf-8",delete=False) as f:
        f.write(script); name=f.name
    try:
        result=subprocess.run([node,"--check",name],capture_output=True,text=True)
        assert result.returncode==0, result.stderr
    finally: Path(name).unlink(missing_ok=True)
