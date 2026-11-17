import pandas as pd
from pathlib import Path
from log_parser import load_records

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"


def build_dataframe(records: list[dict]) -> pd.DataFrame:
    """Turn parsed records into a DataFrame with proper types."""
    df = pd.DataFrame(records)
    df["time"] = pd.to_datetime(df["time"])
    df["date"] = df["time"].dt.date
    df["is_pass"] = df["result"] == "PASS"
    df["is_fail"] = ~df["is_pass"]
    return df

def get_failures(df: pd.DataFrame) -> pd.DataFrame:
    """All failed test records, oldest first."""
    cols = ["time", "sn", "station", "test", "value", "result", "file"]
    return df.loc[df["result"] == "FAIL", cols].sort_values("time").reset_index(drop=True)

def fail_rate_by_test(df:pd.DataFrame)->pd.DataFrame:
    out=df.groupby("test").agg(
        total=("sn","count"),
        fails=("is_fail","sum"),
        fail_rate_pct=("is_fail","mean"),
    )
    out["fail_rate_pct"]=(out["fail_rate_pct"]*100).round(1)
    return out.sort_values("fail_rate_pct",ascending=False)

def value_stats_by_test(df:pd.DataFrame)->pd.DataFrame:
    return df.groupby("test")["value"].agg(["count", "mean", "std", "min", "max"]).round(2)

def recovered_after_retest(df: pd.DataFrame) -> pd.DataFrame:
    attempts=(
        df.sort_values("time")
        .groupby(["sn","test"])
        .agg(first_pass=("is_pass","first"),
             last_pass=("is_pass","last"),
             attempts=("is_pass","size"))
    )
    return attempts[(~attempts["first_pass"])& attempts["last_pass"]]

def main() -> None:
    try:
        records, bad_lines, stats = load_records(LOG_DIR)
    except FileNotFoundError as e:
        print("ERROR:", e)
        return
    if not records:
        print("No records found.")
        return

    df = build_dataframe(records)

    REPORT_DIR.mkdir(exist_ok=True)
    df.to_csv(REPORT_DIR / "records.csv", index=False)

    print(df.shape)
    print(df["date"].value_counts().sort_index())
    print(df["value"].describe())
    print(df["is_pass"].mean())
    fail_rate_by_test(df).to_csv(REPORT_DIR / "fail_rate_by_test.csv")
    value_stats_by_test(df).to_csv(REPORT_DIR / "value_stats_by_test.csv")


if __name__ == "__main__":
    main()