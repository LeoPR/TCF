"""TCF v0.2 encoder — real columnar compression with progressive levels.

Levels:
    0  Expanded (no compression, baseline)
    1  RLE on columns (compress consecutive repeats)
    2  Sort by best column + RLE (maximize consecutive repeats)
    3  Dictionary encoding + sort + RLE (replace strings with indices)

All levels produce a flat supertable (JOIN of all tables).
All levels are fully reversible via decoder_v02.

Usage:
    from tcf.encoder_v02 import encode_v02

    text = encode_v02("data/metadata.json", "data/", level=2)
"""

from __future__ import annotations
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import TableMeta, load_schema
from .compression import (
    rle_encode, dict_build, sort_columns,
    fmt_num, is_numeric_column,
)


@dataclass
class V02Config:
    """Configuration for v0.2 encoder."""
    level: int = 2            # 0=expanded, 1=rle, 2=sorted+rle, 3=dict+rle
    include_stats: bool = True
    precision: int | None = None  # decimal places (None = auto-compact)


# ---------------------------------------------------------------------------
# Join tables into flat supertable
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


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def _stats_line(col: str, vals: list[str]) -> str | None:
    """Build STATS line for numeric column."""
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

    def _c(f: float) -> str:
        return str(int(f)) if f == int(f) else f"{f:.4g}"

    return f"# STATS {col}: n={n} sum={_c(s)} min={_c(min(floats))} max={_c(max(floats))} avg={_c(s / n)}"


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------

def encode_v02(
    meta_path: str | Path,
    data_dir: str | Path,
    config: V02Config | None = None,
) -> str:
    """Encode tables as a flat TCF with progressive compression.

    Args:
        meta_path: Path to metadata.json
        data_dir:  Directory with CSV files
        config:    V02Config (default: level=2, stats=True)

    Returns:
        TCF v0.2 formatted string
    """
    if config is None:
        config = V02Config()

    meta_path = Path(meta_path)
    data_dir = Path(data_dir)
    schema = load_schema(meta_path, data_dir)

    all_data: dict[str, list[dict[str, str]]] = {}
    for name, meta in schema.items():
        with meta.file.open(newline="", encoding="utf-8") as fh:
            all_data[name] = list(csv.DictReader(fh))

    fact_name, col_names, columns = _join_tables(schema, all_data)
    n = len(columns[col_names[0]]) if col_names else 0

    if not n:
        return f"# TCF v0.2 level={config.level}\n\n## {fact_name} n=0\n"

    # Format numeric values
    for col in col_names:
        if is_numeric_column(columns[col]):
            columns[col] = [fmt_num(v, config.precision) for v in columns[col]]

    # Level 2+: sort rows to maximize RLE
    sort_by = ""
    if config.level >= 2:
        columns, sort_by = sort_columns(columns)

    # Level 3: dictionary encoding for text columns
    dicts: dict[str, list[str]] = {}  # col -> ordered unique values
    if config.level >= 3:
        for col in col_names:
            if not is_numeric_column(columns[col]):
                unique_vals, indices = dict_build(columns[col])
                dicts[col] = unique_vals
                columns[col] = [str(i) for i in indices]

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
    lines.append(f"## {fact_name} n={n}{sort_tag}")

    # Dictionary lines
    for col in col_names:
        if col in dicts:
            lines.append(f"# dict {col}: {','.join(dicts[col])}")

    # Stats
    if config.include_stats:
        for col in col_names:
            vals = columns[col]
            # For dict-encoded columns, stats don't make sense
            if col not in dicts and is_numeric_column(vals):
                stat = _stats_line(col, vals)
                if stat:
                    lines.append(stat)

    # Data columns
    for col in col_names:
        vals = columns[col]
        lines.append(f"{col}:")

        if config.level >= 1:
            # RLE compress
            rle_lines = rle_encode(vals)
            lines.extend(rle_lines)
        else:
            # Level 0: one value per line, no compression
            lines.extend(vals)

    lines.append("")
    return "\n".join(lines)
