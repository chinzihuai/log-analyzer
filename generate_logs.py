"""Generate fake factory test logs for practice.

Run:  python generate_logs.py
Creates a logs/ folder next to this script with a few .log files.
"""
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)  # same output every run

# station -> list of (test name, nominal value, tolerance)
TESTS = {
    "ICT": [("Voltage_3V3", 3.30, 0.10), ("Voltage_5V", 5.00, 0.15), ("Resistance_R12", 100.0, 3.0)],
    "FCT": [("Current_Idle", 0.50, 0.05), ("Freq_Clock", 16.0, 0.05), ("Temp_CPU", 45.0, 8.0)],
}

# (file name, serial prefix, date, number of units)
FILES = [
    ("line1_2026-10-20.log", "A", "2026-10-20", 40),
    ("line1_2026-10-21.log", "A", "2026-10-21", 40),
    ("line2_2026-10-21.log", "B", "2026-10-21", 30),
]


def make_value(nominal, tol, defect):
    """Normal readings sit close to nominal; a defect pushes the value out of tolerance."""
    if defect:
        return round(nominal + random.choice([-1, 1]) * tol * random.uniform(1.2, 2.0), 2)
    return round(random.gauss(nominal, tol / 3), 2)


def run_station(lines, t, sn, station, defect_rate):
    """Run every test of one station for one unit. Returns (all_passed, new_time)."""
    all_passed = True
    for test, nominal, tol in TESTS[station]:
        t += timedelta(seconds=1)
        value = make_value(nominal, tol, random.random() < defect_rate)
        result = "PASS" if abs(value - nominal) <= tol else "FAIL"
        all_passed = all_passed and result == "PASS"
        lines.append(
            f"{t:%Y-%m-%d %H:%M:%S} | SN={sn} | STATION={station} "
            f"| TEST={test} | VALUE={value} | RESULT={result}"
        )
    return all_passed, t


def main():
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    counters = {"A": 1000, "B": 1000}

    for name, prefix, date, units in FILES:
        t = datetime.strptime(f"{date} 08:00:00", "%Y-%m-%d %H:%M:%S")
        lines = [f"# Test log - {name} - generated for practice"]

        for _ in range(units):
            counters[prefix] += 1
            sn = f"{prefix}{counters[prefix]}"
            t += timedelta(seconds=random.randint(20, 60))

            passed, t = run_station(lines, t, sn, "ICT", defect_rate=0.04)
            if not passed and random.random() < 0.5:  # operator retests the unit
                t += timedelta(seconds=30)
                passed, t = run_station(lines, t, sn, "ICT", defect_rate=0.0)
            if passed:
                passed, t = run_station(lines, t, sn, "FCT", defect_rate=0.04)

            # messy data on purpose, so your parser has something to survive
            if random.random() < 0.05:
                lines.append(f"{t:%Y-%m-%d %H:%M:%S} | SN={sn} | STATION=ICT | TEST=Voltage_3V3 | VALUE=ERR | RESULT=")
            if random.random() < 0.05:
                lines.append("")

        (log_dir / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote {name}: {len(lines)} lines")


if __name__ == "__main__":
    main()
