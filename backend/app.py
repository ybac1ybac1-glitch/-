from flask import Flask, render_template, abort, jsonify
from data import get_stock_data,get_history,get_stock_list,pro,start_update,status,start_turnover_backfill
from stock_filter import filter_stock
from market import assess
from announcement import fetch as fetch_ann, analyze as ann_analyze
from news import fetch as fetch_news, analyze as news_analyze
from signals import migrate, list_signals, resonance
import os, sqlite3
app=Flask(__name__)

def _p1rows(strategy=None):
 c=sqlite3.connect(__import__('data').DB_PATH); migrate(c); return list_signals(c,strategy)
@app.route('/')
def index():
 df,error=get_stock_data(); market=assess(daily=df) if not df.empty else {'state':'无法判断','factor':0,'trend':0,'breadth':0,'amount_change':0,'reason':'市场环境数据缺失'}
 stocks=filter_stock(df,market,history_loader=lambda code:get_history(code)) .to_dict('records') if not df.empty else []
 records=stocks; return render_template('index.html',stocks=records,priority_stocks=[x for x in records if x.get('priority')==1],market=market,error=error,stats=status())
@app.post('/admin/update')
def update(): return jsonify(start_update())
@app.post('/admin/turnover-backfill')
def turnover_backfill(): return jsonify(start_turnover_backfill())
@app.get('/admin/update/status')
def update_status(): return jsonify(status())
@app.get('/strategy/a')
def strategy_a(): return render_template('strategy.html',title='策略 A：威科夫×操盘手2',rows=_p1rows('A_WYCKOFF_VOLUME'))
@app.get('/strategy/b')
def strategy_b(): return render_template('strategy.html',title='策略 B：野人哥独立体系',rows=_p1rows('B_YEREN'))
@app.get('/strategy/resonance')
def strategy_resonance():
 c=sqlite3.connect(__import__('data').DB_PATH); migrate(c); return render_template('strategy.html',title='双策略共振',rows=resonance(c))
@app.get('/data-health')
def data_health():
 import os
 c=sqlite3.connect(__import__('data').DB_PATH); migrate(c); row=c.execute('SELECT COUNT(*),MIN(trade_date),MAX(trade_date),SUM(turnover_rate IS NULL) FROM daily').fetchone() if os.path.exists(__import__('data').DB_PATH) else (0,None,None,0)
 return render_template('health.html',db_exists=os.path.exists(__import__('data').DB_PATH),coverage=f'{row[1]} - {row[2]}',symbols=c.execute('SELECT COUNT(DISTINCT ts_code) FROM daily').fetchone()[0] if row[0] else 0,missing_turnover=row[3])
@app.route('/stock/<ts_code>')
def stock_detail(ts_code):
 stocks=get_stock_list(); hit=stocks[stocks.ts_code.astype(str)==str(ts_code)]
 if hit.empty: abort(404)
 info=hit.iloc[0].to_dict(); frames={'daily':get_history(ts_code,'daily'),'weekly':get_history(ts_code,'weekly'),'monthly':get_history(ts_code,'monthly')}
 from wyckoff import analyze
 return render_template('detail.html',stock=info,analysis=analyze(frames['daily']),frames={k:v.tail(120).to_dict('records') for k,v in frames.items()},ann=ann_analyze(fetch_ann(ts_code,pro)),news=news_analyze(fetch_news(ts_code,pro)),error='')
if __name__=='__main__': app.run(host='127.0.0.1',port=8000,debug=False)
