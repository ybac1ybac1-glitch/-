"""Read-only Windows acceptance checks for Issue #20."""
from __future__ import annotations
import argparse, os, sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

def ro(path):
    uri="file:"+quote(str(Path(path).resolve()).replace("\\","/"),safe="/:")+"?mode=ro"
    return sqlite3.connect(uri,uri=True)

def inspect_market(path):
    out={"exists":path.exists(),"size":path.stat().st_size if path.exists() else 0}
    if not out["exists"]: return out
    c=None
    try:
        c=ro(path)
        tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
        if "daily" not in tables:
            out["error"]="daily表不存在"; return out
        row=c.execute("select max(trade_date),count(*),count(distinct ts_code) from daily").fetchone()
        out.update(max_trade_date=row[0],daily_rows=row[1],stock_count=row[2])
        out["001246_rows"]=c.execute("select count(*) from daily where ts_code=?",("001246.SZ",)).fetchone()[0]
    except Exception as exc: out["error"]=str(exc)
    finally:
        if c is not None: c.close()
    return out

def inspect_results(path):
    out={"exists":path.exists(),"size":path.stat().st_size if path.exists() else 0}
    if not out["exists"]: return out
    c=None
    try:
        c=ro(path)
        tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
        if "scans" not in tables:
            out["error"]="scans表不存在"; return out
        cols={r[1] for r in c.execute("pragma table_info(scans)")}
        required={"id","asof_date","stock_count","signal_count","valid"}
        if not required<=cols:
            out["error"]="scans缺少字段:"+",".join(sorted(required-cols)); return out
        row=c.execute("select asof_date,stock_count,signal_count from scans where valid=1 order by id desc limit 1").fetchone()
        out["latest_scan"]={"asof_date":row[0],"stock_count":row[1],"signal_count":row[2]} if row else None
    except Exception as exc: out["error"]=str(exc)
    finally:
        if c is not None: c.close()
    return out

def write_report(root, report_path):
    root=Path(root); market=root/"backend"/"market_cache.sqlite3"; results=root/"backend"/"strategy_a_results.sqlite3"
    report={"time":datetime.now().isoformat(timespec="seconds"),"market":inspect_market(market),"results":inspect_results(results),"urls":["http://127.0.0.1:8000/","http://127.0.0.1:8000/stock/001246.SZ","http://127.0.0.1:8000/strategy/a/v4","http://127.0.0.1:8000/strategy/a/v4/stock/001246.SZ"]}
    p=Path(report_path); p.parent.mkdir(parents=True,exist_ok=True)
    lines=["策略 A V4 本地只读验收报告",f"时间：{report['time']}"]
    for name,data in (("行情库",report["market"]),("策略结果库",report["results"])):
        lines.append(f"{name}：存在={data.get('exists')} 大小={data.get('size')} 字节")
        for k,v in data.items():
            if k not in ("exists","size"): lines.append(f"  {k}={v}")
    lines.append("验收 URL（Flask 启动后访问）：")
    lines.extend("  "+u for u in report["urls"])
    p.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return report

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).parents[1])); ap.add_argument("--report",default=None); args=ap.parse_args()
    report=write_report(args.root,args.report or str(Path(args.root)/"work"/"acceptance_report.txt"))
    print("只读数据库检查完成，报告："+(args.report or str(Path(args.root)/"work"/"acceptance_report.txt")))
    for name,data in (("行情库",report["market"]),("策略结果库",report["results"])):
        print(f"{name}：存在={data.get('exists')}，大小={data.get('size')} 字节")
        if data.get("error"): print("  错误："+data["error"])
    if report["market"].get("exists"): print("行情最新交易日："+str(report["market"].get("max_trade_date"))+"，001246.SZ日线："+str(report["market"].get("001246_rows",0))+"条")
    if report["results"].get("latest_scan"): print("最新有效扫描："+str(report["results"]["latest_scan"]))
