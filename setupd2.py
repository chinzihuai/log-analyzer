from pathlib import Path

logs = Path(__file__).parent / "logs"

# 1. a subfolder with its own log file
sub = logs / "2026-10"
sub.mkdir(parents=True, exist_ok=True)
(sub / "line3_2026-10-22.log").write_text(
    "2026-10-22 09:00:01 | SN=C1001 | STATION=ICT | TEST=Voltage_3V3 | VALUE=3.31 | RESULT=PASS\n"
    "2026-10-22 09:00:02 | SN=C1001 | STATION=ICT | TEST=Voltage_5V | VALUE=5.02 | RESULT=PASS\n",
    encoding="utf-8",
)

# 2. an empty file
(logs / "empty.log").write_text("", encoding="utf-8")

# 3. a file with broken (non-UTF-8) bytes
(logs / "bad_encoding.log").write_bytes(
    b"2026-10-22 10:00:01 | SN=C1002 | STATION=ICT | TEST=Voltage_3V3 | VALUE=3.30 | RESULT=PASS \xff\xfe\n"
)