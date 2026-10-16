from evidence import Evidence
STRATEGY_ID='A_WYCKOFF_VOLUME'; VERSION='A-P1-0.1'
def scan(symbol,asof,frame=None):
 missing=[] if frame is not None else ['daily_ohlcv']
 return [Evidence(STRATEGY_ID,'A.SKELETON',VERSION,'威科夫×操盘手2','P1骨架','E4',symbol,asof,state='INSUFFICIENT_DATA' if missing else 'WATCH',missing_fields=tuple(missing),evidence={})]
