"""Compression primitives for TCF v0.2.

RLE notation: `N*val` means val repeated N times. No prefix = single occurrence.
Separator: newline (one value/group per line, CSV-like).

Functions:
    rle_encode(values) -> list[str]   lines with N*val notation
    rle_decode(lines)  -> list[str]   expanded values
    dict_build(values) -> (mapping, indices)
    dict_resolve(mapping, indices) -> list[str]
    sort_columns(columns, sort_by) -> columns  reorder all columns by one
"""

from __future__ import annotations
from collections import Counter
from typing import Sequence


# ---------------------------------------------------------------------------
# RLE encode/decode
# ---------------------------------------------------------------------------

def rle_encode(values: Sequence[str]) -> list[str]:
    """Run-length encode a list of values.

    Consecutive repeats become `N*val`. Singles stay as `val`.
    Returns a list of lines (one per group).

    Example:
        ["ana", "ana", "ana", "luiz", "luiz"] -> ["3*ana", "2*luiz"]
        ["a", "b", "b", "a"] -> ["a", "2*b", "a"]
    """
    if not values:
        return []
    lines: list[str] = []
    i = 0
    while i < len(values):
        val = values[i]
        count = 1
        while i + count < len(values) and values[i + count] == val:
            count += 1
        lines.append(f"{count}*{val}" if count > 1 else val)
        i += count
    return lines


def rle_decode(lines: Sequence[str]) -> list[str]:
    """Decode RLE lines back to flat list.

    `3*ana` -> ["ana", "ana", "ana"]
    `ana`   -> ["ana"]
    """
    result: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "*" in line:
            star_pos = line.index("*")
            count_str = line[:star_pos]
            val = line[star_pos + 1:]
            if count_str.isdigit():
                result.extend([val] * int(count_str))
            else:
                # Not a valid RLE token, treat as literal
                result.append(line)
        else:
            result.append(line)
    return result


# ---------------------------------------------------------------------------
# Dictionary encoding
# ---------------------------------------------------------------------------

def dict_build(values: Sequence[str]) -> tuple[list[str], list[int]]:
    """Build a dictionary mapping for repeated string values.

    Returns:
        (unique_values_sorted_by_frequency, index_per_row)

    Example:
        ["ana","ana","ana","luiz","luiz"]
        -> (["ana", "luiz"], [0, 0, 0, 1, 1])
    """
    counter = Counter(values)
    # Sort by frequency descending (most common = index 0 = shortest ref)
    ordered = [val for val, _ in counter.most_common()]
    val_to_idx = {val: i for i, val in enumerate(ordered)}
    indices = [val_to_idx[v] for v in values]
    return ordered, indices


def dict_resolve(mapping: Sequence[str], indices: Sequence[int]) -> list[str]:
    """Resolve dictionary indices back to values.

    Example:
        (["ana", "luiz"], [0, 0, 0, 1, 1]) -> ["ana","ana","ana","luiz","luiz"]
    """
    return [mapping[i] for i in indices]


# ---------------------------------------------------------------------------
# Column sorting
# ---------------------------------------------------------------------------

def sort_columns(
    columns: dict[str, list[str]],
    sort_by: str | None = None,
) -> tuple[dict[str, list[str]], str]:
    """Sort all columns by one column to maximize RLE compression.

    If sort_by is None, auto-selects the column with lowest cardinality
    (most repetition = best RLE).

    Returns (sorted_columns, sort_by_column_name).
    """
    col_names = list(columns.keys())
    if not col_names or not columns[col_names[0]]:
        return columns, sort_by or ""

    n = len(columns[col_names[0]])

    # Auto-select: column with lowest cardinality (most repetition)
    if sort_by is None:
        best_col = min(col_names, key=lambda c: len(set(columns[c])))
        sort_by = best_col

    if sort_by not in columns:
        return columns, sort_by

    # Build sort indices
    indices = list(range(n))
    sort_vals = columns[sort_by]
    indices.sort(key=lambda i: sort_vals[i])

    # Apply same order to all columns
    sorted_cols: dict[str, list[str]] = {}
    for col in col_names:
        sorted_cols[col] = [columns[col][i] for i in indices]

    return sorted_cols, sort_by


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------

def fmt_num(v: str, precision: int | None = None) -> str:
    """Format a numeric string compactly: 2.50 -> 2.5, 12.00 -> 12."""
    try:
        f = float(v)
    except (ValueError, TypeError):
        return v
    if f == int(f):
        return str(int(f))
    if precision is not None:
        return f"{f:.{precision}f}"
    return str(f)


def is_numeric_column(values: Sequence[str]) -> bool:
    """Check if a column is numeric (all values parse as float)."""
    for v in values:
        if v.strip():
            try:
                float(v)
            except (ValueError, TypeError):
                return False
    return True
