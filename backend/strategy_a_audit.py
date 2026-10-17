"""Read-only audit for persisted Strategy A V4 signals."""
from __future__ import annotations
import argparse, json, os, sqlite3
from collections import Counter, defaultdict
from datetime import datetime

RULES=[f"A{i:02d}" for i in range(1,10)]
STATES=("CANDIDATE","CONFIRMED","INVALIDATED")

def _ro(path):
    return sqlite3.connect("file:"+os.path.abspath(path).replace("\\","/")+"?mode=ro",uri=True)

def _safe_json(value):
    try: return json.loads(value or "{}")
    except (TypeError,ValueError): return {}

def audit(results_path, market_path=None):
    report={"status":"NO_SNAPSHOT","read_only":True,"rules":{r:{"total":0,"states":Counter()} for r in RULES},
            "state_totals":Counter(),"status_summary":{"candidate":0,"confirmed":0,"invalidated":0},"evidence":{"complete":0,"incomplete":0,"missing_reasons":Counter()},
            "duplicates":{"exact_signal_rows":0,"event_rule_dates":[],"cross_rule_events":[]},
            "untraceable":[],"suspicious":[],"examples":[],"data_checks":{"market_rows_checked":0,"abnormal_rows":0}}
    rc=None; mc=None
    try:
        if not os.path.exists(results_path):
            report["status"]="RESULT_DB_MISSING"; return _normalize(report)
        rc=_ro(results_path)
        scan=rc.execute("SELECT id,asof_date,stock_count,signal_count,failed,partial FROM scans WHERE valid=1 ORDER BY id DESC LIMIT 1").fetchone()
        if not scan:
            report["status"]="NO_VALID_SNAPSHOT"; return _normalize(report)
        sid,asof,stock_count,signal_count,failed,partial=scan
        report.update(status="OK",scan={"id":sid,"asof_date":asof,"stock_count":stock_count,"signal_count":signal_count,"failed":failed,"partial":bool(partial)})
        rows=rc.execute("SELECT ts_code,rule_id,state,signal_date,event_id,evidence FROM signals WHERE scan_id=? ORDER BY ts_code,signal_date,rule_id,state",(sid,)).fetchall()
        report["actual_signal_rows"]=len(rows)
        event_keys=Counter(); event_rules=defaultdict(set)
        if market_path and os.path.exists(market_path): mc=_ro(market_path)
        for ts_code,rule,state,signal_date,event_id,evidence_raw in rows:
            evidence=_safe_json(evidence_raw); report["rules"].setdefault(rule,{"total":0,"states":Counter()}); report["rules"][rule]["total"]+=1; report["rules"][rule]["states"][state]+=1; report["state_totals"][state]+=1
            reasons=[]
            if not rule or not state or not signal_date: reasons.append("基础字段缺失")
            if state not in STATES: reasons.append("未知状态")
            if not event_id: reasons.append("event_id缺失")
            if rule in ("A03","A04","A05","A06") and not event_id: reasons.append("事件规则缺少事件ID")
            for key in ("frozen_support","frozen_resistance"):
                if key in evidence and evidence[key] is not None:
                    try:
                        if float(evidence[key])<=0: reasons.append(key+"非法")
                    except (TypeError,ValueError): reasons.append(key+"非法")
            if evidence.get("event_date") and signal_date and str(evidence["event_date"])>str(signal_date): reasons.append("证据事件日期晚于信号日期")
            if mc and ts_code and signal_date:
                m=mc.execute("SELECT open,high,low,close,vol FROM daily WHERE ts_code=? AND trade_date=?",(ts_code,str(signal_date))).fetchone()
                report["data_checks"]["market_rows_checked"]+=1
                if not m: reasons.append("行情日线不可追溯")
                elif any(v is not None and float(v)<0 for v in m): reasons.append("行情字段异常")
                elif m[1] is not None and m[2] is not None and (float(m[2])>float(m[1])): reasons.append("high/low异常")
            if reasons:
                report["evidence"]["incomplete"]+=1
                for reason in reasons: report["evidence"]["missing_reasons"][reason]+=1
                item={"ts_code":ts_code,"rule_id":rule,"state":state,"signal_date":signal_date,"event_id":event_id,"reasons":sorted(set(reasons))}
                report["untraceable"].append(item)
                if any("异常" in x or "非法" in x for x in reasons): report["suspicious"].append(item)
            else: report["evidence"]["complete"]+=1
            key=(ts_code,rule,signal_date,event_id or "")
            event_keys[key]+=1; event_rules[(ts_code,signal_date,event_id or "")].add(rule)
            if len(report["examples"])<20: report["examples"].append({"ts_code":ts_code,"rule_id":rule,"state":state,"signal_date":signal_date,"event_id":event_id,"evidence":evidence})
        report["duplicates"]["exact_signal_rows"]=sum(n-1 for n in event_keys.values() if n>1)
        report["duplicates"]["event_rule_dates"]=[{"key":list(k),"count":n} for k,n in event_keys.items() if n>1]
        report["duplicates"]["cross_rule_events"]=[{"key":list(k),"rules":sorted(v)} for k,v in event_rules.items() if len(v)>1]
        report["status_summary"]={"candidate":report["state_totals"].get("CANDIDATE",0),"confirmed":report["state_totals"].get("CONFIRMED",0),"invalidated":report["state_totals"].get("INVALIDATED",0)}
        report["audit_conclusions"]={"verified":["统计来自当前有效持久化快照","数据库连接使用只读模式"],"findings":[],"insufficient":["未提供用户本机真实数据库时不能复现92只股票/127条信号","仅凭持久化结果不能证明完整历史重放无未来函数"]}
        if partial: report["audit_conclusions"]["findings"].append("快照标记为部分样本，不能外推全市场")
        if report["untraceable"]: report["audit_conclusions"]["findings"].append("存在不可追溯或证据不完整信号")
        return _normalize(report)
    finally:
        if mc: mc.close()
        if rc: rc.close()

def _normalize(obj):
    def conv(x):
        if isinstance(x,Counter): return {str(k):conv(v) for k,v in x.items()}
        if isinstance(x,dict): return {k:conv(v) for k,v in x.items()}
        if isinstance(x,list): return [conv(v) for v in x]
        return x
    return conv(obj)

def write_report(report,path):
    with open(path,"w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--results",required=True); p.add_argument("--market"); p.add_argument("--json")
    a=p.parse_args(); report=audit(a.results,a.market); print(json.dumps(report,ensure_ascii=False,indent=2))
    if a.json: write_report(report,a.json)
if __name__=="__main__": main()
