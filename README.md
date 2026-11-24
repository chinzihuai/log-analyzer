# Automated Factory Test Log Analyzer & Yield Reporter

A command-line tool that reads raw factory test logs (ICT and FCT stations), cleans and de-duplicates them, and produces yield reports: per unit, per station, per production line and per day. It also writes charts and an Excel workbook that can be handed to a supervisor.

The project was built as a Python learning exercise using `pathlib`, `re` and `pandas`. The log data in this repository is synthetic.

## Features

- Finds `.log` files recursively, including subfolders, and skips empty files or files without a `_YYYY-MM-DD` date in the name.
- Detects duplicate files by content hash (SHA-256) and keeps only one copy.
- Parses each line with a regular expression; bad lines (for example `VALUE=ERR`) are collected and reported instead of crashing the run.
- Handles non-printable characters and broken encodings.
- Removes duplicate records but keeps genuine retests (same unit and test, measured at a different time).
- Calculates yield **per unit** (serial number), not per record, with both first-pass and final yield.
- Reports yield by line, by date and by station, plus a daily trend and the top failing tests.
- Writes CSV and text reports, three PNG charts and one Excel workbook.
- Reports problems clearly (missing folder, no valid records, too many bad lines, report file locked) and returns a proper exit code.

## Project structure

```
log-analyzer/
├── analyzer.py        # entry point: command-line arguments, main(), report writing
├── log_parser.py      # find, de-duplicate, clean and parse log files
├── analysis.py        # pandas analysis: failures, unit table, yield tables
├── charts.py          # matplotlib charts
├── excel_report.py    # multi-sheet Excel workbook
├── generate_logs.py   # creates synthetic sample logs
├── requirements.txt   # third-party dependencies
├── logs/              # input: .log files
└── reports/           # output: all generated reports
```

## Installation

Python 3.10 or newer is required (the code uses `list[str]` and `dict | None` type hints).

```
pip install -r requirements.txt
```

## Usage

Run with the default folders (`logs/` in, `reports/` out):

```
python analyzer.py
```

Choose the folders yourself:

```
python analyzer.py D:\other_logs
python analyzer.py -o out_test
python analyzer.py D:\other_logs -o out_test
```

Show all options:

```
python analyzer.py --help
```

| Argument | Meaning | Default |
|---|---|---|
| `log_dir` (positional, optional) | Folder that contains the `.log` files | `./logs` |
| `-o`, `--report-dir` | Folder where the reports are written | `./reports` |

A warning is printed when more than 5% of the data lines cannot be parsed, which usually means the wrong folder was given.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Error: log folder not found, no valid records, or the reports could not be written (for example `yield_report.xlsx` is open in Excel) |

## Log format

One test record per line:

```
2026-10-20 08:01:01 | SN=A1001 | STATION=ICT | TEST=Voltage_3V3 | VALUE=3.3 | RESULT=PASS
```

Blank lines and lines starting with `#` are ignored. File names must end with `_YYYY-MM-DD` before the extension, and the production line is taken from the start of the name, for example `line1_2026-10-20.log` belongs to `line1`.

The `RESULT` field is read from the log as it is. The sample data uses these limits:

| Station | Test | Nominal ± tolerance |
|---|---|---|
| ICT (in-circuit test) | Voltage_3V3 | 3.30 ± 0.10 |
| ICT | Voltage_5V | 5.00 ± 0.15 |
| ICT | Resistance_R12 | 100 ± 3.0 |
| FCT (functional test) | Current_Idle | 0.50 ± 0.05 |
| FCT | Freq_Clock | 16.0 ± 0.05 |
| FCT | Temp_CPU | 45 ± 8 |

Units go through ICT first, then FCT. A unit that fails ICT and is not retested never reaches FCT.

## Output files

All files are written to the report folder.

| File | Content |
|---|---|
| `yield_summary.txt` | Headline yield, status counts, yield by line and by date |
| `unit_results.csv` | One row per unit: flags, line, date, failing station, status |
| `station_yield.csv` | First-pass and final yield for each station |
| `daily_trend.csv` | Yield per date and the change in first-pass yield versus the previous date |
| `fail_rate_by_test.csv` | Fail rate of every test |
| `top_failing_tests.csv` | The five tests with the highest fail rate |
| `value_stats_by_test.csv` | Count, mean, standard deviation, min and max of the measured values per test |
| `failures.csv` | Every failed record, oldest first |
| `records.csv` | All clean records after parsing and de-duplication |
| `data_quality.txt` | What was skipped, removed or suspicious while loading |
| `file_report.txt` | Lines, size and modification time of each log file used |
| `run_history.txt` | One line per run (appended, never overwritten) |
| `daily_yield.png` | Line chart of first-pass and final yield per date |
| `station_yield.png` | Grouped bar chart of yield by station |
| `top_failing_tests.png` | Horizontal bar chart of the top failing tests |
| `yield_report.xlsx` | Workbook with sheets Units, Daily trend, Station yield, Top failing tests, Failures |

## How yield is calculated

Yield is calculated per **unit** (serial number). Counting records would be misleading: in the sample data 95.7% of records pass, but only 75.5% of units pass first time.

- **Unit**: one serial number (`SN`).
- **Complete unit**: a unit that has records at every station.
- **First-pass yield (FPY)**: units whose every test passed on the first attempt, and that are complete.
- **Final yield**: units whose every test passed on the latest attempt, and that are complete.
- **Retest vs duplicate**: a duplicate is the same record twice (identical timestamp) and is removed. A retest is the same unit, station and test measured again at a different time and is kept. Duplicates are always removed before retests are counted.

Each unit gets one status. If several apply, the first one in this list wins:

| Status | Meaning |
|---|---|
| `FAIL_AT_<station>` | The latest result of some test at that station is a failure |
| `IN_PROGRESS` | No failure, but a station is missing. Excluded from the yield denominator and reported separately |
| `PASS_AFTER_RETEST` | Passed, but at least one test needed a retest |
| `PASS_FIRST_TIME` | Passed with no retest |

Station yield uses the units that entered the station as the denominator, and a unit counts only if it has every test of that station.

## Data quality handling

| Situation | What the tool does |
|---|---|
| Empty file | Skipped, a message is printed |
| File name without `_YYYY-MM-DD` | Skipped, a message is printed |
| Identical copy of a file | Only one copy is read (the one closest to the top folder) |
| Files in subfolders | Found and read |
| Broken encoding or non-printable characters | Characters are replaced or removed, the line is still parsed if possible |
| Blank line or `#` comment | Ignored, not counted as bad |
| Line that does not match the format (for example `VALUE=ERR`) | Counted as a bad line and listed in `data_quality.txt` |
| Same time, unit, station and test twice | Duplicate removed; a `CONFLICT` message is printed if the two values differ |
| Folder missing or no valid records | Error message and exit code 1 |

## Sample result

Produced from the three sample log files (`line1_2026-10-20.log`, `line1_2026-10-21.log`, `line2_2026-10-21.log`).

| Item | Value |
|---|---|
| Records after de-duplication | 669 |
| Bad lines | 4 |
| Units | 110 |
| First-pass yield | 83 / 110 = 75.5% |
| Final yield | 90 / 110 = 81.8% |

Status counts:

| Status | Units |
|---|---|
| PASS_FIRST_TIME | 83 |
| PASS_AFTER_RETEST | 7 |
| FAIL_AT_FCT | 15 |
| FAIL_AT_ICT | 5 |

Yield by station:

| Station | Units tested | First-pass yield | Final yield |
|---|---|---|---|
| ICT | 110 | 88.2% | 95.5% |
| FCT | 105 | 85.7% | 85.7% |

Yield by date:

| Date | Units | First-pass yield | Final yield |
|---|---|---|---|
| 2026-10-20 | 40 | 75.0% | 82.5% |
| 2026-10-21 | 70 | 75.7% | 81.4% |

Highest fail rate: `Freq_Clock`, 8 failures in 105 runs (7.6%).

## Limitations

- The sample data is synthetic and small. The difference between `line1` (80 units) and `line2` (30 units) may not be statistically meaningful, and the daily trend covers only two days.
- Only ICT has retests in the sample data, so first-pass and final yield are identical for FCT.
- Pass or fail comes from the `RESULT` field in the log; the tool does not recompute it from the tolerances.