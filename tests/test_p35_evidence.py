import json,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
from validation import _compact
from strategy_a_audit import audit

def test_compact_preserves_structured_evidence():
    class E:
        def to_dict(self): return {}
    class R:
        def to_dict(self):
            return {"rule_id":"A01","state":"CANDIDATE","signal_date":"20261015","risk_level":"unknown","missing_fields":[],"evidence":{"valid":True,"support":10,"resistance":12,"width":.2,"slope":0,"valid_sessions":80}}
    x=_compact([R()])[0]
    assert x["evidence_version"]=="A-EVIDENCE-1" and x["evidence"]["support"]==10
    json.dumps(x)

def make_db(p,evidence):
 c=sqlite3.connect(p);c.execute("create table scans(id integer primary key,asof_date text,created_at text,stock_count integer,signal_count integer,failed integer,partial integer,valid integer)");c.execute("create table signals(scan_id integer,ts_code text,rule_id text,state text,signal_date text,event_id text,evidence text)");c.execute("insert into scans values(1,'20261015','',1,1,0,0,1)");c.execute("insert into signals values(1,'600001.SH','A01','CANDIDATE','20261015','' ,?)",(json.dumps(evidence),));c.commit();c.close()

def test_audit_new_nested_and_old_flat_evidence(tmp_path):
 p=tmp_path/"r.sqlite3";make_db(p,{"evidence_version":"A-EVIDENCE-1","evidence":{"valid":True,"support":10,"resistance":12,"width":.2,"slope":0,"valid_sessions":80}})
 r=audit(str(p));assert "strategy_fields" in r["persistence_audit"] and r["evidence"]["complete"]==1
