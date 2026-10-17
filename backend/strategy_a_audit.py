"""Read-only, rule-aware audit for persisted Strategy A V4 signals."""
from __future__ import annotations
import argparse,json,math,os,sqlite3
from collections import Counter,defaultdict
RULE_REQUIREMENTS={
 "A01":("valid","support","resistance","width","slope","valid_sessions"),
 "A02":("recent_volume","base_volume","pullback","liquid"),
 "A03":("event_id","event_date","frozen_support"),
 "A04":("event_id","spring_date","transition"),
 "A05":("event_id","event_date","frozen_resistance","frozen_volume_baseline"),
 "A06":("event_id","sos_date","transition"),
 "A07":("volume_effort","price_result"),
 "A08":("price_up","volume_down"),
 "A09":("risk_conditions","independent_conditions"),
}
RULE_NOT_REQUIRED={
 "A01":("event_id","frozen_support","frozen_resistance"),
 "A02":("event_id","frozen_support","frozen_resistance"),
 "A07":("event_id","frozen_support","frozen_resistance"),
 "A08":("event_id","frozen_support","frozen_resistance"),
 "A09":("event_id","frozen_support","frozen_resistance"),
}
STATES=("CANDIDATE","CONFIRMED","INVALIDATED","WATCH","INSUFFICIENT_DATA")

def _ro(path): return sqlite3.connect("file:"+os.path.abspath(path).replace("\\","/")+"?mode=ro",uri=True)
def _json(v):
    try:return json.loads(v or "{}")
    except (TypeError,ValueError):return {}
def _finite_positive(v):
    try:return math.isfinite(float(v)) and float(v)>0
    except (TypeError,ValueError):return False

def _market_check(c,code,date):
    if not c:return "market_not_checked",None
    \n    try: row=c.execute("SELECT open,high,low,close,vol,amount FROM daily WHERE ts_code=? AND trade_date=?",(code,str(date))).fetchone()\n    except sqlite3.OperationalError: row=c.execute("SELECT open,high,low,close,vol FROM daily WHERE ts_code=? AND trade_date=?",(code,str(date))).fetchone()
    if not row:return "market_row_missing",None
    if any(v is None for v in row):return "market_field_missing",row
    o,h,l,cl,vol=map(float,row[:5]); amount=float(row[5]) if len(row)>5 else 0.0
    if not all(math.isfinite(v) for v in row):return "market_nonfinite",row
    if min(o,h,l,cl)<=0 or vol<0 or amount<0:return "market_nonpositive_or_negative",row
    if h<max(o,cl,l) or l>min(o,cl,h):return "market_ohlc_bounds_invalid",row
    return None,row

def audit(results_path,market_path=None):
    out={"status":"NO_SNAPSHOT","read_only":True,"rule_requirements":{r:{"required":list(v),"optional":list(RULE_NOT_REQUIRED.get(r,()))} for r,v in RULE_REQUIREMENTS.items()},"rules":{r:{"total":0,"states":{}} for r in RULE_REQUIREMENTS},"state_summary":{"candidate":0,"confirmed":0,"invalidated":0,"watch":0},"evidence":{"complete":0,"incomplete":0,"missing_reasons":{}},"duplicates":{"exact_records":0,"same_event_state_changes":[],"cross_rule_event_references":[],"empty_event_id_excluded":0},"mismatches":[],"untraceable":[],"suspicious":[],"data_checks":{"checked":0,"abnormal":0}}
    rc=mc=None
    try:
        if not os.path.exists(results_path):out["status"]="RESULT_DB_MISSING";return out
        rc=_ro(results_path); scan=rc.execute("SELECT id,asof_date,stock_count,signal_count,failed,partial FROM scans WHERE valid=1 ORDER BY id DESC LIMIT 1").fetchone()
        if not scan:out["status"]="NO_VALID_SNAPSHOT";return out
        sid,asof,stock_count,signal_count,failed,partial=scan; rows=rc.execute("SELECT ts_code,rule_id,state,signal_date,event_id,evidence FROM signals WHERE scan_id=? ORDER BY ts_code,signal_date,rule_id,state",(sid,)).fetchall()
        out.update(status="OK",scan={"id":sid,"asof_date":asof,"stock_count":stock_count,"signal_count":signal_count,"failed":failed,"partial":bool(partial)},actual_signal_rows=len(rows))
        distinct=len({r[0] for r in rows}); out["actual_distinct_stocks"]=distinct
        if len(rows)!=int(signal_count or 0):out["mismatches"].append({"type":"signal_count","stored":signal_count,"actual":len(rows)})
        if distinct!=int(stock_count or 0):out["mismatches"].append({"type":"stock_count","stored":stock_count,"actual":distinct})
        if market_path and os.path.exists(market_path):mc=_ro(market_path)
        exact=Counter(); event_states=defaultdict(set); cross=defaultdict(set)
        for code,rule,state,date,event_id,raw in rows:
            ev=_json(raw); meta=out["rules"].setdefault(rule,{"total":0,"states":{}});meta["total"]+=1;meta["states"][state]=meta["states"].get(state,0)+1
            if state in out["state_summary"]:out["state_summary"][state]+=1
            reasons=[]; required=RULE_REQUIREMENTS.get(rule,())
            watch=state=="WATCH"
            for field in required:
                if field=="event_id" and watch:continue
                if field not in ev or ev[field] in (None,"",[]):reasons.append("缺少:"+field)
            if state not in STATES:reasons.append("未知状态")
            if "event_id" in required and event_id and ev.get("event_id") and str(event_id)!=str(ev["event_id"]):reasons.append("event_id不一致")
            for field in ("frozen_support","frozen_resistance","frozen_volume_baseline"):
                if field in ev and ev[field] is not None and not _finite_positive(ev[field]):reasons.append(field+"非法")
            if ev.get("event_date") and date and str(ev["event_date"])>str(date):reasons.append("事件日期晚于信号日期")
            issue,bar=_market_check(mc,code,date);out["data_checks"]["checked"]+=bool(mc)
            if issue and issue!="market_not_checked":reasons.append(issue);out["data_checks"]["abnormal"]+=1 if issue!="market_row_missing" else 0
            if reasons:
                out["evidence"]["incomplete"]+=1
                for x in set(reasons):out["evidence"]["missing_reasons"][x]=out["evidence"]["missing_reasons"].get(x,0)+1
                item={"ts_code":code,"rule_id":rule,"state":state,"signal_date":date,"event_id":event_id,"reasons":sorted(set(reasons))};out["untraceable"].append(item)
                if any("非法" in x or "invalid" in x or "abnormal" in x or "nonpositive" in x for x in reasons):out["suspicious"].append(item)
            else:out["evidence"]["complete"]+=1
            key=(code,rule,date,event_id or "");exact[key]+=1
            if event_id:event_states[(code,rule,event_id)].add(state);cross[(code,date,event_id)].add(rule)
            else:out["duplicates"]["empty_event_id_excluded"]+=1
        out["duplicates"]["exact_records"]=[{"key":list(k),"count":n} for k,n in exact.items() if n>1]
        out["duplicates"]["same_event_state_changes"]=[{"key":list(k),"states":sorted(v)} for k,v in event_states.items() if len(v)>1]
        out["duplicates"]["cross_rule_event_references"]=[{"key":list(k),"rules":sorted(v)} for k,v in cross.items() if len(v)>1]
        out["logic_audit"]={"status":"UNVERIFIED","verified":[],"unverified":["A01-A09条件是否符合历史重放只能通过策略代码/逐日回放复核，持久化结果不能单独证明","冻结区间、15日等待及未来数据约束未由结果快照单独证明"],"rule_notes":{r:"字段要求按策略实现和P2.1规范映射；工程阈值仍为E4，未在本审计中调整" for r in RULE_REQUIREMENTS}}
        out["audit_conclusions"]={"verified":["持久化统计和字段审计","只读数据库连接","OHLC有限性及边界检查"],"findings":[],"evidence_insufficient":["无用户真实数据库不复现本地样本","逻辑时序仍需独立回放验证"]}
        if out["mismatches"]:out["audit_conclusions"]["findings"].append("扫描快照计数与实际信号/股票数量不一致")
        if out["untraceable"]:out["audit_conclusions"]["findings"].append("存在规则证据缺失或不可追溯信号")
        return out
    finally:
        if mc:mc.close()
        if rc:rc.close()

def write_report(report,path):
    with open(path,"w",encoding="utf-8") as f:json.dump(report,f,ensure_ascii=False,indent=2)
def main():
    p=argparse.ArgumentParser();p.add_argument("--results",required=True);p.add_argument("--market");p.add_argument("--json");a=p.parse_args();r=audit(a.results,a.market);print(json.dumps(r,ensure_ascii=False,indent=2));write_report(r,a.json) if a.json else None
if __name__=="__main__":main()
