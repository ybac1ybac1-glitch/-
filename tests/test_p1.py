import sqlite3,sys,tempfile,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
from evidence import Evidence
from signals import migrate,save,resonance

def test_migration_idempotent_and_signal_unique():
 c=sqlite3.connect(':memory:'); migrate(c); migrate(c); e=Evidence('A_WYCKOFF_VOLUME','A.X','v1','src','sec','E4','600000.SH','20260102',state='INSUFFICIENT_DATA',missing_fields=('daily',),evidence={}); assert save(c,e)==save(c,e); assert len(c.execute('select * from signals').fetchall())==1

def test_independent_resonance_only_intersection():
 c=sqlite3.connect(':memory:'); migrate(c); a=Evidence('A_WYCKOFF_VOLUME','A.X','v1','s','s','E4','600000.SH','20260102',evidence={}); b=Evidence('B_YEREN','B.X','v1','s','s','E2','600000.SH','20260102',evidence={}); save(c,a); save(c,b); assert resonance(c)==[('600000.SH','20260102')]
