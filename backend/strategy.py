"""V3.1 candidate ranking and walk-forward evaluation; no future data in signals."""
import numpy as np, pandas as pd

def eligible(code,name=''):
 c=str(code or ''); n=str(name or '').upper()
 return not any(x in n for x in ('ST','*ST')) and (c.startswith('60') or c.startswith('00'))

def classify(hist):
 if not isinstance(hist,pd.DataFrame) or len(hist)<60: return {'priority':0,'label':'数据不足','score':None,'reason':'数据不足，无法评分'}
 d=hist.sort_values('trade_date').dropna(subset=['close','high','low','vol']).copy(); close=d.close.astype(float); vol=d.vol.astype(float)
 n=len(d); base=d.iloc[max(0,n-120):max(0,n-5)]; recent=d.tail(5); pressure=float(base.high.quantile(.9)); support=float(base.low.quantile(.1)); avg20=float(d.vol.tail(20).mean()); vr=float(recent.vol.max()/max(avg20,1e-9)); breakout=recent.high.max()>pressure*1.01 and recent.close.iloc[-1]>pressure and vr>=1.8
 rng=float((base.high.max()-base.low.min())/max(base.close.mean(),1e-9)); vol_std=float(base.close.pct_change().std()); high=float(close.tail(120).max()); high_risk=close.iloc[-1]>high*.95 and close.iloc[-1]/max(close.iloc[-21],1e-9)>1.25
 pullback=len(d)>=65 and close.iloc[-1]<close.tail(5).max()*.97 and vr<1 and close.iloc[-1]>pressure*.97
 if breakout and 60<=len(base)+5<=125 and not high_risk and avg20>0: label,priority,score='主板底部放量突破',1,92
 elif pullback: label,priority,score='低位首板后缩量回踩',2,78
 elif rng<.35 and vol_std<.05: label,priority,score='底部吸筹观察',3,62
 else: label,priority,score='候选观察',0,None
 return {'priority':priority,'label':label,'score':score,'breakout_date':str(recent.loc[recent.high==recent.high.max(),'trade_date'].iloc[-1]) if breakout else '', 'breakout_price':round(float(close.iloc[-1]),2) if breakout else None,'volume_ratio':round(vr,2),'support':round(support,2),'resistance':round(pressure,2),'invalid_condition':f'收盘跌破支撑 {support:.2f}','chasing':bool(high_risk),'reason':('最近1-5日突破平台且量比≥1.8' if breakout else label)}

def backtest(hist, horizons=(5,10,20)):
 if not isinstance(hist,pd.DataFrame) or len(hist)<80: return {'status':'数据不足，无法回测'}
 d=hist.sort_values('trade_date').reset_index(drop=True); trades=[]
 for i in range(60,len(d)-max(horizons)):
  sig=classify(d.iloc[:i+1])
  if sig['priority']!=1: continue
  rec={'date':d.loc[i,'trade_date']}
  for h in horizons: rec[f'ret_{h}d']=float(d.loc[i+h,'close']/d.loc[i,'close']-1)
  trades.append(rec)
 out={'status':'候选回测','trades':len(trades)}
 for h in horizons:
  vals=[x[f'ret_{h}d'] for x in trades]; out[f'win_rate_{h}d']=round(sum(v>0 for v in vals)/len(vals),4) if vals else None; out[f'avg_return_{h}d']=round(float(np.mean(vals)),4) if vals else None
 return out
