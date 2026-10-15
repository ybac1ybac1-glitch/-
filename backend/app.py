from flask import Flask, render_template, abort
from data import get_stock_data,get_history,get_stock_list,pro
from stock_filter import filter_stock
from market import assess
from announcement import fetch as fetch_ann, analyze as ann_analyze
from news import fetch as fetch_news, analyze as news_analyze
app=Flask(__name__)

def _market(df): return assess(daily=df)
@app.route('/')
def index():
 df=get_stock_data(); m=_market(df); stocks=filter_stock(df,m).to_dict('records')
 return render_template('index.html',stocks=stocks,market=m)
@app.route('/stock/<ts_code>')
def stock_detail(ts_code):
 stocks=get_stock_list(); hit=stocks[stocks.ts_code==ts_code]
 if hit.empty: abort(404)
 info=hit.iloc[0].to_dict(); frames={k:get_history(ts_code,k,240) for k in ('daily','weekly','monthly')}
 from wyckoff import analyze
 w=analyze(frames['daily']); anns=fetch_ann(ts_code,pro); nws=fetch_news(ts_code,pro)
 return render_template('detail.html',stock=info,analysis=w,frames={k:v.tail(120).to_dict('records') for k,v in frames.items()},ann=ann_analyze(anns),news=news_analyze(nws))
if __name__=='__main__': app.run(host='0.0.0.0',port=8000,debug=True)
