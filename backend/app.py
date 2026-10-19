from flask import Flask, render_template, abort, jsonify
from data import get_stock_data,get_history,get_stock_list,pro,start_update,status,start_turnover_backfill
from stock_filter import filter_stock
from market import assess
from announcement import fetch as fetch_ann, analyze as ann_analyze
from news import fetch as fetch_news, analyze as news_analyze
from signals import migrate, list_signals, resonance
from history_extension import start as start_history_extend
from validation import validate_cache,start as start_validation,status as validation_status,get_results
from strategy_a_store import start as start_a_web,status as a_web_status,results as a_web_results\nfrom auto_refresh import start_scheduler
import os, sqlite3, json, math
import pandas as pd
app=Flask(__name__)\nstart_scheduler()

def _clean_value(value):
    try:
        if value is None:
            return None
        if hasattr(value, "item"):
            value = value.item()
        if isinstance(value, (float, int)) and not math.isfinite(float(value)):
            return None
        missing = pd.isna(value)
        if isinstance(missing, bool) and missing:
            return None
    except Exception:
        return None
    return value

def _clean_rows(rows):
    return [{k: _clean_value(v) for k, v in row.items()} for row in rows]

def _p1rows(strategy=None):
    c=sqlite3.connect(__import__('data').DB_PATH)
    try: migrate(c); return list_signals(c,strategy)
    finally: c.close()
@app.route('/')
def index():
    df,error=get_stock_data(); market=assess(daily=df) if not df.empty else {'state':'无法判断','factor':0,'trend':0,'breadth':0,'amount_change':0,'reason':'市场环境数据缺失'}
    stocks=_clean_rows(filter_stock(df,market,history_loader=lambda code:get_history(code)).to_dict('records')) if not df.empty else []
    return render_template('index.html',stocks=stocks,priority_stocks=[x for x in stocks if x.get('priority')==1],market=market,error=error,stats=status())
@app.post('/admin/history-extend')
def history_extend(): return jsonify(start_history_extend(360))
@app.post('/admin/update')
def update(): return jsonify(start_update())
@app.post('/admin/turnover-backfill')
def turnover_backfill(): return jsonify(start_turnover_backfill())
@app.get('/admin/update/status')
def update_status(): return jsonify(status())
@app.get('/strategy/a/validate')
def strategy_a_validate_status(): return jsonify(validation_status())
@app.post('/strategy/a/validate')
def strategy_a_validate_start():
    from flask import request
    import data
    q=request.get_json(silent=True) or request.form or request.args
    try: batch=int(q.get('batch_size',100)); max_results=int(q.get('max_results',200))
    except Exception: return jsonify({'error':'batch_size/max_results必须为整数'}),400
    if not 1<=batch<=1000 or not 1<=max_results<=10000:return jsonify({'error':'batch_size必须1-1000，max_results必须1-10000'}),400
    result, code = start_validation(data.DB_PATH,q.get('asof_date'),batch,max_results)
    return jsonify(result),code
@app.get('/strategy/a/validate/results')
def strategy_a_validate_results():
    from flask import request
    try: page=int(request.args.get('page',1)); size=int(request.args.get('page_size',100))
    except Exception:return jsonify({'error':'page/page_size必须为整数'}),400
    result=get_results(page,size)
    if result.get('errors'): return jsonify(result),400
    return jsonify(result)
@app.get('/strategy/a')
def strategy_a(): return render_template('strategy.html',title='策略 A：威科夫×操盘手2',rows=_p1rows('A_WYCKOFF_VOLUME'))
@app.get('/strategy/b')
def strategy_b(): return render_template('strategy.html',title='策略 B：野人哥独立体系',rows=_p1rows('B_YEREN'))
@app.get('/strategy/resonance')
def strategy_resonance():
    c=sqlite3.connect(__import__('data').DB_PATH)
    try: migrate(c); rows=resonance(c)
    finally: c.close()
    return render_template('strategy.html',title='双策略共振',rows=rows)
@app.get('/data-health')
def data_health():
    import os
    path=__import__('data').DB_PATH; exists=os.path.exists(path); row=(0,None,None,0); symbols=0; per_stock=(0,0); missing={}
    if exists:
        c=sqlite3.connect(path)
        try:
            tables={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'daily' in tables:
                cols={r[1] for r in c.execute('PRAGMA table_info(daily)')}; row=c.execute('SELECT COUNT(DISTINCT trade_date),MIN(trade_date),MAX(trade_date),0 FROM daily').fetchone(); symbols=c.execute('SELECT COUNT(DISTINCT ts_code) FROM daily').fetchone()[0]; per_stock=c.execute('SELECT COALESCE(MIN(n),0),COALESCE(MAX(n),0) FROM (SELECT ts_code,COUNT(DISTINCT trade_date) n FROM daily GROUP BY ts_code)').fetchone()
                for col in ('open','high','low','close','vol','amount','turnover_rate'):
                    missing[col]='数据不足' if col not in cols else c.execute(f'SELECT COUNT(*) FROM daily WHERE {col} IS NULL').fetchone()[0]
                if 'turnover_rate' in cols: row=(row[0],row[1],row[2],c.execute('SELECT COUNT(*) FROM daily WHERE turnover_rate IS NULL').fetchone()[0])
        finally: c.close()
    coverage=f'{row[1]} - {row[2]}' if row[0] else '数据不足'
    return render_template('health.html',db_exists=exists,coverage=coverage,symbols=symbols,missing_turnover=row[3] if row[0] else '数据不足',missing=missing,requirements={'80':row[0]>=80,'120':row[0]>=120,'240':row[0]>=240},global_days=row[0],min_stock_days=per_stock[0],max_stock_days=per_stock[1])
@app.route('/stock/<ts_code>')
def stock_detail(ts_code):
    stocks=get_stock_list(); hit=stocks[stocks.ts_code.astype(str)==str(ts_code)]
    if hit.empty: abort(404)
    info={k:_clean_value(v) for k,v in hit.iloc[0].to_dict().items()}
    frames={}; errors=[]
    for kind in ('daily','weekly','monthly'):
        try: frames[kind]=get_history(ts_code,kind)
        except Exception as exc:
            frames[kind]=__import__('pandas').DataFrame(); errors.append(f'{kind}: {exc}')
    try:
        from wyckoff import analyze
        analysis=analyze(frames['daily'])
    except Exception as exc:
        analysis={'stage':'数据不足','score':None,'reason':'无法生成分析：'+str(exc)}
    try: ann=ann_analyze(fetch_ann(ts_code,pro))
    except Exception: ann={'sentiment':'数据不足','score':None,'items':[]}
    try: news=news_analyze(fetch_news(ts_code,pro))
    except Exception: news={'sentiment':'数据不足','score':None,'items':[]}
    return render_template('detail.html',stock=info,analysis=analysis,
        frames={k:_clean_rows(v.tail(120).to_dict('records')) for k,v in frames.items()},
        ann=ann,news=news,error='；'.join(errors) if errors else '')

def _v4_readonly_meta():
    cache=os.path.join(os.path.dirname(__file__),'market_cache.sqlite3')
    out={'raw_latest':'未知','validated_latest':'未知'}
    if not os.path.exists(cache): return out
    conn=None
    try:
        conn=sqlite3.connect('file:'+quote(os.path.abspath(cache).replace('\\','/'),safe='/:')+'?mode=ro',uri=True)
        tables={r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
        if 'daily' in tables: out['raw_latest']=conn.execute('select max(trade_date) from daily').fetchone()[0] or '未知'
        if 'history_date_tasks' in tables:
            row=conn.execute("select max(trade_date) from history_date_tasks where status=? and ohlcv_state=? and turnover_state=?",('TURNOVER_COMPLETE','OHLCV_COMPLETE','TURNOVER_COMPLETE')).fetchone()
            out['validated_latest']=row[0] or '未知'
    except Exception: pass
    finally:
        if conn is not None: conn.close()
    return out

@app.get('/strategy/a/v4')
def strategy_a_v4():
    path=os.path.join(os.path.dirname(__file__),'strategy_a_results.sqlite3')
    result=a_web_results(path)
    meta=_v4_readonly_meta()
    return render_template('strategy_a_v4.html',status=a_web_status(),result=result,meta=meta)
@app.post('/strategy/a/v4/start')
def strategy_a_v4_start():
    from flask import request
    import data
    q=request.get_json(silent=True) or request.form or request.args
    raw=q.get('max_stocks')
    try: max_stocks=int(raw) if raw not in (None,'') else None
    except Exception:return jsonify({'error':'max_stocks必须为正整数'}),400
    if max_stocks is not None and max_stocks<1:return jsonify({'error':'max_stocks必须为正整数'}),400
    result,code=start_a_web(data.DB_PATH,os.path.join(os.path.dirname(__file__),'strategy_a_results.sqlite3'),q.get('asof_date'),max_stocks=max_stocks)
    return jsonify(result),code
@app.get('/strategy/a/v4/status')
def strategy_a_v4_status(): return jsonify(a_web_status())

@app.get('/strategy/a/v4/stock/<ts_code>')
def strategy_a_v4_stock(ts_code):
    cache_path=os.path.join(os.path.dirname(__file__),'market_cache.sqlite3')
    result_path=os.path.join(os.path.dirname(__file__),'strategy_a_results.sqlite3')
    def ro(path):
        return sqlite3.connect('file:'+os.path.abspath(path).replace('\\','/')+'?mode=ro', uri=True)
    bars=[]; signals=[]
    if os.path.exists(cache_path):
        c=ro(cache_path)
        try:
            cols={r[1] for r in c.execute('PRAGMA table_info(daily)')}
            required=('trade_date','open','high','low','close','vol','amount')
            if not set(required).issubset(cols): raise sqlite3.Error('daily表缺少OHLCV字段')
            pct='pct_chg' if 'pct_chg' in cols else 'NULL AS pct_chg'
            rows=c.execute(f'SELECT ts_code,trade_date,open,high,low,close,{pct},vol,amount FROM daily WHERE ts_code=? ORDER BY trade_date DESC LIMIT 250',(ts_code,)).fetchall()
            bars=[dict(zip(('ts_code','trade_date','open','high','low','close','pct_chg','vol','amount'),x)) for x in reversed(rows)]
        except sqlite3.Error: bars=[]
        finally: c.close()
    if os.path.exists(result_path):
        c=ro(result_path)
        try:
            row=c.execute('SELECT id FROM scans WHERE valid=1 ORDER BY id DESC LIMIT 1').fetchone()
            if row:
                for x in c.execute('SELECT rule_id,state,signal_date,event_id,evidence FROM signals WHERE scan_id=? AND ts_code=? ORDER BY signal_date,rule_id',(row[0],ts_code)):
                    signals.append({'rule_id':x[0],'state':x[1],'signal_date':x[2],'event_id':x[3],'evidence':json.loads(x[4])})
        except (sqlite3.Error,ValueError): signals=[]
        finally: c.close()
    if not bars and not signals and not os.path.exists(cache_path) and not os.path.exists(result_path):
        abort(404)
    return render_template('strategy_a_v4_stock.html',ts_code=ts_code,bars=bars[-120:],ma_context=bars[-139:-120],signals=signals,empty_message="暂无本地行情数据" if not bars else "",source="本地 market_cache.sqlite3（只读）")

@app.get('/strategy/a/v4/stock/<ts_code>/data')
def strategy_a_v4_stock_data(ts_code):
    from flask import request
    raw=request.args.get('days','120')
    try: days=int(raw)
    except (TypeError,ValueError): return jsonify({'error':'days必须为60、120或250'}),400
    if days not in (60,120,250): return jsonify({'error':'days必须为60、120或250'}),400
    path=os.path.join(os.path.dirname(__file__),'market_cache.sqlite3')
    if not os.path.exists(path): return jsonify({'error':'本地行情数据库不存在'}),404
    c=sqlite3.connect('file:'+os.path.abspath(path).replace('\\','/')+'?mode=ro',uri=True)
    try:
        rows=c.execute('SELECT trade_date,open,high,low,close,pct_chg,vol,amount FROM daily WHERE ts_code=? ORDER BY trade_date DESC LIMIT ?',(ts_code,days+19)).fetchall()
        if not rows: return jsonify({'error':'没有该股票的日线数据'}),404
        keys=('trade_date','open','high','low','close','pct_chg','vol','amount'); allbars=[dict(zip(keys,x)) for x in reversed(rows)]; context=allbars[:-days]; visible=allbars[-days:]
        return jsonify({'ts_code':ts_code,'days':days,'context':context,'bars':visible})
    finally: c.close()

@app.get('/strategy/a/v4/results')
def strategy_a_v4_results():
    from flask import request
    try:
        page=int(request.args.get('page',1)); size=int(request.args.get('page_size',100))
        if page<1 or size<1 or size>1000:return jsonify({'error':'分页参数无效'}),400
        return jsonify(a_web_results(os.path.join(os.path.dirname(__file__),'strategy_a_results.sqlite3'),page,size,request.args.get('rule_id'),request.args.get('state'),request.args.get('code')))
    except ValueError:return jsonify({'error':'分页参数无效'}),400
if __name__=='__main__':
    app.run(host='127.0.0.1',port=8000,debug=False)
