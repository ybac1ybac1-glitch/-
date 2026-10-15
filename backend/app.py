from flask import Flask, render_template, abort, jsonify
from data import get_stock_data,get_history,get_stock_list,pro,start_update,status
from stock_filter import filter_stock
from market import assess
from announcement import fetch as fetch_ann, analyze as ann_analyze
from news import fetch as fetch_news, analyze as news_analyze
app=Flask(__name__)
@app.route('/')
def index():
 df,error=get_stock_data(); market=assess(daily=df) if not df.empty else {'state':'无法判断','factor':0,'trend':0,'breadth':0,'amount_change':0,'reason':'市场环境数据缺失'}
 stocks=filter_stock(df,market,history_loader=lambda code:get_history(code)) .to_dict('records') if not df.empty else []
 return render_template('index.html',stocks=stocks,market=market,error=error,stats=status())
@app.post('/admin/update')
def update(): return jsonify(start_update())
@app.get('/admin/update/status')
def update_status(): return jsonify(status())
@app.route('/stock/<ts_code>')
def stock_detail(ts_code):
 stocks=get_stock_list(); hit=stocks[stocks.ts_code.astype(str)==str(ts_code)]
 if hit.empty: abort(404)
 info=hit.iloc[0].to_dict(); frames={'daily':get_history(ts_code),'weekly':get_history(ts_code),'monthly':get_history(ts_code)}
 from wyckoff import analyze
 return render_template('detail.html',stock=info,analysis=analyze(frames['daily']),frames={k:v.tail(120).to_dict('records') for k,v in frames.items()},ann=ann_analyze(fetch_ann(ts_code,pro)),news=news_analyze(fetch_news(ts_code,pro)),error='')
if __name__=='__main__': app.run(host='127.0.0.1',port=8000,debug=False)
