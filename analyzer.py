from datetime import datetime
from pathlib import Path
from log_parser import SERIAL_RE, find_log_files, parse_file, load_records, find_retests

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"


def count_lines(path: Path) -> int:
    with path.open(encoding="utf-8", errors="replace") as fh:
        return sum(1 for _ in fh)

# ---------- output ----------
def write_file_report(log_files: list[Path]) -> None:
    """Write reports/file_report.txt and add a line to reports/run_history.txt."""
    report_lines: list[str] = []
    total_lines = 0
    for f in log_files:
        st = f.stat()
        n = count_lines(f)
        total_lines += n
        modified = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        report_lines.append(
            f"{f.relative_to(LOG_DIR)} | {n} lines | {st.st_size / 1024:.1f} KB | modified {modified}"
        )
    report_lines.append(f"TOTAL | {len(log_files)} files | {total_lines} lines")
    (REPORT_DIR / "file_report.txt").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with (REPORT_DIR / "run_history.txt").open("a", encoding="utf-8") as fh:
        fh.write(f"{timestamp} | {len(log_files)} files | {total_lines} lines\n")


def mask_file(src: Path, dst: Path) -> None:
    """Copy src to dst with serial numbers masked (A1001 -> A***)."""
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
    
    retests = find_retests(records)
    print(stats)
    print(f"Unique units: {len({r['sn'] for r in records})}")
    print(f"Retested (unit, station) pairs: {len(retests)}")
    


if __name__ == "__main__":
    main()