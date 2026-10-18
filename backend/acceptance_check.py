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
        c=ro(path)
        tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
        if "daily" not in tables: out["error"]="daily表不存在"; return out
        row=c.execute("select max(trade_date),count(*),count(distinct ts_code) from daily").fetchone()
        out.update(max_trade_date=row[0],daily_rows=row[1],stock_count=row[2])
        out["001246_rows"]=c.execute("select count(*) from daily where ts_code=?",("001246.SZ",)).fetchone()[0]
    except Exception as exc: out["error"]="行情库读取失败："+str(exc)
    finally:
        if c is not None: c.close()
    return out

def inspect_results(path):
    out={"exists":path.exists(),"size":path.stat().st_size if path.exists() else 0}
    if not out["exists"]: out["error"]="策略结果数据库不存在，无法验证策略结果"; return out
    c=None
    try:
        c=ro(path)
        tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
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

def smoke_v4(root):
    """Only exercise V4 read-only routes; V3 routes are explicitly skipped."""
    sys.path.insert(0,str(Path(root)/"backend"))
    import app as app_module
    client=app_module.app.test_client()
    checks={}
    for url in ("/strategy/a/v4","/strategy/a/v4/stock/001246.SZ"):
        try:
            response=client.get(url)
            body=response.get_data(as_text=True)
            checks[url]={"status_code":response.status_code,"has_scan_date":"2026-" in body or "复盘日期" in body,"has_ohlcv":any(x in body for x in ("开","成交量","交易日")),"empty_message":"暂无本地行情数据" in body}
        except Exception as exc:
            checks[url]={"status_code":None,"error":str(exc)}
    checks["/"]="SKIPPED_READ_ONLY: 旧V3首页会调用可写数据初始化路径"
    checks["/stock/001246.SZ"]="SKIPPED_READ_ONLY: 旧V3详情会调用可写数据初始化路径"
    return checks

def write_report(root, report_path, smoke=False):
    root=Path(root); market=root/"backend"/"market_cache.sqlite3"; results=root/"backend"/"strategy_a_results.sqlite3"
    report={"time":datetime.now().isoformat(timespec="seconds"),"market":inspect_market(market),"results":inspect_results(results),"smoke":smoke_v4(root) if smoke else {"status":"NOT_RUN"},"urls":["http://127.0.0.1:8000/","http://127.0.0.1:8000/stock/001246.SZ","http://127.0.0.1:8000/strategy/a/v4","http://127.0.0.1:8000/strategy/a/v4/stock/001246.SZ"]}
    p=Path(report_path); p.parent.mkdir(parents=True,exist_ok=True)
    lines=["策略 A V4 本地只读验收报告",f"时间：{report['time']}"]
    for name,data in (("行情库",report["market"]),("策略结果库",report["results"])):
        lines.append(f"{name}：存在={data.get('exists')} 大小={data.get('size')} 字节")
        for k,v in data.items():
            if k not in ("exists","size"): lines.append(f"  {k}={v}")
    lines.append("网页检查：")
    for url,value in report["smoke"].items(): lines.append(f"  {url} => {value}")
    lines.append("验收 URL："); lines.extend("  "+u for u in report["urls"])
    p.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return report

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).parents[1])); ap.add_argument("--report"); ap.add_argument("--smoke",action="store_true"); args=ap.parse_args()
    report=write_report(args.root,args.report or str(Path(args.root)/"work"/"acceptance_report.txt"),args.smoke)
    print("验收报告："+(args.report or str(Path(args.root)/"work"/"acceptance_report.txt")))
    for name,data in (("行情库",report["market"]),("策略结果库",report["results"])):
        print(f"{name}：存在={data.get('exists')}，大小={data.get('size')} 字节")
        if data.get("error"): print("  "+data["error"])
    if report["market"].get("exists"): print("行情最新交易日："+str(report["market"].get("max_trade_date"))+"，001246.SZ日线："+str(report["market"].get("001246_rows",0))+"条")
    if report["results"].get("latest_scan"): print("最新有效扫描："+str(report["results"]["latest_scan"]))
    if args.smoke: print("V4只读页面检查："+str(report["smoke"]))
    market_ok=report["market"].get("exists") and not report["market"].get("error") and report["market"].get("max_trade_date")
    result_ok=report["results"].get("latest_scan") is not None and not report["results"].get("error")
    raise SystemExit(0 if market_ok and result_ok else (1 if not market_ok else 2))
