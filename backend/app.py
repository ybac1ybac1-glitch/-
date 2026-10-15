from flask import Flask, render_template, abort
from data import get_stock_data,get_history,get_stock_list,pro,LAST_ERROR
from stock_filter import filter_stock
from market import assess
from announcement import fetch as fetch_ann, analyze as ann_analyze
from news import fetch as fetch_news, analyze as news_analyze
app=Flask(__name__)

def _market(df): return assess(daily=df)
@app.route('/')
def index():
 df,error=get_stock_data()
 if df.empty: return render_template('index.html',stocks=[],market=_market(df),error=error or LAST_ERROR)
 stocks=filter_stock(df,_market(df),history_loader=lambda code:get_history(code,'daily',240)).to_dict('records')
 return render_template('index.html',stocks=stocks,market=_market(df),error=error)
@app.route('/stock/<ts_code>')
def stock_detail(ts_code):
 stocks=get_stock_list(); hit=stocks[stocks.ts_code.astype(str)==str(ts_code)]
 if hit.empty: abort(404)
 info=hit.iloc[0].to_dict(); frames={k:get_history(ts_code,k,240) for k in ('daily','weekly','monthly')}
 from wyckoff import analyze
 w=analyze(frames['daily']); anns=fetch_ann(ts_code,pro); nws=fetch_news(ts_code,pro)
 return render_template('detail.html',stock=info,analysis=w,frames={k:v.tail(120).to_dict('records') for k,v in frames.items()},ann=ann_analyze(anns),news=news_analyze(nws),error=LAST_ERROR)
if __name__=='__main__': app.run(host='127.0.0.1',port=8000,debug=False)
