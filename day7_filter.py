import pandas as pd
from pathlib import Path
from log_parser import load_records
from analysis import build_dataframe,get_failures

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"

records, bad_lines, stats = load_records(LOG_DIR)
df = build_dataframe(records)
fails = df[df["result"] == "FAIL"]
recovered = []

for _,f in fails.iterrows():
    later_pass=df[
        (df["sn"] == f["sn"])
        & (df["test"] == f["test"])
        & (df["time"] > f["time"])
        & (df["result"] == "PASS")
    ]
    if not later_pass.empty:
        recovered.append((f["sn"], f["test"]))

print(len(recovered), recovered)
print("units:", len({sn for sn, test in recovered}))

""""
cols = ["time", "sn", "station", "test", "value", "result"]
ict_fails=df[(df["station"]=="ICT") & (df["result"]=="FAIL")]
passes=df[~(df["result"]=="FAIL")]
volt=df[df["test"].isin(["Voltage_3V3", "Voltage_5V"]) & (df["result"]=="FAIL")]
late=df[(df["station"]=="ICT")
        & (df["result"]=="FAIL")
        & (df["time"]>"2026-10-20 08:10:00")]
window=df[df["time"].between("2026-10-21 08:00", "2026-10-21 08:10")]
failed=df.loc[df["result"]=="FAIL",["time", "sn", "test", "value", "station"]]
fct_units=df.loc[df["station"]=="FCT","sn"]
stopped=df[~df["sn"].isin(fct_units)]
print(stopped["sn"].unique())
print(len(stopped))
failures = get_failures(df)
failures.to_csv(REPORT_DIR / "failures.csv", index=False)
"""