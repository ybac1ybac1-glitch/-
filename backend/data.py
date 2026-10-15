import os
from datetime import datetime, timedelta
import pandas as pd
try:
 import tushare as ts
except Exception: ts=None
from config import TOKEN

pro=None; LAST_ERROR=""
if ts and TOKEN:
 try: ts.set_token(TOKEN); pro=ts.pro_api()
 except Exception as exc: LAST_ERROR=f"Tushare初始化失败: {exc}"
BASE=os.path.dirname(__file__)

def _fail(exc):
 global LAST_ERROR; LAST_ERROR=f"Tushare数据获取失败: {exc}"

def get_stock_list():
 p=os.path.join(BASE,'stock_list.csv')
 if os.path.exists(p):
  try: return pd.read_csv(p,dtype={'ts_code':str})
  except Exception as exc: _fail(exc)
 if pro:
  try:
   d=pro.stock_basic(exchange='',list_status='L',fields='ts_code,symbol,name,market,list_date'); d.to_csv(p,index=False,encoding='utf-8-sig'); return d
  except Exception as exc: _fail(exc)
 return pd.DataFrame(columns=['ts_code','symbol','name','market'])

def latest_trade_date(now=None):
 """Use the latest completed weekday; avoid requesting a future/intraday date."""
 now=now or datetime.now(); day=now.date()
 if now.weekday()==5: day-=timedelta(days=1)
 elif now.weekday()==6: day-=timedelta(days=2)
 elif now.hour<16: day-=timedelta(days=1)
 while day.weekday()>=5: day-=timedelta(days=1)
 return day.strftime('%Y%m%d')

def get_daily_data(trade_date=None):
 if not pro: return pd.DataFrame()
 try: return pro.daily(trade_date=trade_date or latest_trade_date())
 except Exception as exc: _fail(exc); return pd.DataFrame()

def get_history(ts_code, kind='daily', days=180):
 if not pro: return pd.DataFrame()
 try:
  end=latest_trade_date(); start=(datetime.now()-timedelta(days=days*2)).strftime('%Y%m%d')
  d=getattr(pro,kind)(ts_code=ts_code,start_date=start,end_date=end)
  if 'trade_date' in d: d['trade_date']=d['trade_date'].astype(str); d=d.sort_values('trade_date')
  return d
 except Exception as exc: _fail(exc); return pd.DataFrame()

def get_stock_data():
 stocks=get_stock_list(); daily=get_daily_data()
 if daily.empty: return pd.DataFrame(), LAST_ERROR or '暂无已完成交易日行情数据'
 return stocks.merge(daily,on='ts_code',how='inner'), ''
