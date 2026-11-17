from pathlib import Path

logs = Path(__file__).parent / "logs"

# 1. exact copy of a log in an archive subfolder
archive = logs / "archive"
archive.mkdir(exist_ok=True)
src = logs / "line1_2026-10-20.log"
(archive / src.name).write_bytes(src.read_bytes())

# 2. a different file that overlaps: header + first 10 data lines of the same log
first_lines = src.read_text(encoding="utf-8").splitlines()[:11]
(logs / "line1b_2026-10-20.log").write_text("\n".join(first_lines) + "\n", encoding="utf-8")