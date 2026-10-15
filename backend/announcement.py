import re
POS=['回购','增持','中标','重大合同','业绩增长']; NEG=['减持','处罚','问询','亏损']
def analyze(items):
    text=' '.join(str(x) for x in (items or [])); p=sum(text.count(k) for k in POS); n=sum(text.count(k) for k in NEG); score=max(-10,min(10,(p-n)*3)); return {'score':score,'sentiment':'利好' if score>0 else ('利空' if score<0 else '中性'),'items':list(items or [])[:8]}
def fetch(ts_code, pro=None):
    if pro is None: return []
    try:
        d=pro.anns(ts_code=ts_code, limit=20); col='title' if 'title' in d else d.columns[0]; return d[col].dropna().tolist()
    except Exception: return []
