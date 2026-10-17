import sys,sqlite3,re,shutil,subprocess,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
import app as appmod

def db(path,n=30):
    c=sqlite3.connect(path); c.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,pct_chg real,vol real,amount real)")
    for i in range(n):
        c.execute("insert into daily values(?,?,?,?,?,?,?,?,?)",("600001.SH",f"202501{i+1:02d}",10+i,12+i,9+i,11+i,.1,100+i,1000+i))
    c.commit(); c.close()

def test_professional_chart_axes_ohlc_and_ma_source():
    t=Path(__file__).parents[1].joinpath("backend/templates/strategy_a_v4_stock.html").read_text()
    for token in ("MA5","MA10","MA20","function ma(","const hi=","cross","wheel","mousedown","成交量","成交额"):
        assert token in t

def test_api_bad_days_never_500(tmp_path,monkeypatch):
    db(tmp_path/"market_cache.sqlite3"); monkeypatch.setattr(appmod.os.path,"dirname",lambda _:str(tmp_path))
    c=appmod.app.test_client()
    for v in ("abc","","-2","0","61","120.5"):
        assert c.get("/strategy/a/v4/stock/600001.SH/data?days="+v).status_code==400

def test_api_keeps_real_order_and_range(tmp_path,monkeypatch):
    db(tmp_path/"market_cache.sqlite3",30); monkeypatch.setattr(appmod.os.path,"dirname",lambda _:str(tmp_path))
    d=appmod.app.test_client().get("/strategy/a/v4/stock/600001.SH/data?days=250").get_json()
    assert len(d["bars"])==30 and d["bars"][0]["close"]==11 and d["bars"][-1]["close"]==40
    assert [x["trade_date"] for x in d["bars"]]==sorted(x["trade_date"] for x in d["bars"])

def test_professional_chart_javascript_syntax():
    t=Path(__file__).parents[1].joinpath("backend/templates/strategy_a_v4_stock.html").read_text()
    script=re.search(r"<script>(.*?)</script>",t,re.S).group(1)
    script=re.sub(r"\{\{.*?\}\}","null",script)
    node=shutil.which("node")
    if not node:return
    with tempfile.NamedTemporaryFile("w",suffix=".js",delete=False) as f:
        f.write(script); name=f.name
    try: assert subprocess.run([node,"--check",name],capture_output=True).returncode==0
    finally: Path(name).unlink(missing_ok=True)

def test_javascript_coordinate_and_ma_behavior():
    text=Path(__file__).parents[1].joinpath("backend","templates","strategy_a_v4_stock.html").read_text()
    script=re.search(r"<script>(.*?)</script>",text,re.S).group(1)
    script=re.sub(r"\{\{.*?\}\}","null",script)
    node=shutil.which("node")
    if not node:return
    js="const canvas={width:1000,height:460,getContext:()=>({clearRect(){},beginPath(){},moveTo(){},lineTo(){},stroke(){},fillRect(){},fillText(){},setLineDash(){}}),addEventListener(){},getBoundingClientRect:()=>({left:0,top:0,width:1000,height:460})};const document={getElementById:()=>canvas,querySelector:()=>({checked:true}),querySelectorAll:()=>[],};const window={addEventListener(){}};"+script+";const vals=[...Array(20)].map((_,i)=>({close:i+1}));if(window.chartMath.visibleIndex(500,{left:0,width:1000},1000,8,78,10)!==5)throw Error('index');if(window.chartMath.movingAverage(vals,19,20)!==10.5)throw Error('ma');if(window.chartMath.movingAverage(vals,5,20)!==null)throw Error('insufficient');"
    with tempfile.NamedTemporaryFile("w",suffix=".js",delete=False) as f:
        f.write(js); name=f.name
    try: assert subprocess.run([node,name],capture_output=True,text=True).returncode==0
    finally: Path(name).unlink(missing_ok=True)
