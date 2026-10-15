import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
def test_function_references():
 import app, data
 assert app.start_update is data.start_update
 assert app.status is data.status
