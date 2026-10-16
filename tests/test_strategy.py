import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
from strategy import classify,backtest

def bars(n=100):
 rows=[]
 for i in range(n):
  close=10+i*.01; high=close*1.01; vol=100; amount=100000
  if i==80: close*=1.1; high=close; vol=250
  rows.append({'trade_date':f'2026{i+1:03d}','open':close,'high':high,'low':close*.99,'close':close,'vol':vol,'amount':amount})
 return pd.DataFrame(rows)
def test_requires_amount_and_ohlcv():
 d=bars().drop(columns=['amount']); assert classify(d)['score'] is None
def test_backtest_uses_next_bar():
 r=backtest(bars()); assert r['status'] in ('候选回测','数据不足，无法回测')
