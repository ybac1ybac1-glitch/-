import os
from datetime import datetime, timedelta
import pandas as pd
try:
 import tushare as ts
except Exception: ts=None
from config import TOKEN

if ts:
 try: ts.set_token(os.getenv('TUSHARE_TOKEN', TOKEN)); pro=ts.pro_api()
 except Exception: pro=None
else: pro=None
BASE=os.path.dirname(__file__)

def get_stock_list():
 p=os.path.join(BASE,'stock_list.csv')
 if os.path.exists(p): return pd.read_csv(p,dtype={'ts_code':str})
 if pro:
  try:
   d=pro.stock_basic(exchange='',list_status='L',fields='ts_code,symbol,name,market,list_date'); d.to_csv(p,index=False,encoding='utf-8-sig'); return d
  except Exception: pass
 return pd.DataFrame(columns=['ts_code','symbol','name','market'])

def get_daily_data(trade_date=None):
 if pro:
  try: return pro.daily(trade_date=trade_date or datetime.now().strftime('%Y%m%d'))
  except Exception: pass
 return pd.DataFrame()

def get_history(ts_code, kind='daily', days=180):
 if pro:
  try:
   end=datetime.now().strftime('%Y%m%d'); start=(datetime.now()-timedelta(days=days*2)).strftime('%Y%m%d')
   d=getattr(pro,kind)(ts_code=ts_code,start_date=start,end_date=end); return d.sort_values('trade_date')
  except Exception: pass
 return pd.DataFrame()

def get_stock_data():
 stocks=get_stock_list(); daily=get_daily_data()
 if daily.empty: return stocks.assign(pct_chg=0.0,vol=0.0,close=0.0,announcement_score=0,news_score=0)
 return stocks.merge(daily,on='ts_code',how='inner')
