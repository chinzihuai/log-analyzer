import re
NON_PRINTABLE_RE = re.compile(r"[^\x20-\x7E]")  
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
def get_value(line:str)->float|None:
    q4=re.search(r"VALUE=([\d.]+)",line)

    if q4:
        return float(q4.group(1))
    else:
        return None

def get_hours(line:str)->str|None:
    q6=re.search(r"\d{4}-\d{2}-\d{2}\s(\d{2})",line)

    return q6.group(1)

def clean_line(line: str) -> str:
    #replace non-printable characters with nothing, then strip leading/trailing whitespace
    return NON_PRINTABLE_RE.sub("", line).strip()

def parse_line(line: str) -> dict | None:
    """Parse one log line into a dict, or return None if it is invalid."""
    m=LINE_RE.fullmatch(clean_line(line))
    if not m:
        return None
    record = m.groupdict()
    record["value"] = float(record["value"])
    record["result"]=record["result"].upper()
    return record

def parse_file(path:Path)->tuple[list[dict],int]:
    """Return (records, number_of_bad_lines) for one log file."""
    records: list[dict] = []
    bad = 0
    with path.open(encoding="utf-8",errors="replace") as fh:
        for line in fh:
            stripped=line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            record=parse_line(stripped)
            if record is None:
                bad+=1
                continue
            record["file"]=path.name
            records.append(record)
    return records,bad

    

line_pass = "2026-10-20 08:01:01 | SN=A1001 | STATION=ICT | TEST=Voltage_3V3 | VALUE=3.3 | RESULT=PASS"
line_fail = "2026-10-20 08:04:58 | SN=A1007 | STATION=ICT | TEST=Voltage_3V3 | VALUE=3.41 | RESULT=FAIL"
line_err  = "2026-10-20 08:24:23 | SN=A1031 | STATION=ICT | TEST=Voltage_3V3 | VALUE=ERR | RESULT="

q1=re.search(r"STATION=(\w+)",line_pass)
q2=re.search(r"TEST=(\w+)",line_pass)
q3=re.search(r"VALUE=([\d.]+)",line_fail)

print(q1.group(1))
print(q2.group(1))
print(float(q3.group(1))+1)

print(get_value(line_pass))
print(get_value(line_fail))
print(get_value(line_err))

print(get_hours(line_pass))
print(get_hours(line_fail))
print(get_hours(line_err))

print(parse_line("2026-10-20 08:01:01 | SN=A1001 | STATION=ICT | TEST=Voltage_3V3 | VALUE=3.3 | RESULT=pass"))
# {'time': '2026-10-20 08:01:01', 'sn': 'A1001', 'station': 'ICT',
#  'test': 'Voltage_3V3', 'value': 3.3, 'result': 'PASS'}

print(parse_line(line_err))     # None
