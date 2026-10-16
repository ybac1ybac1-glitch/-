from dataclasses import dataclass,asdict
from typing import Any
STATES={'WATCH','CANDIDATE','CONFIRMED','INVALIDATED','NEEDS_INTRADAY','INSUFFICIENT_DATA'}
@dataclass(frozen=True)
class Evidence:
 strategy_id:str; rule_id:str; rule_version:str; source:str; source_section:str; source_grade:str; symbol:str; signal_date:str; state:str='WATCH'; confirmation_date:str=''; invalidation:str=''; invalidation_date:str=''; risk_level:str='unknown'; missing_fields:tuple=(); evidence:dict=None
 def to_dict(self):
  d=asdict(self); d['missing_fields']=list(d['missing_fields']); d['evidence']=d['evidence'] or {}; return d

def validate(e):
 if e.state not in STATES: raise ValueError('invalid state')
 if not e.strategy_id or not e.rule_id or not e.signal_date: raise ValueError('missing identity')
 return e
