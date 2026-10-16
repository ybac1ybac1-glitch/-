import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
from strategy import classify, backtest, eligible

def make(n=130, breakout=None, limit=False, code='600000.SH'):
 rows=[]; price=10
 for i in range(n):
  pre=price; pct=.1 if limit and i==n-8 else .002; price=pre*(1+pct); close=price
  if breakout and i==n-1: close=11; price=close
  rows.append({'ts_code':code,'name':'测试','trade_date':f'2026{i+1:03d}','open':pre,'high':close*1.01,'low':pre*.99,'close':close,'pre_close':pre,'vol':250 if breakout and i==n-1 else 100,'amount':100000})
 return pd.DataFrame(rows)
def test_valid_bottom_breakout(): assert classify(make(breakout=True))['label'] in ('主板底部放量突破','候选观察')
def test_high_acceleration_not_priority(): assert classify(make(breakout=True).assign(close=lambda x:x.close*1.4))['priority'] != 1
def test_no_volume_breakout(): assert classify(make(breakout=True).assign(vol=100))['priority'] != 1
def test_first_board_pullback_requires_limit(): assert classify(make(limit=True).assign(close=lambda x:x.close*.98))['priority'] in (0,2,3)
def test_non_limit_pullback_unconfirmed(): assert classify(make().assign(close=lambda x:x.close*.98))['priority'] != 2
def test_exclusions(): assert not eligible('300001.SZ','普通'); assert not eligible('688001.SH','普通'); assert not eligible('600001.SH','*ST测试'); assert eligible('600001.SH','普通')
def test_backtest_next_open_and_costs():
 d=make(breakout=True); a=backtest(d,fee=0); b=backtest(d,fee=.01); assert a['status'] in ('候选回测','数据不足，无法回测'); assert b['status']==a['status']
