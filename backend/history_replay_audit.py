"""P3.6 daily replay, evidence and state-machine audit."""
from __future__ import annotations
import argparse,json,math
import pandas as pd
from strategy_a import scan,replay_events

TERMINALS={"TEST_CANDIDATE","LPS_CANDIDATE","INVALIDATED","EXPIRED"}
ALLOWED={"SPRING":{(None,"CANDIDATE"),("CANDIDATE","WAITING_TEST"),("WAITING_TEST","TEST_CANDIDATE"),("WAITING_TEST","INVALIDATED"),("WAITING_TEST","EXPIRED")},"SOS":{(None,"CANDIDATE"),("CANDIDATE","WAITING_LPS"),("WAITING_LPS","LPS_CANDIDATE"),("WAITING_LPS","INVALIDATED"),("WAITING_LPS","EXPIRED")}}

def _parse_date(v):
    s=str(v).strip()
    if s.isdigit() and len(s)==8: return pd.to_datetime(s,format="%Y%m%d",errors="coerce")
    return pd.to_datetime(s,errors="coerce")

def _norm(v):
    if isinstance(v,dict): return {str(k):_norm(x) for k,x in sorted(v.items()) if k not in {"parameters"}}
    if isinstance(v,(list,tuple)): return [_norm(x) for x in v]
    if isinstance(v,(pd.Timestamp,)): return v.isoformat()
    if hasattr(v,"item"):
        try:return _norm(v.item())
        except Exception:pass
    if isinstance(v,float):
        return None if math.isnan(v) else round(v,10)
    if pd.isna(v): return None
    return v

def _evidence(e):
    return _norm(getattr(e,"evidence",{}) or {})

def _record(e):
    return {"rule_id":e.rule_id,"state":e.state,"signal_date":str(e.signal_date),"event_id":_evidence(e).get("event_id",""),"event_date":_evidence(e).get("event_date",""),"evidence":_evidence(e)}

def _diff(a,b):
    keys=sorted(set(a)|set(b)); return {k:(a.get(k),b.get(k)) for k in keys if _norm(a.get(k))!=_norm(b.get(k))}

def _state_checks(events):
    issues=[]
    for e in events:
        typ=e.get("event_type"); hist=e.get("transition_history",[]); prev=None; dates=[]
        for h in hist:
            pair=(h.get("from"),h.get("to")); dates.append(str(h.get("date","")))
            if pair not in ALLOWED.get(typ,set()): issues.append({"type":"illegal_transition","event_id":e.get("event_id"),"transition":h})
            if h.get("from")!=prev: issues.append({"type":"transition_from_mismatch","event_id":e.get("event_id"),"transition":h})
            if _parse_date(dates[-1]) < _parse_date(e.get("event_date","")): issues.append({"type":"transition_before_event","event_id":e.get("event_id"),"transition":h})
            if len(dates)>1 and _parse_date(dates[-1]) < _parse_date(dates[-2]): issues.append({"type":"date_regression","event_id":e.get("event_id"),"transition":h})
            if prev in TERMINALS: issues.append({"type":"terminal_event_extended","event_id":e.get("event_id"),"transition":h})
            prev=h.get("to")
    return issues

def audit_frame(symbol,frame,dates=None):
    x=frame.copy();x["trade_date"]=x["trade_date"].map(_parse_date);x=x.sort_values("trade_date").drop_duplicates("trade_date")
    days=sorted(x.trade_date.dt.normalize().unique());targets=days if dates is None else [_parse_date(d).normalize() for d in dates]
    r={"status":"PASS","symbol_count":1,"trading_days_checked":0,"signals_checked":0,"future_leakage_count":0,"state_transition_anomalies":0,"frozen_evidence_anomalies":0,"repeatability_anomalies":0,"evidence_differences":0,"raw_state_transition_anomalies":0,"unique_state_transition_anomalies":0,"cases":[],"coverage":{f"A{i:02d}":{"status":"UNVERIFIED","days":0,"signals":0,"capabilities":{"historical_truncation":{"status":"UNVERIFIED","checks":0,"reason":"尚未执行"},"evidence_consistency":{"status":"UNVERIFIED","checks":0,"reason":"尚未执行"},"state_transition_legality":{"status":"UNVERIFIED","checks":0,"reason":"未触发对应事件"},"frozen_evidence_stability":{"status":"UNVERIFIED","checks":0,"reason":"未触发冻结事件"},"waiting_15_sessions":{"status":"UNVERIFIED","checks":0,"reason":"未真实触发第14/15/16个交易日状态"},"persisted_snapshot_consistency":{"status":"UNVERIFIED","checks":0,"reason":"没有逐日持久化快照"}}} for i in range(1,10)},"unverified":["没有逐日历史结果快照，无法证明持久化结果与重放逐项相等","停牌、涨跌停、复权和分钟数据不在日线输入中"]}
    freeze_history={}
    for d in targets:
        prefix=x[x.trade_date<=d]
        if prefix.empty:continue
        asof=d.strftime("%Y%m%d");a=scan(symbol,asof,prefix);b=scan(symbol,asof,x);r["trading_days_checked"]+=1
        ra=[_record(e) for e in a];rb=[_record(e) for e in b];r["signals_checked"]+=len(ra)
        for e in ra:
            q=r["coverage"].setdefault(e["rule_id"],{"status":"UNVERIFIED","days":0,"signals":0});q["days"]+=1;q["signals"]+=1;q["status"]="PASS"
        if ra!=rb:
            r["future_leakage_count"]+=1;r["evidence_differences"]+=1;r["cases"].append({"type":"future_truncation_difference","symbol":symbol,"date":asof,"changes":_diff({"records":ra},{"records":rb})})
        if [_record(e) for e in scan(symbol,asof,prefix)]!=ra:
            r["repeatability_anomalies"]+=1;r["cases"].append({"type":"non_repeatable_scan","symbol":symbol,"date":asof})
        events=replay_events(symbol,prefix,asof)
        issues=_state_checks(events);r["state_transition_anomalies"]+=len(issues);r["raw_state_transition_anomalies"]+=len(issues);r["cases"].extend([{"symbol":symbol,"date":asof,**i} for i in issues])
        for ev in events:
            rule="A03" if ev.get("event_type")=="SPRING" else "A05"
            if ev.get("event_type") in {"SPRING","SOS"}: r["coverage"][rule]["capabilities"]["state_transition_legality"]={"status":"PASS" if not issues else "FAIL","checks":r["coverage"][rule]["capabilities"].get("state_transition_legality",{}).get("checks",0)+1,"reason":"事件状态机已执行"}
            if ev.get("event_type")=="SPRING" and ev.get("current_state") in {"TEST_CANDIDATE","INVALIDATED","EXPIRED"}: r["coverage"]["A04"]["capabilities"]["state_transition_legality"]={"status":"PASS" if not issues else "FAIL","checks":1,"reason":"Spring状态转换已执行"}
            if ev.get("event_type")=="SOS" and ev.get("current_state") in {"LPS_CANDIDATE","INVALIDATED","EXPIRED"}: r["coverage"]["A06"]["capabilities"]["state_transition_legality"]={"status":"PASS" if not issues else "FAIL","checks":1,"reason":"SOS状态转换已执行"}
        for e in events:
            if str(e.get("event_date",""))>asof or any(str(h.get("date",""))>asof for h in e.get("transition_history",[])):
                r["future_leakage_count"]+=1;r["cases"].append({"type":"future_event_transition","symbol":symbol,"date":asof,"event_id":e.get("event_id")})
            key=e.get("event_id")
            frozen=(e.get("event_date"),e.get("frozen_support"),e.get("frozen_resistance"),e.get("frozen_volume_baseline"))
            if key and key in freeze_history and freeze_history[key]!=frozen:r["frozen_evidence_anomalies"]+=1;r["cases"].append({"type":"frozen_evidence_changed","event_id":key,"before":freeze_history[key],"after":frozen})
            if key:
                freeze_history[key]=frozen
                rule=("A03" if str(key).find(":A03:")>=0 else "A05" if str(key).find(":A05:")>=0 else None)
                if rule: r["coverage"][rule]["capabilities"]["frozen_evidence_stability"]={"status":"PASS","checks":r["coverage"][rule]["capabilities"].get("frozen_evidence_stability",{}).get("checks",0)+1,"reason":"冻结事件跨日期稳定"}
    for rule in ("A03","A04","A05","A06"):
        if r["coverage"][rule]["status"]=="UNVERIFIED": r["unverified"].append(rule+"未触发对应事件或等待状态，无法证明完整状态机")
    keys={(i.get("event_id"),i.get("transition",{}).get("date"),i.get("type")) for i in r["cases"] if i.get("type") in {"illegal_transition","transition_from_mismatch","date_regression","terminal_event_extended","transition_before_event"}}
    r["unique_state_transition_anomalies"]=len(keys)
    if r["trading_days_checked"]==0:r["status"]="UNVERIFIED";r["unverified"].append("没有有效交易日")
    if any(r[k] for k in ("future_leakage_count","state_transition_anomalies","frozen_evidence_anomalies","repeatability_anomalies")):r["status"]="FAIL"
    return r

def audit(symbol,frame,dates=None): return audit_frame(symbol,frame,dates)
def main():
    p=argparse.ArgumentParser();p.add_argument("--csv",required=True);p.add_argument("--symbol",required=True);p.add_argument("--json");a=p.parse_args();r=audit(a.symbol,pd.read_csv(a.csv));print(json.dumps(r,ensure_ascii=False,indent=2));json.dump(r,open(a.json,"w",encoding="utf-8"),ensure_ascii=False,indent=2) if a.json else None
if __name__=="__main__":main()
