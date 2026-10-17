import json,sqlite3,sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
from strategy_a import scan
from validation import _compact
from strategy_a_store import _db
from strategy_a_audit import audit
import app as appmod

def frame(n=50):
    return pd.DataFrame({"trade_date":pd.date_range("2026-08-01",periods=n,freq="D").strftime("%Y%m%d"),"open":[10.0]*n,"high":[11.0]*n,"low":[9.0]*n,"close":[10.0+(i%3)*.1 for i in range(n)],"vol":[100.0]*n,"amount":[1000.0]*n})

def test_scan_compact_audit_and_detail_roundtrip(tmp_path,monkeypatch):
    ts="600001.SH"; df=frame(); evidences=scan(ts,"20260919",df)
    compact=_compact(evidences)
    assert {x["rule_id"] for x in compact}=={x.rule_id for x in evidences}
    assert all("evidence_version" in x and "evidence" in x for x in compact)
    rp=tmp_path/"strategy_a_results.sqlite3"; c=_db(str(rp)); cur=c.execute("insert into scans(asof_date,created_at,stock_count,signal_count,failed,partial,valid) values(?,?,?,?,?,?,1)",("20260919","",1,len(compact),0,0)); sid=cur.lastrowid
    for x in compact:c.execute("insert into signals values(?,?,?,?,?,?,?)",(sid,ts,x["rule_id"],x["state"],x["signal_date"],x["event_id"],json.dumps(x)))
    c.commit();c.close()
    result=audit(str(rp)); assert result["actual_signal_rows"]==len(compact)
    json.dumps(result)
    mp=tmp_path/"market_cache.sqlite3"; m=sqlite3.connect(mp);m.execute("create table daily(ts_code text,trade_date text,open real,high real,low real,close real,pct_chg real,vol real,amount real)")
    for _,r in df.iterrows():m.execute("insert into daily values(?,?,?,?,?,?,?,?,?)",(ts,r.trade_date,r.open,r.high,r.low,r.close,0,r.vol,r.amount))
    m.commit();m.close()
    monkeypatch.setattr(appmod.os.path,"dirname",lambda _:str(tmp_path))
    page=appmod.app.test_client().get("/strategy/a/v4/stock/"+ts)
    assert page.status_code==200 and b"evidence" in page.data.lower()

def test_evidence_enhancement_does_not_change_signal_identity():
    x=frame(); before=scan("600001.SH","20260919",x); after=scan("600001.SH","20260919",x)
    identity=lambda rows:[(e.rule_id,e.state,e.signal_date,e.evidence.get("event_id","")) for e in rows]
    assert identity(before)==identity(after)
