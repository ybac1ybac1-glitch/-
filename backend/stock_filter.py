import pandas as pd
from market import assess
from announcement import analyze as ann_analyze
from news import analyze as news_analyze
from strategy import eligible,classify

def filter_stock(df,market=None,history_loader=None):
 if not isinstance(df,pd.DataFrame) or df.empty:return pd.DataFrame()
 out=[]; market=market or assess(daily=df)
 for _,row in df.iterrows():
  if not eligible(row.get('ts_code'),row.get('name')): continue
  hist=history_loader(row.get('ts_code')) if history_loader else None; sig=classify(hist)
  ann=ann_analyze(row.get('_announcements',[])); news=news_analyze(row.get('_news',[])); r=row.to_dict(); r.update(wyckoff_stage=sig['label'],wyckoff_score=sig['score'],wyckoff_reason=sig['reason'],announcement_score=ann['score'],news_score=news['score'],priority=sig['priority'],breakout_date=sig.get('breakout_date',''),breakout_price=sig.get('breakout_price'),volume_ratio=sig.get('volume_ratio'),support=sig.get('support'),invalid_condition=sig.get('invalid_condition',''),chasing=sig.get('chasing',False))
  out.append(r)
 return pd.DataFrame(out).sort_values(['priority','wyckoff_score'],ascending=[True,False],na_position='last').head(100)
