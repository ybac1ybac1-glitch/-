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
