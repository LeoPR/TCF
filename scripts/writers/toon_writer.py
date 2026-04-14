"""TOON (Token-Oriented Object Notation) writer.

Implements the tabular array subset of TOON per spec at toonformat.dev.
This is the format most comparable to TCF for tabular data.

TOON tabular syntax:
    table_name[N]{field1,field2,...}:
      val1,val2,...
      val1,val2,...

Spec rules applied:
  - Strings with special chars (colon, comma, quotes, whitespace) are quoted
  - null values are literal 'null'
  - Numbers are unquoted
  - Boolean is lowercase 'true'/'false'

This is a SUPPORT SCRIPT, not part of TCF core.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping


# Characters that require quoting in TOON
_TOON_SPECIAL = set(':,"\\[]{}')
_TOON_RESERVED = {"true", "false", "null"}


def _needs_quoting(val: str) -> bool:
    """Check if a TOON value needs double-quote wrapping."""
    if not val:
        return True  # empty string must be quoted as ""
    if val in _TOON_RESERVED:
        return True  # reserved words must be quoted if they are strings
    if val[0] in (' ', '\t') or val[-1] in (' ', '\t'):
        return True  # leading/trailing whitespace
    if any(c in _TOON_SPECIAL for c in val):
        return True
    # Check if it looks like a number (then needs quoting if it's a string)
    try:
        float(val)
        return False  # it IS a number, don't quote
    except ValueError:
        pass
    return False


def _toon_escape(val: str) -> str:
    """Escape a string value for TOON."""
    # Replace backslash first, then quotes, then control chars
    val = val.replace("\\", "\\\\")
    val = val.replace('"', '\\"')
    val = val.replace("\n", "\\n")
    val = val.replace("\r", "\\r")
    val = val.replace("\t", "\\t")
    return val


def _format_value(val: Any) -> str:
    """Convert a Python value to TOON text representation."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    # String
    s = str(val)
    if _needs_quoting(s):
        return '"' + _toon_escape(s) + '"'
    return s


def encode_toon(
    table_name: str,
    columns: list[str],
    rows: Iterable[Mapping],
    *,
    delimiter: str = ",",
) -> str:
    """Encode tabular data to TOON format.

    Args:
        table_name: name for the array header
        columns: ordered list of column names
        rows: iterable of dict-like rows
        delimiter: value separator (default ',')

    Returns:
        TOON formatted string
    """
    rows_list = list(rows) if not isinstance(rows, list) else rows
    n = len(rows_list)

    # Header
    fields = delimiter.join(columns)
    header = f"{table_name}[{n}]{{{fields}}}:"

    # Rows (indented with 2 spaces per TOON spec)
    data_lines = []
    for row in rows_list:
        vals = [_format_value(row.get(col)) for col in columns]
        data_lines.append("  " + delimiter.join(vals))

    return header + "\n" + "\n".join(data_lines) + "\n"


def write_toon(
    path: Path,
    columns: list[str],
    rows: Iterable[Mapping],
    *,
    table_name: str = "data",
    delimiter: str = ",",
) -> int:
    """Write rows to a TOON file. Returns row count."""
    rows_list = list(rows) if not isinstance(rows, list) else rows
    text = encode_toon(table_name, columns, rows_list, delimiter=delimiter)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return len(rows_list)
