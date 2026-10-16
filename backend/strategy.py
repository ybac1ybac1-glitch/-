"""V3.1 candidate rules and walk-forward backtest (signals use only completed bars)."""
import numpy as np
import pandas as pd
MIN_AMOUNT_20=150000.0

def eligible(code,name=''):
 c=str(code or ''); n=str(name or '').upper()
 return not any(x in n for x in ('ST','*ST')) and (c.startswith('60') or c.startswith('00'))
def _limit_pct(code,name=''):
 c=str(code or ''); n=str(name or '').upper()
 if 'ST' in n or '*ST' in n:return .05
 if c.startswith(('30','68')):return .20
 return .10
def _prepared(hist):
 if not isinstance(hist,pd.DataFrame):return None
 req={'trade_date','open','high','low','close','vol','amount','pre_close'}
 if not req.issubset(hist.columns):return None
 d=hist.sort_values('trade_date').copy()
 for c in req-{ 'trade_date'}: d[c]=pd.to_numeric(d[c],errors='coerce')
 return d.dropna(subset=list(req))
def classify(hist):
 d=_prepared(hist)
 if d is None or len(d)<60:return {'priority':0,'label':'数据不足','score':None,'reason':'数据不足，无法评分'}
 n=len(d); base=d.iloc[max(0,n-120):n-5]; recent=d.tail(5); pressure=float(base.high.max()); support=float(base.low.min()); avg20v=float(d.vol.tail(20).mean()); avg20a=float(d.amount.tail(20).mean()); long_low=float(d.low.tail(min(250,n)).min()); pre_return=float(base.close.iloc[-1]/max(base.close.iloc[0],1e-9)-1); range_pct=float((base.high.max()-base.low.min())/max(base.close.mean(),1e-9))
 if avg20v<=0 or avg20a<MIN_AMOUNT_20:return {'priority':0,'label':'数据不足','score':None,'reason':'数据不足，成交额未达到150000千元门槛'}
 if 'turnover_rate' not in d or pd.to_numeric(d.turnover_rate,errors='coerce').tail(20).isna().any():return {'priority':0,'label':'数据不足','score':None,'reason':'数据不足，缺少换手率'}
 vr=float(recent.vol.max()/avg20v); close=float(d.close.iloc[-1]); breakout_idx=int(recent.high.values.argmax()); breakout=recent.iloc[breakout_idx]; distance_low=close/max(long_low,1e-9)-1
 structure=range_pct<.35 and pre_return<.35
 highrisk=(pre_return>.35 and range_pct>.45) or (pre_return>.25 and distance_low>1.5)
 breakout_ok=float(breakout.close)>pressure*1.01 and float(breakout.high)>pressure*1.01 and float(breakout.vol)>=avg20v*1.8 and structure and not highrisk
 code=d.ts_code.iloc[-1] if 'ts_code' in d else ''; name=d.name.iloc[-1] if 'name' in d else ''; lp=_limit_pct(code,name); pct=d.close/d.pre_close-1; limit_days=(pct.tail(60)>=lp*.98)&(d.close.tail(60)>=d.pre_close.tail(60)*(1+lp*.98)); first_board=bool(limit_days.any() and not limit_days.iloc[-5:-1].any()); pullback=bool(first_board and close<recent.close.max()*.97 and recent.vol.mean()<avg20v and close>pressure*.97 and not highrisk)
 if breakout_ok: label,priority,score='主板底部放量突破',1,92
 elif pullback: label,priority,score='低位首板后缩量回踩',2,78
 elif structure and close<pressure and float(d.close.pct_change().tail(20).std())<.05: label,priority,score='底部吸筹观察',3,62
 else: label,priority,score='候选观察',0,None
 return {'priority':priority,'label':label,'score':score,'breakout_date':str(breakout.trade_date) if breakout_ok else '','breakout_price':round(float(breakout.close),2) if breakout_ok else None,'volume_ratio':round(vr,2),'support':round(support,2),'invalid_condition':f'收盘跌破支撑 {support:.2f}','chasing':bool(highrisk),'avg_amount_20':round(avg20a,2),'reason':('突破前区间收敛，收盘突破且量比≥1.8' if breakout_ok else label)}
def backtest(hist,horizons=(5,10,20),fee=.001,slippage=.001):
 d=_prepared(hist)
 if d is None or len(d)<80:return {'status':'数据不足，无法回测','trades':[]}
 trades=[]
 for i in range(60,len(d)-max(horizons)-1):
  sig=classify(d.iloc[:i+1])
  if sig['priority']!=1:continue
  entry=float(d.open.iloc[i+1])*(1+slippage); prev=float(d.close.iloc[i]); limit_up=prev*(1+_limit_pct(d.ts_code.iloc[i],d.name.iloc[i])*.98)
  if entry>=limit_up:trades.append({'executable':False});continue
  rec={'executable':True,'entry':entry}
  for h in horizons:rec[f'ret_{h}d']=float(d.close.iloc[i+1+h]/entry-1)-2*fee
  trades.append(rec)
 out={'status':'候选回测','trades':trades}
 for h in horizons:
  vals=[x[f'ret_{h}d'] for x in trades if x.get('executable')];out[f'win_rate_{h}d']=round(sum(v>0 for v in vals)/len(vals),4) if vals else None;out[f'avg_return_{h}d']=round(float(np.mean(vals)),4) if vals else None
 return out
