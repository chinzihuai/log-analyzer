import pandas as pd
from pathlib import Path
from log_parser import load_records
from analysis import build_dataframe

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"

records, bad_lines, stats = load_records(LOG_DIR)
df = build_dataframe(records)
by_test=df.groupby("test",as_index=False).agg(
    total=("sn","count"),
    fails=("is_fail","sum"),
    fail_rate_pct=("is_fail","mean"),
)
g=df.groupby(["station","test"],as_index=False).agg(
    total=("sn","count"),
    fails=("is_fail","sum"),
)
d = df.groupby(["date", "station"]).agg(
    rows=("sn", "count"),
    fails=("is_fail", "sum"),
    units=("sn", "nunique"),
)
attempts = (
    df.sort_values("time")
      .groupby(["sn", "test"])
      .agg(
          first_pass=("is_pass", "first"),
          last_pass=("is_pass", "last"),
          attempts=("is_pass", "size"),
      )
)
unit_pass=df.groupby("sn")["is_pass"].all()
passed_unit=unit_pass[unit_pass].index.tolist()
print(unit_pass.sum())    
print(unit_pass.mean() * 100)   


"""
recovered = attempts[(~attempts["first_pass"]) & attempts["last_pass"]]
print(attempts)
print(len(recovered))              # 9
print(recovered.index.tolist())
print(attempts["attempts"].value_counts())
"""