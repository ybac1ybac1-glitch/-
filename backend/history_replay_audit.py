"""P3.6 read-only daily replay and future-function audit for Strategy A."""
from __future__ import annotations
import argparse,json,math
from collections import Counter
import pandas as pd
from strategy_a import scan,replay_events

def _dates(frame):
    return sorted(pd.to_datetime(frame["trade_date"]).dt.normalize().unique())

def _identity(e):
    ev=e.evidence or {}
    return (e.rule_id,e.state,e.signal_date,ev.get("event_id",""),ev.get("event_date",""),ev.get("frozen_support"),ev.get("frozen_resistance"))

def _state_checks(events):
    issues=[]
    terminal={"INVALIDATED","EXPIRED","TEST_CANDIDATE","LPS_CANDIDATE"}
    for e in events:
        hist=e.get("transition_history",[])
        prev=None
        for h in hist:
            if h.get("from")!=prev: issues.append({"type":"transition_from_mismatch","event_id":e.get("event_id"),"transition":h})
            prev=h.get("to")
        if e.get("current_state") in terminal and len(hist)>0 and any(h.get("date","")>hist[-1].get("date","") for h in hist[hist.index(hist[-1])+1:]): issues.append({"type":"terminal_event_extended","event_id":e.get("event_id")})
        for h in hist:
            if h.get("date","")<e.get("event_date",""): issues.append({"type":"transition_before_event","event_id":e.get("event_id"),"transition":h})
    return issues

def audit_frame(symbol,frame,dates=None):
    x=frame.copy(); x["trade_date"]=pd.to_datetime(x["trade_date"]); x=x.sort_values("trade_date").drop_duplicates("trade_date")
    days=list(_dates(x)); targets=days if dates is None else [pd.to_datetime(d).normalize() for d in dates]
    report={"status":"PASS","symbol_count":1,"trading_days_checked":0,"signals_checked":0,"future_leakage_count":0,"state_transition_anomalies":0,"frozen_evidence_anomalies":0,"repeatability_anomalies":0,"cases":[],"coverage":{f"A{i:02d}":{"days":0,"signals":0} for i in range(1,10)},"unverified":[]}
    for d in targets:
        prefix=x[x.trade_date<=d]; full=x
        if prefix.empty:continue
        asof=d.strftime("%Y%m%d"); a=scan(symbol,asof,prefix); b=scan(symbol,asof,full)
        report["trading_days_checked"]+=1
        ia=[_identity(e) for e in a]; ib=[_identity(e) for e in b]; report["signals_checked"]+=len(ia)
        for e in a:
            report["coverage"].setdefault(e.rule_id,{"days":0,"signals":0});report["coverage"][e.rule_id]["days"]+=1;report["coverage"][e.rule_id]["signals"]+=1
        if ia!=ib:
            report["future_leakage_count"]+=1;report["cases"].append({"type":"future_truncation_difference","date":asof,"truncated":ia,"full_asof":ib})
        r1=scan(symbol,asof,prefix);r2=scan(symbol,asof,prefix)
        if [_identity(e) for e in r1]!=[_identity(e) for e in r2]:
            report["repeatability_anomalies"]+=1;report["cases"].append({"type":"non_repeatable_scan","date":asof})
        events=replay_events(symbol,prefix,asof); report["state_transition_anomalies"]+=len(_state_checks(events))
        for e in events:
            if any(str(h.get("date",""))>asof for h in e.get("transition_history",[])) or str(e.get("event_date",""))>asof:
                report["future_leakage_count"]+=1;report["cases"].append({"type":"future_event_transition","date":asof,"event_id":e.get("event_id")})
            if e.get("event_id") and (e.get("event_date") not in e.get("event_id","")):
                report["frozen_evidence_anomalies"]+=1;report["cases"].append({"type":"event_id_date_mismatch","date":asof,"event_id":e.get("event_id")})
    if report["future_leakage_count"] or report["state_transition_anomalies"] or report["frozen_evidence_anomalies"] or report["repeatability_anomalies"]:report["status"]="FAIL"
    report["unverified"]=["历史结果库未提供每个交易日的原始快照，无法逐项证明线上历史结果等于重放结果","停牌、涨跌停、复权等缺失数据无法由日线重放验证"]
    return report

def audit(symbol,frame,dates=None):
    return audit_frame(symbol,frame,dates)

def main():
    p=argparse.ArgumentParser();p.add_argument("--csv",required=True);p.add_argument("--symbol",required=True);p.add_argument("--json");a=p.parse_args();r=audit(a.symbol,pd.read_csv(a.csv));print(json.dumps(r,ensure_ascii=False,indent=2));json.dump(r,open(a.json,"w",encoding="utf-8"),ensure_ascii=False,indent=2) if a.json else None
if __name__=="__main__":main()
