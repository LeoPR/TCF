"""JSON Lines writer — baseline row-oriented format with typed values.

Writes one JSON object per line. Preserves actual types (int, float, null)
instead of CSV's everything-is-a-string approach.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping


def write_jsonl(
    path: Path,
    columns: list[str],
    rows: Iterable[Mapping],
    *,
    ensure_ascii: bool = False,
) -> int:
    """Write rows to JSONL (one JSON object per line).

    Args:
        path: output file path
        columns: column order (used to order keys inside each object)
        rows: iterable of dict-like rows
        ensure_ascii: if True, escape non-ASCII to \\uXXXX (default False)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            ordered = {c: row.get(c) for c in columns}
            f.write(json.dumps(ordered, ensure_ascii=ensure_ascii))
            f.write("\n")
            count += 1
    return count
