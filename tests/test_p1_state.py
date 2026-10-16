import sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
from evidence import Evidence
from signals import migrate,save,transition

def test_state_events_and_no_restore():
 c=sqlite3.connect(':memory:');migrate(c);e=Evidence('A','A.1','v1','s','s','E4','X','20260102',state='WATCH',evidence={});sid=save(c,e);assert transition(c,sid,'CANDIDATE','ok','20260102')=='CANDIDATE';assert transition(c,sid,'INVALIDATED','bad','20260103')=='INVALIDATED'
 try: transition(c,sid,'CONFIRMED','bad','20260104');assert False
 except ValueError: pass
 assert c.execute('select count(*) from signal_events').fetchone()[0]==2
def test_transition_confirmation_date_and_invalidation_fields():
 c=sqlite3.connect(':memory:'); migrate(c); e=Evidence('A','A.2','v1','s','s','E4','X','20260102',state='CANDIDATE',evidence={}); sid=save(c,e)
 try: transition(c,sid,'CONFIRMED','ok','20260103')
 except ValueError: pass
 assert c.execute('select state from signals where id=?',(sid,)).fetchone()[0]=='CANDIDATE'
 assert transition(c,sid,'CONFIRMED','ok','20260103','20260103')=='CONFIRMED'
 assert transition(c,sid,'INVALIDATED','bad','20260104')=='INVALIDATED'
 assert c.execute('select invalidation_date,invalidation from signals where id=?',(sid,)).fetchone()==('20260104','bad')
