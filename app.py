"""Streamlit user interface for the factory test log analyzer.

Run:  streamlit run app.py

It uses the same modules as analyzer.py (log_parser, analysis, charts,
excel_report), so the numbers here are exactly the numbers in the reports.
"""
import contextlib
import io
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from analysis import (
    build_dataframe,
    build_unit_table,
    daily_trend,
    fail_rate_by_test,
    get_failures,
    station_yield_table,
    top_failing_tests,
    yield_table,
)
from charts import plot_daily_yield, plot_station_yield, plot_top_failing
from excel_report import write_excel_report
from log_parser import find_retests, load_records

BASE_DIR = Path(__file__).parent
DEFAULT_LOG_DIR = BASE_DIR / "logs"
BAD_LINE_WARN_RATIO = 0.05      # same 5% limit as analyzer.py

st.set_page_config(page_title="Factory Test Log Analyzer", layout="wide")


# ---------- analysis (runs only when the button is pressed) ----------

def chart_bytes(plot_fn, data) -> bytes:
    """Draw a chart with the functions from charts.py and return the PNG bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "chart.png"
        plot_fn(data, path)
        return path.read_bytes()


def excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "yield_report.xlsx"
        write_excel_report(sheets, path)
        return path.read_bytes()


def run_analysis(log_dir: Path) -> dict:
    """Load and analyse the logs. Raises FileNotFoundError if the folder is missing."""
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):          # keep the loader's messages
        records, bad_lines, stats = load_records(log_dir)

    result = {
        "log_dir": log_dir,
        "records": records,
        "bad_lines": bad_lines,
        "stats": stats,
        "messages": printed.getvalue(),
    }
    if not records:
        return result

    df = build_dataframe(records)
    units = build_unit_table(df)
    trend = daily_trend(units)
    stations = station_yield_table(df)
    top = top_failing_tests(df)
    failures = get_failures(df)

    result.update(
        df=df,
        units=units,
        done=units[units["status"] != "IN_PROGRESS"],
        trend=trend,
        stations=stations,
        top=top,
        failures=failures,
        fail_rates=fail_rate_by_test(df),
        retested_pairs=len(find_retests(records)),
        png_daily=chart_bytes(plot_daily_yield, trend),
        png_station=chart_bytes(plot_station_yield, stations),
        png_top=chart_bytes(plot_top_failing, top),
        xlsx=excel_bytes({
            "Units": units,
            "Daily trend": trend,
            "Station yield": stations,
            "Top failing tests": top,
            "Failures": failures,
        }),
    )
    return result


def pct(series: pd.Series) -> str:
    return f"{series.mean() * 100:.1f}%" if len(series) else "n/a"


# ---------- sidebar ----------

st.sidebar.title("Log analyzer")
folder_text = st.sidebar.text_input("Log folder", value=str(DEFAULT_LOG_DIR))
st.sidebar.caption("Type or paste the path of a folder that contains .log files.")

if st.sidebar.button("Run analysis", type="primary"):
    try:
        with st.spinner("Reading and analysing logs..."):
            st.session_state["result"] = run_analysis(Path(folder_text).expanduser())
    except FileNotFoundError as e:
        st.session_state.pop("result", None)
        st.error(str(e))

# ---------- main page ----------

st.title("Factory Test Log Analyzer & Yield Reporter")

res = st.session_state.get("result")
if res is None:
    st.info("Choose a log folder in the sidebar and click **Run analysis**.")
    st.stop()

st.caption(f"Folder analysed: {res['log_dir']}")

if not res["records"]:
    st.error("No valid records found in this folder.")
    st.stop()

stats = res["stats"]
units, done, df = res["units"], res["done"], res["df"]

total_lines = stats["records_parsed"] + stats["bad_lines"]
if total_lines and stats["bad_lines"] / total_lines > BAD_LINE_WARN_RATIO:
    st.warning(
        f"{stats['bad_lines']} of {total_lines} lines are bad "
        f"({stats['bad_lines'] / total_lines:.1%}). Is this the right folder?"
    )

c1, c2, c3, c4 = st.columns(4)
c1.metric("Units finished", len(done))
c2.metric("First-pass yield", pct(done["first_pass"]))
c3.metric("Final yield", pct(done["final_pass"]))
c4.metric("In progress (excluded)", len(units) - len(done))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Records", len(df))
c6.metric("Bad lines", stats["bad_lines"])
c7.metric("Duplicate files skipped", stats["duplicate_files"])
c8.metric("Duplicate records removed", stats["duplicate_records"])

tab_over, tab_station, tab_trend, tab_fail, tab_units, tab_quality, tab_down = st.tabs(
    ["Overview", "Stations", "Daily trend", "Failures", "Units", "Data quality", "Downloads"]
)

with tab_over:
    left, right = st.columns(2)
    with left:
        st.subheader("Unit status")
        st.bar_chart(units["status"].value_counts())
    with right:
        st.subheader("Yield by line")
        st.dataframe(yield_table(done, "line"))
        st.subheader("Yield by date")
        st.dataframe(yield_table(done, "date"))

with tab_station:
    st.subheader("Yield by station")
    st.image(res["png_station"], width=700)
    st.dataframe(res["stations"], hide_index=True)

with tab_trend:
    st.subheader("Daily yield")
    st.image(res["png_daily"], width=700)
    st.dataframe(res["trend"])
    st.caption("Check the Units column before reading a trend into a small difference.")

with tab_fail:
    st.subheader("Top failing tests")
    st.image(res["png_top"], width=700)
    st.dataframe(res["fail_rates"])

    st.subheader("Failed records")
    failures = res["failures"]
    f1, f2, f3 = st.columns(3)
    stations_sel = f1.multiselect("Station", sorted(failures["station"].unique()))
    tests_sel = f2.multiselect("Test", sorted(failures["test"].unique()))
    sn_text = f3.text_input("Serial number contains")
    shown = failures
    if stations_sel:
        shown = shown[shown["station"].isin(stations_sel)]
    if tests_sel:
        shown = shown[shown["test"].isin(tests_sel)]
    if sn_text:
        shown = shown[shown["sn"].str.contains(sn_text, case=False)]
    st.caption(f"{len(shown)} of {len(failures)} failed records")
    st.dataframe(shown, hide_index=True)

with tab_units:
    st.subheader("Units")
    u1, u2, u3 = st.columns(3)
    status_sel = u1.multiselect("Status", sorted(units["status"].unique()))
    line_sel = u2.multiselect("Line", sorted(units["line"].unique()))
    unit_text = u3.text_input("Serial number contains", key="unit_sn")
    shown_units = units
    if status_sel:
        shown_units = shown_units[shown_units["status"].isin(status_sel)]
    if line_sel:
        shown_units = shown_units[shown_units["line"].isin(line_sel)]
    if unit_text:
        shown_units = shown_units[shown_units.index.str.contains(unit_text, case=False)]
    st.caption(f"{len(shown_units)} of {len(units)} units")
    st.dataframe(shown_units)

with tab_quality:
    st.subheader("Loading summary")
    summary = {k: v for k, v in stats.items() if k != "files_used"}
    summary["retested_pairs"] = res["retested_pairs"]
    st.dataframe(pd.DataFrame({"value": summary}))

    st.subheader("Files used")
    st.write([str(f.relative_to(res["log_dir"])) for f in stats["files_used"]])

    st.subheader("Bad lines")
    if res["bad_lines"]:
        st.code("\n".join(res["bad_lines"][:20]))
        if len(res["bad_lines"]) > 20:
            st.caption(f"Showing the first 20 of {len(res['bad_lines'])}.")
    else:
        st.write("None.")

    if res["messages"].strip():
        with st.expander("Messages from the loader"):
            st.code(res["messages"])

with tab_down:
    st.subheader("Download")
    st.download_button(
        "Excel report (yield_report.xlsx)",
        data=res["xlsx"],
        file_name="yield_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.download_button(
        "Unit results (CSV)",
        data=units.to_csv().encode("utf-8"),
        file_name="unit_results.csv",
        mime="text/csv",
    )
    st.download_button(
        "Failures (CSV)",
        data=res["failures"].to_csv(index=False).encode("utf-8"),
        file_name="failures.csv",
        mime="text/csv",
    )