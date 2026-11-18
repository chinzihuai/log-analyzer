import pandas as pd
from pathlib import Path
from log_parser import load_records
from analysis import build_dataframe,yield_table,write_yield_report

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

d=df.sort_values("time").copy()
d["attempts"]=d.groupby(["sn","station","test"]).cumcount()+1

n_station=d["station"].nunique()


first_ok=d[d["attempts"]==1].groupby("sn")["is_pass"].all()
last_ok=d.groupby(["sn","station","test"]).tail(1).groupby("sn")["is_pass"].all()
complete=d.groupby("sn")["station"].nunique()==n_station
retested=d.groupby("sn")["attempts"].max()>1

units=pd.DataFrame({
    "complete":complete,
    "retested":retested,
    "first_pass":first_ok&complete,
    "final_pass":last_ok&complete,
})
units["line"]=d.groupby("sn")["line"].first()
units["date"]=d.groupby("sn")["date"].first()
last = d.groupby(["sn", "station", "test"]).tail(1)           # latest attempt of each test
units["failed_at"] = last[~last["is_pass"]].groupby("sn")["station"].first()
units["status"] = "PASS_FIRST_TIME"
units.loc[units["retested"], "status"] = "PASS_AFTER_RETEST"
units.loc[~units["complete"], "status"] = "IN_PROGRESS"

failed = units["failed_at"].notna()
units.loc[failed, "status"] = "FAIL_AT_" + units.loc[failed, "failed_at"]

print(units)

total=len(units)
fpy=units["first_pass"].mean()*100
final_yield=units["final_pass"].mean()*100

print(f"Units tested     : {total}")
print(f"First-pass yield : {units['first_pass'].sum()}/{total} = {fpy:.1f}%")
print(f"Final yield      : {units['final_pass'].sum()}/{total} = {final_yield:.1f}%")
table=yield_table(units,"date")


"""
unit_pass=df.groupby("sn")["is_pass"].all()
passed_unit=unit_pass[unit_pass].index.tolist()
print(unit_pass.sum())    
print(unit_pass.mean() * 100)   

recovered = attempts[(~attempts["first_pass"]) & attempts["last_pass"]]
print(attempts)
print(len(recovered))              # 9
print(recovered.index.tolist())
print(attempts["attempts"].value_counts())
print(table)
units.to_csv(REPORT_DIR / "unit_results.csv")
write_yield_report(units, REPORT_DIR / "yield_summary.txt")
"""