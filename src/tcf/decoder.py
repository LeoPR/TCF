"""TCF decoder — all compression levels.

Auto-detects level from header and reverses compression:
    - RLE: `3*ana` -> ["ana", "ana", "ana"]
    - Dict: resolves numeric indices back to strings via `# dict` lines
    - Normalize: extracts reference tables from unique text values

Usage:
    from tcf import decode

    # Flat table only
    tables = decode(tcf_text, normalize=False)
    # {"vendas": [{"pessoa": "Ana", "produto": "Caneta", "vl": "2.5"}, ...]}

    # Rebuild reference tables
    tables = decode(tcf_text, normalize=True)
    # {"pessoa": [...], "produto": [...], "vendas": [...]}
"""

from __future__ import annotations
import re
from typing import Any

from .compression import rle_decode, dict_resolve


_TABLE_RE = re.compile(r"^##\s+(\w+)\s+n=(\d+)")
_DICT_RE = re.compile(r"^#\s+dict\s+(\w+):\s*(.*)")


def decode(
    tcf_text: str,
    normalize: bool = True,
) -> dict[str, list[dict[str, str]]]:
    """Decode TCF text back to tables.

    Args:
        tcf_text:  TCF v0.2 text (any level)
        normalize: If True, extract reference tables with sequential IDs.

    Returns:
        dict of table_name -> list of row dicts
    """
    table_name: str | None = None
    table_n: int = 0
    dicts: dict[str, list[str]] = {}    # col -> ordered unique values
    columns: dict[str, list[str]] = {}  # col -> values (after RLE expansion)
    col_order: list[str] = []

    current_col: str | None = None
    current_lines: list[str] = []

    def _flush_col() -> None:
        nonlocal current_col, current_lines
        if current_col and current_lines:
            expanded = rle_decode(current_lines)
            # Resolve dict if applicable
            if current_col in dicts:
                mapping = dicts[current_col]
                indices = [int(v) for v in expanded]
                expanded = dict_resolve(mapping, indices)
            columns[current_col] = expanded
            if current_col not in col_order:
                col_order.append(current_col)
        current_col = None
        current_lines = []

    for raw_line in tcf_text.splitlines():
        line = raw_line.strip()

        # Table header
        m = _TABLE_RE.match(line)
        if m:
            _flush_col()
            table_name = m.group(1)
            table_n = int(m.group(2))
            continue

        # Dict line
        m = _DICT_RE.match(line)
        if m:
            col = m.group(1)
            vals_str = m.group(2)
            dicts[col] = [v.strip() for v in vals_str.split(",")]
            continue

        # Comment/header lines
        if line.startswith("#") or line.startswith(">"):
            continue

        # Empty line
        if not line:
            continue

        # Column header (word followed by colon at end of line)
        if line.endswith(":") and not line[0].isdigit():
            _flush_col()
            current_col = line[:-1]  # remove trailing ":"
            current_lines = []
            continue

        # Data line (belongs to current column)
        if current_col is not None:
            current_lines.append(line)

    _flush_col()

    if not table_name:
        table_name = "data"
    if not table_n and columns:
        table_n = max(len(v) for v in columns.values())

    # Build flat rows
    flat_rows: list[dict[str, str]] = []
    for i in range(table_n):
        row = {}
        for col in col_order:
            vals = columns.get(col, [])
            row[col] = vals[i] if i < len(vals) else ""
        flat_rows.append(row)

    if not normalize:
        return {table_name: flat_rows}

    # Normalize: detect text columns with repetition -> reference tables
    tables: dict[str, list[dict[str, str]]] = {}

    for col in col_order:
        vals = columns.get(col, [])
        is_numeric = True
        for v in vals:
            if v.strip():
                try:
                    float(v)
                except (ValueError, TypeError):
                    is_numeric = False
                    break

        if not is_numeric and len(set(vals)) < len(vals):
            # Text column with repetition -> reference table
            unique_vals = sorted(set(vals))
            name_to_id = {name: str(i + 1) for i, name in enumerate(unique_vals)}
            tables[col] = [{"id": str(i + 1), "nome": name} for i, name in enumerate(unique_vals)]

            # Replace names with IDs in fact rows
            for row in flat_rows:
                if col in row:
                    row[f"id_{col}"] = name_to_id[row[col]]
                    del row[col]

    tables[table_name] = flat_rows
    return tables
