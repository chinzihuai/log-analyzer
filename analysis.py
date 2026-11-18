"""pandas analysis: failures, per-test statistics, per-unit and per-station yield.

This module only holds functions. The entry point is analyzer.py.
"""
from pathlib import Path

import pandas as pd


# ---------- building the tables ----------

def build_dataframe(records: list[dict]) -> pd.DataFrame:
    """Turn parsed records into a DataFrame with proper types."""
    df = pd.DataFrame(records)
    df["time"] = pd.to_datetime(df["time"])
    df["date"] = df["time"].dt.date
    df["is_pass"] = df["result"] == "PASS"
    df["is_fail"] = ~df["is_pass"]
    # production line from the file name, e.g. line1_2026-10-20.log -> line1
    df["line"] = df["file"].str.extract(r"^(line\d+)", expand=False).fillna("unknown")
    return df


def add_attempts(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by time and number each test's attempts (1 = first try)."""
    d = df.sort_values("time").copy()
    d["attempt"] = d.groupby(["sn", "station", "test"]).cumcount() + 1
    return d


# ---------- record-level analysis ----------

def get_failures(df: pd.DataFrame) -> pd.DataFrame:
    """All failed test records, oldest first."""
    cols = ["time", "sn", "station", "test", "value", "result", "file"]
    return df.loc[df["result"] == "FAIL", cols].sort_values("time").reset_index(drop=True)


def fail_rate_by_test(df: pd.DataFrame) -> pd.DataFrame:
    out = df.groupby("test").agg(
        total=("sn", "count"),
        fails=("is_fail", "sum"),
        fail_rate_pct=("is_fail", "mean"),
    )
    out["fail_rate_pct"] = (out["fail_rate_pct"] * 100).round(1)
    return out.sort_values("fail_rate_pct", ascending=False)


def value_stats_by_test(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("test")["value"].agg(["count", "mean", "std", "min", "max"]).round(2)


def recovered_after_retest(df: pd.DataFrame) -> pd.DataFrame:
    """(unit, test) pairs whose first attempt failed and whose last attempt passed."""
    attempts = (
        df.sort_values("time")
          .groupby(["sn", "test"])
          .agg(first_pass=("is_pass", "first"),
               last_pass=("is_pass", "last"),
               attempts=("is_pass", "size"))
    )
    return attempts[(~attempts["first_pass"]) & attempts["last_pass"]]


# ---------- unit-level yield ----------

def build_unit_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per unit: flags, line, date and a status label.

    Rules:
      first_pass : every test passed on attempt 1 and the unit visited all stations
      final_pass : every test's latest attempt passed and the unit visited all stations
    Status (later rules overwrite earlier ones, failure wins):
      FAIL_AT_<station>  the latest result of some test failed there
      IN_PROGRESS        no failure, but a station is missing (excluded from yield)
      PASS_AFTER_RETEST  passed, but needed a retest
      PASS_FIRST_TIME    passed with no retest
    """
    d = add_attempts(df)
    n_stations = d["station"].nunique()

    first_ok = d[d["attempt"] == 1].groupby("sn")["is_pass"].all()
    last = d.groupby(["sn", "station", "test"]).tail(1)      # latest attempt of each test
    last_ok = last.groupby("sn")["is_pass"].all()
    complete = d.groupby("sn")["station"].nunique() == n_stations
    retested = d.groupby("sn")["attempt"].max() > 1

    units = pd.DataFrame({
        "complete": complete,
        "retested": retested,
        "first_pass": first_ok & complete,
        "final_pass": last_ok & complete,
    })
    units["line"] = d.groupby("sn")["line"].first()
    units["date"] = d.groupby("sn")["date"].first()
    units["failed_at"] = last[~last["is_pass"]].groupby("sn")["station"].first()

    units["status"] = "PASS_FIRST_TIME"
    units.loc[units["retested"], "status"] = "PASS_AFTER_RETEST"
    units.loc[~units["complete"], "status"] = "IN_PROGRESS"
    failed = units["failed_at"].notna()
    units.loc[failed, "status"] = "FAIL_AT_" + units.loc[failed, "failed_at"]
    return units


def yield_table(units: pd.DataFrame, by: str) -> pd.DataFrame:
    """First-pass and final yield grouped by a column (e.g. 'line' or 'date')."""
    t = units.groupby(by).agg(
        units=("first_pass", "size"),
        first_pass=("first_pass", "sum"),
        final_pass=("final_pass", "sum"),
    )
    t["first_pass_yield_pct"] = (t["first_pass"] / t["units"] * 100).round(1)
    t["final_yield_pct"] = (t["final_pass"] / t["units"] * 100).round(1)
    return t


def write_yield_report(units: pd.DataFrame, path: Path) -> None:
    """Write the yield summary. Units still in progress are excluded and counted."""
    done = units[units["status"] != "IN_PROGRESS"]
    total = len(done)
    in_progress = len(units) - total

    if total == 0:
        path.write_text("No finished units to report.\n", encoding="utf-8")
        return

    lines = [
        f"Units finished      : {total}",
        f"In progress (excl.) : {in_progress}",
        f"First-pass yield    : {done['first_pass'].sum()}/{total} = {done['first_pass'].mean() * 100:.1f}%",
        f"Final yield         : {done['final_pass'].sum()}/{total} = {done['final_pass'].mean() * 100:.1f}%",
        "",
        "Status counts:",
        units["status"].value_counts().to_string(),
        "",
        "Yield by line:",
        yield_table(done, "line").to_string(),
        "",
        "Yield by date:",
        yield_table(done, "date").to_string(),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------- station-level yield ----------

def station_yield(d: pd.DataFrame, station: str) -> dict:
    """Yield of one station. d must come from add_attempts()."""
    s = d[d["station"] == station]
    n_tests = s["test"].nunique()
    complete = s.groupby("sn")["test"].nunique() == n_tests   # unit has every test of this station

    first_ok = s[s["attempt"] == 1].groupby("sn")["is_pass"].all()
    last_ok = s.groupby(["sn", "test"]).tail(1).groupby("sn")["is_pass"].all()

    tested = s["sn"].nunique()                                # units that entered this station
    first_pass = int((first_ok & complete).sum())
    final_pass = int((last_ok & complete).sum())

    return {
        "station": station,
        "tested": tested,
        "first_pass": first_pass,
        "first_pass_yield_pct": round(first_pass / tested * 100, 1),
        "final_pass": final_pass,
        "final_yield_pct": round(final_pass / tested * 100, 1),
    }


def station_yield_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per station, in the order the units visit them."""
    d = add_attempts(df)
    return pd.DataFrame([station_yield(d, st) for st in d["station"].unique()])