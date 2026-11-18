import pandas as pd
from pathlib import Path
from log_parser import load_records
from analysis import build_dataframe,station_yield

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"

records, bad_lines, stats = load_records(LOG_DIR)
df = build_dataframe(records)

d=df.sort_values("date").copy()
d["attempts"]=d.groupby(["sn","station","test"]).cumcount()+1

result=station_yield(d,"ict")
print(result)
