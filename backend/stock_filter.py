import pandas as pd
from wyckoff import analyze
from market import assess
from announcement import analyze as ann_analyze
from news import analyze as news_analyze

def filter_stock(df, market=None, history_loader=None):
 if not isinstance(df,pd.DataFrame) or df.empty: return pd.DataFrame()
 out=[]; market=market or assess(daily=df)
 for _,row in df.iterrows():
  hist=history_loader(row.get('ts_code')) if history_loader and row.get('ts_code') else None
  w=analyze(hist)
  ann=ann_analyze(row.get('_announcements',[])); news=news_analyze(row.get('_news',[]))
  r=row.to_dict(); r.update(wyckoff_stage=w['stage'],wyckoff_score=w['score'],wyckoff_reason=w['reason'],announcement_score=ann['score'],news_score=news['score'])
  if w['score'] is not None: r['wyckoff_score']=round(max(0,min(100,w['score']*.6+market['factor']*20+(ann['score']+news['score']+20)/40*20)),1)
  out.append(r)
 return pd.DataFrame(out).sort_values('wyckoff_score',ascending=False,na_position='last').head(50)
