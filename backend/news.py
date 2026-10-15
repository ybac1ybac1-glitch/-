POS=['增长','利好','突破','支持','创新高','景气']; NEG=['下滑','风险','处罚','亏损','减持','下调']
def analyze(items):
    text=' '.join(str(x) for x in (items or [])); p=sum(text.count(k) for k in POS); n=sum(text.count(k) for k in NEG); score=max(-10,min(10,(p-n)*2)); return {'score':score,'sentiment':'正面' if score>0 else ('负面' if score<0 else '中性'),'items':list(items or [])[:8]}
def fetch(ts_code, pro=None): return []
