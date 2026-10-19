import os,runpy
from pathlib import Path
backend=Path(__file__).resolve().parent
os.chdir(backend)
os.environ["AUTO_REFRESH_ENABLED"]="1"
os.environ["AUTO_REFRESH_INTERVAL_SECONDS"]="300"
runpy.run_path(str(backend/"app.py"),run_name="__main__")
