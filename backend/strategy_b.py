from evidence import Evidence
STRATEGY_ID='B_YEREN'; VERSION='B-P1-0.1'
def scan(symbol,asof,frame=None):
 missing=[] if frame is not None else ['daily_ohlcv','historical_theme','intraday']
 return [Evidence(STRATEGY_ID,'B.SKELETON',VERSION,'野人哥独立体系','P1骨架','E2',symbol,asof,state='INSUFFICIENT_DATA',missing_fields=tuple(missing),evidence={})]
