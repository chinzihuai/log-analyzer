"""Factory test log analyzer: entry point.

Run:  python analyzer.py
Reads logs/ and writes all reports to reports/.
"""
from datetime import datetime
from pathlib import Path
import argparse
import sys

from analysis import (
    build_dataframe,
    build_unit_table,
    daily_trend,
    fail_rate_by_test,
    get_failures,
    station_yield_table,
    top_failing_tests,
    value_stats_by_test,
    write_yield_report,
)
from log_parser import SERIAL_RE, find_retests, load_records
from charts import plot_daily_yield, plot_station_yield, plot_top_failing

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"
IMAGE_CHART_DIR=REPORT_DIR/ "charts"

# ---------- reports about the files and the data quality ----------

def count_lines(path: Path) -> int:
    with path.open(encoding="utf-8", errors="replace") as fh:
        return sum(1 for _ in fh)


def write_file_report(log_files: list[Path], log_dir: Path, report_dir: Path) -> None:
    """Write file_report.txt and add a line to run_history.txt."""
    report_lines: list[str] = []
    total_lines = 0
    for f in log_files:
        st = f.stat()
        n = count_lines(f)
        total_lines += n
        modified = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        report_lines.append(
            f"{f.relative_to(log_dir)} | {n} lines | {st.st_size / 1024:.1f} KB | modified {modified}"
        )
    report_lines.append(f"TOTAL | {len(log_files)} files | {total_lines} lines")
    (report_dir / "file_report.txt").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with (report_dir / "run_history.txt").open("a", encoding="utf-8") as fh:
        fh.write(f"{timestamp} | {len(log_files)} files | {total_lines} lines\n")


def write_data_quality_report(stats: dict, bad_lines: list[str], retest_pairs: int, path: Path) -> None:
    """Summarize what was skipped, removed or suspicious while loading the logs."""
    lines = [f"{key:20}: {value}" for key, value in stats.items() if key != "files_used"]
    lines.append(f"{'retested_pairs':20}: {retest_pairs}")
    lines.append("")
    lines.append("First bad lines:")
    lines.extend(f"  {line}" for line in bad_lines[:5])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def mask_file(src: Path, dst: Path) -> None:
    """Practice exercise (not part of the pipeline): copy src to dst with serials masked."""
    with src.open(encoding="utf-8", errors="replace") as fin, \
         dst.open("w", encoding="utf-8") as fout:
        for line in fin:
            fout.write(SERIAL_RE.sub(r"\1***", line))

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Factory test log analyzer and yield reporter."
    )
    parser.add_argument("log_dir", nargs="?", type=Path, default=LOG_DIR,
                        help="folder containing .log files (default: ./logs)")
    parser.add_argument("-o", "--report-dir", type=Path, default=REPORT_DIR,
                        help="folder for the reports (default: ./reports)")
    parser.add_argument("--max-bad-ratio", type=float, default=0.05,
                        help="warn when more than this share of lines are bad (default: 0.05)")
    parser.add_argument("--strict", action="store_true",
                        help="stop instead of only warning when there are too many bad lines")
    args = parser.parse_args(argv)
    if not 0 <= args.max_bad_ratio <= 1:
        parser.error("--max-bad-ratio must be between 0 and 1")
    return args

def write_reports(df, units, records, bad_lines, stats, log_dir, report_dir) -> None:
    """Write every report file into report_dir."""
    report_dir.mkdir(parents=True, exist_ok=True)
    chart_dir=report_dir/ "charts"
    chart_dir.mkdir(parents=True,exist_ok=True)

    write_file_report(stats["files_used"], log_dir, report_dir)
    write_data_quality_report(stats, bad_lines, len(find_retests(records)),
                              report_dir / "data_quality.txt")

    df.to_csv(report_dir / "records.csv", index=False)
    get_failures(df).to_csv(report_dir / "failures.csv", index=False)
    fail_rate_by_test(df).to_csv(report_dir / "fail_rate_by_test.csv")
    value_stats_by_test(df).to_csv(report_dir / "value_stats_by_test.csv")

    units.to_csv(report_dir / "unit_results.csv")
    station_yield_table(df).to_csv(report_dir / "station_yield.csv", index=False)
    write_yield_report(units, report_dir / "yield_summary.txt")
             
    top_failing_tests(df).to_csv(report_dir / "top_failing_tests.csv")
                  
    daily_trend(units).to_csv(report_dir / "daily_trend.csv") 

    plot_daily_yield(daily_trend(units), chart_dir / "daily_yield.png")
    plot_station_yield(station_yield_table(df), chart_dir / "station_yield.png")
    plot_top_failing(top_failing_tests(df),chart_dir/ "top_failing_tests.png")
# ---------- main ----------

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # 1. load
    try:
        records, bad_lines, stats = load_records(args.log_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    if not records:
        print(f"ERROR: no valid records found in {args.log_dir}", file=sys.stderr)
        return 1

    # 2. too many bad lines?
    total_lines = stats["records_parsed"] + stats["bad_lines"]
    bad_ratio = stats["bad_lines"] / total_lines
    if bad_ratio > args.max_bad_ratio:
        print(f"WARNING: {stats['bad_lines']} of {total_lines} lines are bad "
              f"({bad_ratio:.1%}), above the {args.max_bad_ratio:.1%} limit. "
              f"Is this the right folder?", file=sys.stderr)
        if args.strict:
            return 1

    # 3. analyse and write
    df = build_dataframe(records)
    units = build_unit_table(df)
    try:
        write_reports(df, units, records, bad_lines, stats, args.log_dir, args.report_dir)
    except OSError as e:
        print(f"ERROR: could not write reports: {e}", file=sys.stderr)
        return 1

    # 4. console summary
    done = units[units["status"] != "IN_PROGRESS"]
    print(f"Records: {len(df)} | bad lines: {len(bad_lines)} | units: {len(units)}")
    if len(done):
        print(f"First-pass yield: {done['first_pass'].mean() * 100:.1f}% | "
              f"Final yield: {done['final_pass'].mean() * 100:.1f}%")
    print(f"Reports written to {args.report_dir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())