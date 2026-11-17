import re
import hashlib
from pathlib import Path
from collections import Counter
# One full log line, e.g.
# 2026-10-20 08:01:01 | SN=A1001 | STATION=ICT | TEST=Voltage_3V3 | VALUE=3.3 | RESULT=PASS
LINE_RE = re.compile(
    r"""
    (?P<time>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})   \s*\|\s*
    SN=(?P<sn>\w+)                                   \s*\|\s*
    STATION=(?P<station>\w+)                         \s*\|\s*
    TEST=(?P<test>\w+)                               \s*\|\s*
    VALUE=(?P<value>-?\d+(?:\.\d+)?)                 \s*\|\s*
    RESULT=(?P<result>PASS|FAIL)
    """,
    re.VERBOSE | re.IGNORECASE,
)
NON_PRINTABLE_RE = re.compile(r"[^\x20-\x7E]")  # anything except printable ASCII
DATE_SUFFIX_RE = re.compile(r"_\d{4}-\d{2}-\d{2}$")  # file names end with _YYYY-MM-DD
SERIAL_RE = re.compile(r"(SN=\w)\w+")  # keep first character, mask the rest

# ---------- finding files ----------

def find_log_files(log_dir: Path) -> list[Path]:
    """Return all valid, non-empty .log files under log_dir, including subfolders."""
    if not log_dir.is_dir():
        raise FileNotFoundError(f"Log folder not found: {log_dir}")

    files: list[Path] = []
    for f in log_dir.rglob("*.log"):
        if not DATE_SUFFIX_RE.search(f.stem):
            print(f"Skipping (no valid date in name): {f.name}")
            continue
        if f.stat().st_size == 0:
            print(f"Skipping empty file: {f.name}")
            continue
        files.append(f)
    return sorted(files)

# ---------- parsing ----------

def clean_line(line: str) -> str:
    """Remove non-printable characters, then strip surrounding whitespace."""
    return NON_PRINTABLE_RE.sub("", line).strip()

def parse_line(line: str) -> dict | None:
    """Parse one log line into a dict, or return None if it is invalid."""
    m = LINE_RE.fullmatch(clean_line(line))
    if m is None:
        return None
    record = m.groupdict()
    record["value"] = float(record["value"])
    record["result"] = record["result"].upper()
    return record

def parse_file(path: Path) -> tuple[list[dict], list[str]]:
    """Return (records, bad_lines) for one log file."""
    records: list[dict] = []
    bad_lines: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue  # blank or comment: not data
            record = parse_line(stripped)
            if record is None:
                bad_lines.append(stripped)
            else:
                record["file"] = path.name
                records.append(record)
    return records, bad_lines

def file_hash(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def drop_duplicate_files(files: list[Path]) -> list[Path]:
    """Keep one file per unique content; prefer the file closest to the top folder."""
    seen:dict[str,Path]={}
    unique:list[Path]=[]

    for f in sorted(files,key=lambda p: (len(p.parts), str(p))):
        digest = file_hash(f)
        if digest in seen:
            print(f"Duplicate file skipped: {f.parent.name}/{f.name} "
                  f"(same content as {seen[digest].parent.name}/{seen[digest].name})")
            continue
        seen[digest]=f
        unique.append(f)
    return unique

def drop_duplicate_records(records: list[dict]) -> list[dict]:
    seen:dict[tuple,dict]={}
    unique:list[dict]=[]

    for r in records:
        key=(r["time"],r["sn"],r["station"],r["test"])
        if key in seen:
            first_value=seen[key]
            if first_value["value"]!=r["value"]:
                print(f"CONFLICT: {r['sn']} {r['test']} at {r['time']} "
                      f"has {first_value['value']} and {r['value']}")
            continue
        seen[key]=r
        unique.append(r)

    return unique

def load_records(log_dir: Path) -> tuple[list[dict], list[str], dict]:
    """Find, de-duplicate and parse all logs. Returns (records, bad_lines, stats)."""
    files = find_log_files(log_dir)
    unique_files = drop_duplicate_files(files)

    records: list[dict] = []
    bad_lines: list[str] = []
    for f in unique_files:
        recs, bad = parse_file(f)
        records.extend(recs)
        bad_lines.extend(f"{f.name}: {line}" for line in bad)

    unique_records = drop_duplicate_records(records)

    stats = {
        "files_found": len(files),
        "duplicate_files": len(files) - len(unique_files),
        "records_parsed": len(records),
        "duplicate_records": len(records) - len(unique_records),
        "bad_lines": len(bad_lines),
    }
    return unique_records, bad_lines, stats

def find_retests(records: list[dict]) -> set[tuple[str, str]]:
    """Return (sn, station) pairs where the same test was run more than once."""
    counts = Counter((r["sn"], r["station"], r["test"]) for r in records)
    return {(sn, station) for (sn, station, test), n in counts.items() if n > 1}
