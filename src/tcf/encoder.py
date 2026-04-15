"""TCF encoder — columnar compression with progressive levels.

Levels:
    0  Expanded (no compression, baseline)
    1  RLE on columns (compress consecutive repeats)
    2  Sort by best column + RLE (maximize consecutive repeats)
    3  Dictionary encoding + sort + RLE (replace strings with indices)

All levels are fully reversible via decode().

Architecture:
    encode_columns()  — CORE: accepts dict[str, list[str]], no IO
    encode_rows()     — convenience: accepts list[dict], transposes, calls encode_columns
    encode()          — legacy wrapper: reads CSV files, joins tables, calls encode_columns

Usage:
    # Core (no IO, no filesystem):
    from tcf import encode_columns, EncodeConfig
    text = encode_columns("lineitem", {"l_quantity": ["1","2","3"], ...})

    # From row-oriented data:
    from tcf import encode_rows
    text = encode_rows("lineitem", [{"l_quantity": 1, ...}, ...])

    # Legacy (reads CSV from disk):
    from tcf import encode
    text = encode("data/metadata.json", "data/")
"""

from __future__ import annotations
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import TableMeta, load_schema
from .compression import (
    rle_encode, dict_build, sort_columns,
    fmt_num, is_numeric_column,
)


_Z_SCORES: dict[float, float] = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}


@dataclass
class EncodeConfig:
    """Configuration for TCF encoder."""
    level: int = 2            # 0=expanded, 1=rle, 2=sorted+rle, 3=dict+rle
    include_stats: bool = True
    precision: int | None = None  # decimal places (None = auto-compact)
    full_n: int | None = None     # total rows in source (enables sampling CI)
    stats_ci: float = 0.95        # confidence level: 0.90, 0.95, or 0.99
    stats_compact: bool = False   # compact "avg~err%" vs verbose "err=X% full_n=N"


# ---------------------------------------------------------------------------
# Stats (shared by all encode paths)
# ---------------------------------------------------------------------------

def _stats_line(
    col: str,
    vals: list[str],
    full_n: int | None = None,
    ci: float = 0.95,
    compact: bool = False,
) -> str | None:
    """Build STATS line for numeric column.

    When full_n is set and full_n > n (truncated dataset), appends a
    confidence interval for the mean:
        verbose:  err=X.X% full_n=N
        compact:  avg~X% (replaces avg value)
    """
    floats = []
    for v in vals:
        try:
            floats.append(float(v))
        except (ValueError, TypeError):
            pass
    if not floats:
        return None
    n = len(floats)
    s = sum(floats)
    mn = min(floats)
    mx = max(floats)
    avg = s / n

    def _c(f: float) -> str:
        return str(int(f)) if f == int(f) else f"{f:.4g}"

    base = f"# STATS {col}: n={n} sum={_c(s)} min={_c(mn)} max={_c(mx)}"

    if full_n is not None and full_n > n and n >= 2 and avg != 0:
        variance = sum((x - avg) ** 2 for x in floats) / (n - 1)
        std = math.sqrt(variance)
        z = _Z_SCORES.get(ci, 1.960)
        margin = z * std / math.sqrt(n)
        err_pct = abs(margin / avg) * 100
        if compact:
            avg_part = f"{_c(avg)}~{err_pct:.0f}%"
            return f"{base} avg={avg_part}"
        else:
            return f"{base} avg={_c(avg)} err={err_pct:.1f}% full_n={full_n}"

    return f"{base} avg={_c(avg)}"


# ---------------------------------------------------------------------------
# Core encoder — pure translation, no IO
# ---------------------------------------------------------------------------

def encode_columns(
    table_name: str,
    columns: dict[str, list[str]],
    *,
    config: EncodeConfig | None = None,
) -> str:
    """Encode column-oriented data to TCF text.

    This is the CORE encoder function. It accepts data already loaded
    into Python structures and performs only format translation:
    numeric formatting, sort, dictionary encoding, RLE, and text assembly.

    It does NOT read files, parse CSV, connect to databases, or resolve
    foreign keys. Those operations belong in wrappers or external scripts.

    Args:
        table_name: name for the ## header (e.g. "lineitem", "adult")
        columns:    {col_name: [val1, val2, ...]} — all lists same length,
                    all values as strings
        config:     compression level, stats, precision (default: level=2)

    Returns:
        TCF formatted text string

    Raises:
        ValueError: if columns have different lengths or are empty
    """
    if config is None:
        config = EncodeConfig()

    col_names = list(columns.keys())

    if not col_names:
        return f"# TCF v0.2 level={config.level}\n\n## {table_name} n=0\n"

    # Validate: all columns same length
    lengths = {col: len(vals) for col, vals in columns.items()}
    unique_lengths = set(lengths.values())
    if len(unique_lengths) > 1:
        raise ValueError(
            f"All columns must have the same length. Got: {lengths}"
        )

    n = next(iter(lengths.values()))
    if n == 0:
        return f"# TCF v0.2 level={config.level}\n\n## {table_name} n=0\n"

    # Work on a copy to avoid mutating caller's data
    cols = {col: list(vals) for col, vals in columns.items()}

    # Format numeric values
    for col in col_names:
        if is_numeric_column(cols[col]):
            cols[col] = [fmt_num(v, config.precision) for v in cols[col]]

    # Level 2+: sort rows to maximize RLE
    sort_by = ""
    if config.level >= 2:
        cols, sort_by = sort_columns(cols)

    # Level 3: dictionary encoding for text columns
    dicts: dict[str, list[str]] = {}
    if config.level >= 3:
        for col in col_names:
            if not is_numeric_column(cols[col]):
                unique_vals, indices = dict_build(cols[col])
                dicts[col] = unique_vals
                cols[col] = [str(i) for i in indices]

    # Build output
    lines: list[str] = []

    # Header
    header_parts = [f"# TCF v0.2 level={config.level}"]
    if config.level >= 1:
        header_parts.append("# N*val = val repeated N times")
    lines.extend(header_parts)

    # Table header
    sort_tag = f" sorted_by={sort_by}" if sort_by else ""
    lines.append("")
    lines.append(f"## {table_name} n={n}{sort_tag}")

    # Dictionary lines
    for col in col_names:
        if col in dicts:
            lines.append(f"# dict {col}: {','.join(dicts[col])}")

    # Stats
    if config.include_stats:
        for col in col_names:
            vals = cols[col]
            if col not in dicts and is_numeric_column(vals):
                stat = _stats_line(col, vals, full_n=config.full_n, ci=config.stats_ci, compact=config.stats_compact)
                if stat:
                    lines.append(stat)

    # Data columns
    for col in col_names:
        vals = cols[col]
        lines.append(f"{col}:")

        if config.level >= 1:
            rle_lines = rle_encode(vals)
            lines.extend(rle_lines)
        else:
            lines.extend(vals)

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Row-oriented convenience wrapper
# ---------------------------------------------------------------------------

def encode_rows(
    table_name: str,
    rows: list[dict[str, Any]],
    *,
    config: EncodeConfig | None = None,
) -> str:
    """Encode row-oriented data to TCF text.

    Convenience wrapper: transposes list[dict] to dict[str, list[str]],
    then calls encode_columns(). This is the natural interface for data
    coming from the shaper, SQLite queries, or pandas DataFrames.

    Type conversion:
        None  -> "" (empty string)
        int   -> str(int)
        float -> str(float)
        other -> str(value)

    Args:
        table_name: name for the ## header
        rows:       list of row dicts [{col: val, ...}, ...]
        config:     compression level, stats, precision

    Returns:
        TCF formatted text string
    """
    if not rows:
        return encode_columns(table_name, {}, config=config)

    col_names = list(rows[0].keys())
    columns: dict[str, list[str]] = {}

    for col in col_names:
        vals = []
        for row in rows:
            v = row.get(col)
            if v is None:
                vals.append("")
            else:
                vals.append(str(v))
        columns[col] = vals

    return encode_columns(table_name, columns, config=config)


# ---------------------------------------------------------------------------
# Legacy wrapper — reads CSV files, joins tables, calls encode_columns
# ---------------------------------------------------------------------------

def _join_tables(
    schema: dict[str, TableMeta],
    all_data: dict[str, list[dict[str, str]]],
) -> tuple[str, list[str], dict[str, list[str]]]:
    """Join fact table with references. Returns (name, col_names, columns_dict)."""
    fact_name = max(schema, key=lambda t: len(schema[t].fks))
    fact_meta = schema[fact_name]
    fact_rows = all_data[fact_name]

    if not fact_rows:
        return fact_name, [], {}

    # Build FK lookups
    fk_lookups: dict[str, dict[str, str]] = {}
    for fk_col, ref_table in fact_meta.fks.items():
        ref_meta = schema.get(ref_table)
        ref_rows = all_data.get(ref_table, [])
        if not ref_rows or not ref_meta or not ref_meta.pk:
            continue
        pk = ref_meta.pk
        cols = list(ref_rows[0].keys())
        label_col = next((c for c in cols if c != pk), cols[0])
        fk_lookups[fk_col] = {r[pk]: r[label_col] for r in ref_rows}

    # Build columns dict (resolved names, no IDs)
    col_names: list[str] = []
    columns: dict[str, list[str]] = {}

    for col in fact_rows[0].keys():
        if col == fact_meta.pk:
            continue
        if col in fact_meta.fks:
            clean = col.removeprefix("id_")
            col_names.append(clean)
            lookup = fk_lookups.get(col, {})
            columns[clean] = [lookup.get(r[col], r[col]) for r in fact_rows]
        else:
            col_names.append(col)
            columns[col] = [r[col] for r in fact_rows]

    return fact_name, col_names, columns


def encode(
    meta_path: str | Path,
    data_dir: str | Path,
    config: EncodeConfig | None = None,
) -> str:
    """Encode tables from CSV files as flat TCF with progressive compression.

    Legacy convenience wrapper that reads CSV files from disk, joins tables
    via foreign keys, and delegates to encode_columns() for the actual
    format translation.

    For new code, prefer encode_columns() or encode_rows() which accept
    data already loaded into Python structures.

    Args:
        meta_path: Path to metadata.json
        data_dir:  Directory with CSV files
        config:    EncodeConfig (default: level=2, stats=True)

    Returns:
        TCF formatted string
    """
    if config is None:
        config = EncodeConfig()

    meta_path = Path(meta_path)
    data_dir = Path(data_dir)
    schema = load_schema(meta_path, data_dir)

    all_data: dict[str, list[dict[str, str]]] = {}
    for name, meta in schema.items():
        with meta.file.open(newline="", encoding="utf-8") as fh:
            all_data[name] = list(csv.DictReader(fh))

    fact_name, col_names, columns = _join_tables(schema, all_data)

    # Delegate to core
    ordered_columns = {col: columns[col] for col in col_names}
    return encode_columns(fact_name, ordered_columns, config=config)
