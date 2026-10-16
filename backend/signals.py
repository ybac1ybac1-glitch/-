import sqlite3,json
from evidence import validate

def migrate(c):
 c.executescript('''CREATE TABLE IF NOT EXISTS signals(id INTEGER PRIMARY KEY, strategy_id TEXT NOT NULL, rule_id TEXT NOT NULL, rule_version TEXT NOT NULL, source TEXT, source_section TEXT, source_grade TEXT, symbol TEXT NOT NULL, signal_date TEXT NOT NULL, state TEXT NOT NULL, confirmation_date TEXT, invalidation TEXT, invalidation_date TEXT, risk_level TEXT, missing_fields TEXT, evidence TEXT, UNIQUE(strategy_id,rule_id,symbol,signal_date)); CREATE TABLE IF NOT EXISTS signal_events(id INTEGER PRIMARY KEY, signal_id INTEGER NOT NULL, event_time TEXT NOT NULL, old_state TEXT, new_state TEXT NOT NULL, reason TEXT, UNIQUE(signal_id,event_time,new_state)); CREATE TABLE IF NOT EXISTS data_health(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT)'''); c.commit()
def save(c,e):
 validate(e); d=e.to_dict(); c.execute('''INSERT INTO signals(strategy_id,rule_id,rule_version,source,source_section,source_grade,symbol,signal_date,state,confirmation_date,invalidation,invalidation_date,risk_level,missing_fields,evidence) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(strategy_id,rule_id,symbol,signal_date) DO NOTHING''',(d['strategy_id'],d['rule_id'],d['rule_version'],d['source'],d['source_section'],d['source_grade'],d['symbol'],d['signal_date'],d['state'],d['confirmation_date'],d['invalidation'],d['invalidation_date'],d['risk_level'],json.dumps(d['missing_fields'],ensure_ascii=False),json.dumps(d['evidence'],ensure_ascii=False))); c.commit(); return c.execute('SELECT id FROM signals WHERE strategy_id=? AND rule_id=? AND symbol=? AND signal_date=?',(d['strategy_id'],d['rule_id'],d['symbol'],d['signal_date'])).fetchone()[0]
def list_signals(c,strategy_id=None):
 q='SELECT * FROM signals'; args=();
 if strategy_id:q+=' WHERE strategy_id=?';args=(strategy_id,)
 return c.execute(q,args).fetchall()
def resonance(c):
 return c.execute('''SELECT a.symbol,a.signal_date FROM signals a JOIN signals b ON a.symbol=b.symbol AND a.signal_date=b.signal_date WHERE a.strategy_id='A_WYCKOFF_VOLUME' AND b.strategy_id='B_YEREN' ''').fetchall()
