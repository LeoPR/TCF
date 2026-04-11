"""Markdown table writer — baseline human-readable format.

Writes a Markdown table with pipe separators. Long tables are truncated
with a note — full Markdown tables are impractical for thousands of rows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping


def _cell(v) -> str:
    if v is None:
        return ""
    s = str(v)
    # Escape pipes in cell values
    return s.replace("|", "\\|").replace("\n", " ")


def write_markdown(
    path: Path,
    columns: list[str],
    rows: Iterable[Mapping],
    *,
    max_rows: int | None = 500,
) -> int:
    """Write rows to a Markdown table. Returns rows written.

    Args:
        path: output file path
        columns: column order
        rows: iterable of dict-like rows
        max_rows: truncate after this many rows (None = all). Default 500
                  because MD tables >500 rows are unreadable in any viewer.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    rows_list = list(rows) if not isinstance(rows, list) else rows
    total = len(rows_list)

    if max_rows is not None and total > max_rows:
        shown = rows_list[:max_rows]
    else:
        shown = rows_list

    with path.open("w", encoding="utf-8") as f:
        f.write("| " + " | ".join(columns) + " |\n")
        f.write("|" + "|".join("---" for _ in columns) + "|\n")
        for row in shown:
            f.write("| " + " | ".join(_cell(row.get(c)) for c in columns) + " |\n")

        if max_rows is not None and total > max_rows:
            f.write(f"\n_... {total - max_rows} more rows truncated_\n")

    return len(shown)
