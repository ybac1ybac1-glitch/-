"""Read-only Windows acceptance checks for Issue #20."""
from __future__ import annotations
import argparse, os, sqlite3, sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

def ro(path):
    uri="file:"+quote(str(Path(path).resolve()).replace("\\","/"),safe="/:")+"?mode=ro"
    return sqlite3.connect(uri,uri=True)

def inspect_market(path):
    out={"exists":path.exists(),"size":path.stat().st_size if path.exists() else 0}
    if not out["exists"]: out["error"]="行情数据库不存在"; return out
    c=None
    try:
        c=ro(path); tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
        if "daily" not in tables: out["error"]="daily表不存在"; return out
        row=c.execute("select max(trade_date),count(*),count(distinct ts_code) from daily").fetchone()
        out.update(max_trade_date=row[0],daily_rows=row[1],stock_count=row[2])
        out["001246_rows"]=c.execute("select count(*) from daily where ts_code=?",("001246.SZ",)).fetchone()[0]
        latest=c.execute("select trade_date,close,vol from daily where ts_code=? order by trade_date desc limit 1",("001246.SZ",)).fetchone()
        out["001246_latest"]={"trade_date":latest[0],"close":latest[1],"vol":latest[2]} if latest else None
    except Exception as exc: out["error"]="行情库读取失败："+str(exc)
    finally:
        if c is not None: c.close()
    return out

def inspect_results(path):
    out={"exists":path.exists(),"size":path.stat().st_size if path.exists() else 0}
    if not out["exists"]: out["error"]="策略结果数据库不存在，无法验证策略结果"; return out
    c=None
    try:
        c=ro(path); tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
        if "scans" not in tables: out["error"]="结果库scans表不存在"; return out
        cols={r[1] for r in c.execute("pragma table_info(scans)")}
        required={"id","asof_date","stock_count","signal_count","valid"}
        if not required<=cols: out["error"]="scans缺少字段:"+",".join(sorted(required-cols)); return out
        row=c.execute("select asof_date,stock_count,signal_count from scans where valid=1 order by id desc limit 1").fetchone()
        out["latest_scan"]={"asof_date":row[0],"stock_count":row[1],"signal_count":row[2]} if row else None
        if row is None: out["error"]="没有有效策略 A scan，无法验证策略结果"
    except Exception as exc: out["error"]="结果库读取失败："+str(exc)
    finally:
        if c is not None: c.close()
    return out

def _check(status_code, condition, reason, body=""):
    if status_code is None: return {"status":"FAIL","http_status":None,"reason":reason}
    if status_code >= 500: return {"status":"FAIL","http_status":status_code,"reason":"网页返回服务器错误"}
    if status_code != 200: return {"status":"FAIL","http_status":status_code,"reason":reason}
    return {"status":"PASS" if condition else "UNVERIFIED","http_status":status_code,"reason":reason if condition else reason,"body_excerpt":body[:160]}

def smoke_v4(root, market, results):
    sys.path.insert(0,str(Path(root)/"backend"))
    try:
        import app as app_module
        client=app_module.app.test_client()
    except Exception as exc:
        return {"/strategy/a/v4":{"status":"FAIL","http_status":None,"reason":"无法加载Flask："+str(exc)},"/strategy/a/v4/stock/001246.SZ":{"status":"FAIL","http_status":None,"reason":"无法加载Flask："+str(exc)}}
    checks={}
    try:
        response=client.get("/strategy/a/v4"); body=response.get_data(as_text=True)
        scan=results.get("latest_scan")
        checks["/strategy/a/v4"]=_check(response.status_code, bool(scan and str(scan.get("asof_date")) in body and "策略 A" in body),"未展示有效持久化扫描日期",body)
    except Exception as exc: checks["/strategy/a/v4"]={"status":"FAIL","http_status":None,"reason":str(exc)}
    try:
        response=client.get("/strategy/a/v4/stock/001246.SZ"); body=response.get_data(as_text=True)
        rows=int(market.get("001246_rows",0) or 0)
        if rows==0:
            condition="暂无本地行情数据" in body and response.status_code==200
            checks["/strategy/a/v4/stock/001246.SZ"]=_check(response.status_code,condition,"001246.SZ无行情，页面应明确显示未验证状态",body)
            if checks["/strategy/a/v4/stock/001246.SZ"]["status"]=="PASS": checks["/strategy/a/v4/stock/001246.SZ"]["status"]="UNVERIFIED"
        else:
            latest=market.get("001246_latest") or {}
            expected=[latest.get("trade_date"), latest.get("close"), latest.get("vol")]
            values_present=all(value is not None and str(value) in body for value in expected)
            condition=response.status_code==200 and rows>0 and values_present and ("initialBars" in body or "<tbody" in body)
            checks["/strategy/a/v4/stock/001246.SZ"]=_check(response.status_code,condition,"未展示行情库中对应的真实交易日、收盘价和成交量",body)
    except Exception as exc: checks["/strategy/a/v4/stock/001246.SZ"]={"status":"FAIL","http_status":None,"reason":str(exc)}
    checks["/"]="SKIPPED_READ_ONLY: 旧V3首页可能调用可写初始化路径"
    checks["/stock/001246.SZ"]="SKIPPED_READ_ONLY: 旧V3详情可能调用可写初始化路径"
    return checks

def write_report(root, report_path, smoke=False):
    root=Path(root); market=inspect_market(root/"backend"/"market_cache.sqlite3"); results=inspect_results(root/"backend"/"strategy_a_results.sqlite3")
    smoke_result=smoke_v4(root,market,results) if smoke else {"status":"UNVERIFIED","reason":"未运行V4 smoke"}
    states=[v.get("status") for v in smoke_result.values() if isinstance(v,dict)]
    conclusion="FAIL" if market.get("error") or not market.get("exists") or "FAIL" in states else ("UNVERIFIED" if results.get("error") or "UNVERIFIED" in states else "PASS")
    report={"time":datetime.now().isoformat(timespec="seconds"),"conclusion":conclusion,"market":market,"results":results,"smoke":smoke_result,"urls":["http://127.0.0.1:8000/","http://127.0.0.1:8000/stock/001246.SZ","http://127.0.0.1:8000/strategy/a/v4","http://127.0.0.1:8000/strategy/a/v4/stock/001246.SZ"]}
    p=Path(report_path); p.parent.mkdir(parents=True,exist_ok=True)
    lines=["策略 A V4 本地只读验收报告",f"时间：{report['time']}",f"汇总结论：{conclusion}"]
    for name,data in (("行情库",market),("策略结果库",results)):
        lines.append(f"{name}：存在={data.get('exists')} 大小={data.get('size')} 字节")
        for k,v in data.items():
            if k not in ("exists","size"): lines.append(f"  {k}={v}")
    lines.append("网页逐项检查：")
    for url,value in smoke_result.items(): lines.append(f"  {url} => {value}")
    lines.append("验收 URL："); lines.extend("  "+u for u in report["urls"])
    p.write_text("
".join(lines)+"
",encoding="utf-8")
    return report

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).parents[1])); ap.add_argument("--report"); ap.add_argument("--smoke",action="store_true"); args=ap.parse_args()
    report=write_report(args.root,args.report or str(Path(args.root)/"work"/"acceptance_report.txt"),args.smoke)
    print("汇总结论："+report["conclusion"])
    if report["conclusion"]=="FAIL": raise SystemExit(1)
    if report["conclusion"]=="UNVERIFIED": raise SystemExit(2)
    raise SystemExit(0)
