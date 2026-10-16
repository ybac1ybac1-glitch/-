from flask import Flask, render_template, abort, jsonify
from data import get_stock_data,get_history,get_stock_list,pro,start_update,status,start_turnover_backfill
from stock_filter import filter_stock
from market import assess
from announcement import fetch as fetch_ann, analyze as ann_analyze
from news import fetch as fetch_news, analyze as news_analyze
from signals import migrate, list_signals, resonance
from history_extension import start as start_history_extend
from validation import validate_cache,start as start_validation,status as validation_status,get_results
from strategy_a_store import start as start_a_web,status as a_web_status,results as a_web_results
import os, sqlite3
app=Flask(__name__)

def _p1rows(strategy=None):
 c=sqlite3.connect(__import__('data').DB_PATH)
 try:
  migrate(c); return list_signals(c,strategy)
 finally: c.close()
@app.route('/')
def index():
 df,error=get_stock_data(); market=assess(daily=df) if not df.empty else {'state':'无法判断','factor':0,'trend':0,'breadth':0,'amount_change':0,'reason':'市场环境数据缺失'}
 stocks=filter_stock(df,market,history_loader=lambda code:get_history(code)) .to_dict('records') if not df.empty else []
 records=stocks; return render_template('index.html',stocks=records,priority_stocks=[x for x in records if x.get('priority')==1],market=market,error=error,stats=status())
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
 result, code = start(data.DB_PATH,q.get('asof_date'),batch,max_results)
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
 try:
  migrate(c); rows=resonance(c)
 finally: c.close()
 return render_template('strategy.html',title='双策略共振',rows=rows)
@app.get('/data-health')
def data_health():
 import os
 path=__import__('data').DB_PATH; exists=os.path.exists(path); row=(0,None,None,0); symbols=0; per_stock=(0,0); missing={}
 if exists:
  c=sqlite3.connect(path); tables={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  if 'daily' in tables:
   cols={r[1] for r in c.execute('PRAGMA table_info(daily)')}; row=c.execute('SELECT COUNT(DISTINCT trade_date),MIN(trade_date),MAX(trade_date),0 FROM daily').fetchone(); symbols=c.execute('SELECT COUNT(DISTINCT ts_code) FROM daily').fetchone()[0]; per_stock=c.execute('SELECT COALESCE(MIN(n),0),COALESCE(MAX(n),0) FROM (SELECT ts_code,COUNT(DISTINCT trade_date) n FROM daily GROUP BY ts_code)').fetchone()
   for col in ('open','high','low','close','vol','amount','turnover_rate'):
    if col not in cols: missing[col]='数据不足'
    else: missing[col]=c.execute(f'SELECT COUNT(*) FROM daily WHERE {col} IS NULL').fetchone()[0]
   if 'turnover_rate' in cols: row=(row[0],row[1],row[2],c.execute('SELECT COUNT(*) FROM daily WHERE turnover_rate IS NULL').fetchone()[0])
  c.close()
 coverage=f'{row[1]} - {row[2]}' if row[0] else '数据不足'
 return render_template('health.html',db_exists=exists,coverage=coverage,symbols=symbols,missing_turnover=row[3] if row[0] else '数据不足',missing=missing,requirements={'80':row[0]>=80,'120':row[0]>=120,'240':row[0]>=240},global_days=row[0],min_stock_days=per_stock[0],max_stock_days=per_stock[1])
@app.route('/stock/<ts_code>')
def stock_detail(ts_code):
 stocks=get_stock_list(); hit=stocks[stocks.ts_code.astype(str)==str(ts_code)]
 if hit.empty: abort(404)
 info=hit.iloc[0].to_dict(); frames={'daily':get_history(ts_code,'daily'),'weekly':get_history(ts_code,'weekly'),'monthly':get_history(ts_code,'monthly')}
 from wyckoff import analyze
 return render_template('detail.html',stock=info,analysis=analyze(frames['daily']),frames={k:v.tail(120).to_dict('records') for k,v in frames.items()},ann=ann_analyze(fetch_ann(ts_code,pro)),news=news_analyze(fetch_news(ts_code,pro)),error='')
if __name__=='__main__': app.run(host='127.0.0.1',port=8000,debug=False)

@app.get('/strategy/a/v4')
def strategy_a_v4():
 return render_template('strategy_a_v4.html',status=a_web_status(),result=a_web_results(os.path.join(os.path.dirname(__file__),'strategy_a_results.sqlite3')))
@app.post('/strategy/a/v4/start')
def strategy_a_v4_start():
 from flask import request
 import data
 q=request.get_json(silent=True) or request.form or request.args
 try: max_stocks=int(q.get('max_stocks')) if q.get('max_stocks') else None
 except Exception:return jsonify({'error':'max_stocks无效'}),400
 return jsonify(start_a_web(data.DB_PATH,os.path.join(os.path.dirname(__file__),'strategy_a_results.sqlite3'),q.get('asof_date'),max_stocks=max_stocks)[0]),202
@app.get('/strategy/a/v4/status')
def strategy_a_v4_status(): return jsonify(a_web_status())
@app.get('/strategy/a/v4/results')
def strategy_a_v4_results():
 from flask import request
 try:return jsonify(a_web_results(os.path.join(os.path.dirname(__file__),'strategy_a_results.sqlite3'),int(request.args.get('page',1)),int(request.args.get('page_size',100)),request.args.get('rule_id'),request.args.get('state')))
 except ValueError:return jsonify({'error':'分页参数无效'}),400
