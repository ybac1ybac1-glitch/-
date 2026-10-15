"""Runtime configuration. Set TUSHARE_TOKEN in the environment before starting."""
import os
TOKEN = os.getenv("TUSHARE_TOKEN", "")
