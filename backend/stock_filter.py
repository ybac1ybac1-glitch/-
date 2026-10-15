import pandas as pd
from wyckoff import analyze
from market import assess
from announcement import analyze as ann_analyze
from news import analyze as news_analyze

def filter_stock(df, market=None):
 out=[]
 market=market or assess(daily=df)
 for _,row in df.iterrows():
  hist=row.get('_history')
  w=analyze(hist) if hist is not None else analyze(pd.DataFrame([row]))
  ann=ann_analyze(row.get('_announcements',[])); news=news_analyze(row.get('_news',[]))
  score=max(0,min(100,w['score']*.6+market['factor']*20+(ann['score']+news['score']+20)/40*20))
  r=row.to_dict(); r.update(wyckoff_stage=w['stage'],wyckoff_score=round(score,1),wyckoff_reason=w['reason'],announcement_score=ann['score'],news_score=news['score'])
  out.append(r)
 return pd.DataFrame(out).sort_values('wyckoff_score',ascending=False).head(50) if out else pd.DataFrame()
