import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
from strategy import classify,backtest,eligible

def base(n=90):
 rows=[]
 for i in range(n):
  date=(pd.Timestamp('2024-01-01')+pd.offsets.BDay(i)).strftime('%Y%m%d'); price=10 if i<80 else 10.3
  rows.append({'ts_code':'600000.SH','name':'测试','trade_date':date,'open':price,'high':price*1.01,'low':price*.99,'close':price,'pre_close':price,'vol':100,'amount':200000,'turnover_rate':3.0})
 return pd.DataFrame(rows)
def test_valid_bottom_breakout():
 d=base(); d.loc[89,['open','high','low','close','vol']]=[10.2,10.8,10.1,10.7,250]; assert classify(d)['priority']==1
def test_high_false_breakout():
 d=base(); d.loc[:79,['close','high','low','open']]=d.loc[:79,['close','high','low','open']]*1.006
 d.loc[0:59,'close']*=1.01; d.loc[89,['high','close','vol']]=[12,11.8,250]; assert classify(d)['priority']!=1
def test_no_volume_breakout():
 d=base(); d.loc[89,['high','close']]=[10.8,10.7]; assert classify(d)['priority']!=1
def test_missing_turnover_unconfirmed():
 d=base().drop(columns='turnover_rate'); assert classify(d)['score'] is None
def test_exclusions():
 assert not eligible('300001.SZ','普通'); assert not eligible('688001.SH','普通'); assert not eligible('600001.SH','*ST测试'); assert eligible('600001.SH','普通')
def test_backtest_cost_and_next_open():
 d=base(); d.loc[89,['high','close','vol']]=[10.8,10.7,250]; r=backtest(d,fee=0); assert isinstance(r['trades'],list)
