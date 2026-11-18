"""Factory test log analyzer: entry point.

Run:  python analyzer.py
Reads logs/ and writes all reports to reports/.
"""
from datetime import datetime
from pathlib import Path

from analysis import (
    build_dataframe,
    build_unit_table,
    fail_rate_by_test,
    get_failures,
    station_yield_table,
    value_stats_by_test,
    write_yield_report,
)
from log_parser import SERIAL_RE, find_retests, load_records

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"


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


# ---------- main ----------

def main() -> None:
    try:
        records, bad_lines, stats = load_records(LOG_DIR)
    except FileNotFoundError as e:
        print("ERROR:", e)
        return
    if not records:
        print("No records found.")
        return

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    df = build_dataframe(records)
    units = build_unit_table(df)

    # file and data-quality reports
    write_file_report(stats["files_used"], LOG_DIR, REPORT_DIR)
    write_data_quality_report(stats, bad_lines, len(find_retests(records)),
                              REPORT_DIR / "data_quality.txt")

    # record-level reports
    df.to_csv(REPORT_DIR / "records.csv", index=False)
    get_failures(df).to_csv(REPORT_DIR / "failures.csv", index=False)
    fail_rate_by_test(df).to_csv(REPORT_DIR / "fail_rate_by_test.csv")
    value_stats_by_test(df).to_csv(REPORT_DIR / "value_stats_by_test.csv")

    # unit-level and station-level yield
    units.to_csv(REPORT_DIR / "unit_results.csv")
    station_yield_table(df).to_csv(REPORT_DIR / "station_yield.csv", index=False)
    write_yield_report(units, REPORT_DIR / "yield_summary.txt")

    done = units[units["status"] != "IN_PROGRESS"]
    print(f"Records: {len(df)} | bad lines: {len(bad_lines)} | units: {len(units)}")
    if len(done):
        print(f"First-pass yield: {done['first_pass'].mean() * 100:.1f}% | "
              f"Final yield: {done['final_pass'].mean() * 100:.1f}%")
    print(f"Reports written to {REPORT_DIR}")


if __name__ == "__main__":
    main()