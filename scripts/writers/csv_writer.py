"""CSV writer — baseline format.

Writes a list[dict] of rows to a CSV file using only stdlib csv module.
Preserves NULLs as empty strings (CSV standard).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping


def write_csv(
    path: Path,
    columns: list[str],
    rows: Iterable[Mapping],
    *,
    delimiter: str = ",",
    quoting: int = csv.QUOTE_MINIMAL,
) -> int:
    """Write rows to CSV. Returns the number of rows written.

    Args:
        path: output file path
        columns: explicit column order
        rows: iterable of dict-like rows
        delimiter: field separator (default ',')
        quoting: csv.QUOTE_* constant
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=columns, delimiter=delimiter, quoting=quoting
        )
        writer.writeheader()
        for row in rows:
            # csv.DictWriter doesn't handle None well in all locales — normalize
            writer.writerow({c: ("" if row.get(c) is None else row.get(c))
                             for c in columns})
            count += 1
    return count
