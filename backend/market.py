import pandas as pd
import numpy as np

def assess(index_frames=None, daily=None):
    frames = index_frames or {}
    trends=[]
    for f in frames.values():
        if f is not None and len(f)>5 and 'close' in f:
            c=pd.to_numeric(f['close'], errors='coerce').dropna(); trends.append(float(c.iloc[-1]/c.iloc[-min(21,len(c))]-1))
    trend=float(np.mean(trends)) if trends else 0.0
    amount_change=0.0
    if daily is not None and 'amount' in daily and len(daily)>5:
        a=pd.to_numeric(daily['amount'], errors='coerce').dropna(); amount_change=float(a.tail(5).mean()/max(a.head(max(5,len(a)//2)).mean(),1e-9)-1)
    breadth=0.0
    if daily is not None and 'pct_chg' in daily:
        p=pd.to_numeric(daily['pct_chg'],errors='coerce').dropna(); breadth=float((p>0).mean()-(p<0).mean()) if len(p) else 0
    if trend>.015 and breadth>.05: state='进攻'; factor=1.0
    elif trend<-.03 or breadth<-.2: state='防守'; factor=.72
    else: state='震荡'; factor=.88
    return {'state':state,'factor':factor,'trend':round(trend*100,2),'amount_change':round(amount_change*100,2),'breadth':round(breadth*100,2),'reason':f'指数趋势{trend*100:.1f}%，涨跌家数差{breadth*100:.1f}%。'}
