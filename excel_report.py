"""Write several tables into one Excel workbook. This module only holds functions."""
from pathlib import Path

import pandas as pd
from openpyxl.utils import get_column_letter


def write_excel_report(sheets: dict[str, pd.DataFrame], path: Path) -> None:
    """Write each DataFrame to its own sheet.

    A meaningful index (date, test name, serial number) is kept as the first column.
    A plain 0, 1, 2... index is dropped.
    """
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, table in sheets.items():
            keep_index = not isinstance(table.index, pd.RangeIndex)
            table.to_excel(writer, sheet_name=name, index=keep_index)
            ws = writer.sheets[name]
            ws.freeze_panes = "A2"                       # keep the header row visible
            fit_columns(ws, table.reset_index() if keep_index else table)


def fit_columns(ws, table: pd.DataFrame) -> None:
    """Set each column's width to fit its longest value (capped at 40)."""
    for i, col in enumerate(table.columns, start=1):
        longest = max([len(str(col))] + [len(str(v)) for v in table[col]])
        ws.column_dimensions[get_column_letter(i)].width = min(longest + 2, 40)