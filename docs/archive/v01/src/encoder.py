"""Encoder: CSV + metadata → TCF text.

Supports multiple encoding variants via EncoderConfig:

  Numeric:
    raw_float   — compact float, lossless (default)
    int_scaled  — multiply by scale factor, emit as integer, lossless
    bins_N      — uniform quantization, lossy (bin index 0..N-1)

  FK representation:
    id_raw      — original FK ID, no context hint (default)
    dict        — emit ## DICT block mapping ID → name before the table
    hint        — emit > comment line after FK column mapping ID → name
    inline      — JOIN at encode time, emit resolved names (lossy roundtrip)

  Sort:
    include_sorted=True  — also emit col[sorted] with RLE (default)
    include_sorted=False — omit sorted variants
"""

from __future__ import annotations
import csv
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .schema import TableMeta, load_schema


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class EncoderConfig:
    """Controls how the encoder represents numeric and relational data.

    numeric:
        "raw_float"  compact floats, lossless (default)
        "int_scaled" integers after ×int_scale, lossless
        "bins_16"    uniform bin index 0..n_bins-1, lossy

    fk_mode:
        "id_raw"   raw ID, no hint (default)
        "dict"     ## DICT block mapping id → name before the table block
        "hint"     > comment after the FK column with id → name map
        "inline"   resolved names in the column (JOIN, lossy roundtrip)

    include_sorted:
        True  emit col[sorted] RLE variant (default)
        False omit sorted variants
    """
    numeric: str = "raw_float"
    n_bins: int = 16
    int_scale: int = 100
    fk_mode: str = "id_raw"
    include_sorted: bool = True
    include_stats: bool = False

    def __post_init__(self) -> None:
        valid_numeric = {"raw_float", "int_scaled", "bins_16"}
        valid_fk     = {"id_raw", "dict", "hint", "inline"}
        if self.numeric not in valid_numeric:
            raise ValueError(f"numeric must be one of {valid_numeric}, got {self.numeric!r}")
        if self.fk_mode not in valid_fk:
            raise ValueError(f"fk_mode must be one of {valid_fk}, got {self.fk_mode!r}")


@dataclass
class EncodeReport:
    """Telemetry from an encode operation."""
    tcf_text: str
    elapsed_s: float
    input_bytes: int       # sum of CSV file sizes
    output_chars: int      # len(tcf_text)
    output_bytes: int      # len(tcf_text.encode('utf-8'))
    compression_ratio: float  # input_bytes / output_bytes
    tables: dict[str, int]    # table_name -> row_count
    config: dict[str, Any]    # EncoderConfig as dict

    def summary(self) -> str:
        lines = [
            f"Encode report:",
            f"  elapsed:     {self.elapsed_s:.4f}s",
            f"  input:       {self.input_bytes:,} bytes (CSV)",
            f"  output:      {self.output_bytes:,} bytes ({self.output_chars:,} chars)",
            f"  ratio:       {self.compression_ratio:.2f}x",
            f"  tables:      {len(self.tables)}",
        ]
        for name, n in self.tables.items():
            lines.append(f"    {name}: {n} rows")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _try_float(v: str) -> float | None:
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _is_numeric(values: Sequence[str], threshold: float = 0.95) -> bool:
    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return False
    ok = sum(1 for v in non_empty if _try_float(v) is not None)
    return ok / len(non_empty) >= threshold


def _fmt_num(v: str) -> str:
    """Compact float: '2.50' → '2.5', '12.00' → '12'."""
    f = float(v)
    return str(int(f)) if f == int(f) else str(f)


def _rle(values: Sequence[str]) -> str:
    """Run-length encode to space-separated string.
    Consecutive runs: '3:val'; singles: 'val'."""
    if not values:
        return ""
    parts: list[str] = []
    i = 0
    while i < len(values):
        val = values[i]
        count = 1
        while i + count < len(values) and values[i + count] == val:
            count += 1
        parts.append(f"{count}:{val}" if count > 1 else val)
        i += count
    return " ".join(parts)


def _sort_key(v: str):
    f = _try_float(v)
    return (0, f) if f is not None else (1, v)


# ---------------------------------------------------------------------------
# Numeric encoding helpers
# ---------------------------------------------------------------------------

def _encode_numeric_raw(vals: list[str]) -> tuple[list[str], list[str]]:
    """raw_float: compact formatting. Returns (encoded_vals, header_comments)."""
    encoded = [_fmt_num(v) if _try_float(v) is not None else v for v in vals]
    return encoded, []


def _encode_numeric_int_scaled(vals: list[str], scale: int) -> tuple[list[str], list[str]]:
    """int_scaled: multiply by scale, truncate to int. Returns (encoded, comments)."""
    encoded = [
        str(int(round(float(v) * scale))) if _try_float(v) is not None else v
        for v in vals
    ]
    comments = [f"# SCALE factor={scale}"]
    return encoded, comments


def _encode_numeric_bins(vals: list[str], n_bins: int, col: str) -> tuple[list[str], list[str]]:
    """bins_N: uniform quantization. Returns (bin_indices, comments)."""
    floats = [float(v) for v in vals if _try_float(v) is not None]
    if not floats:
        return vals, []
    min_v = min(floats)
    max_v = max(floats)
    rng = max_v - min_v

    def _bin(v: str) -> str:
        f = _try_float(v)
        if f is None:
            return v
        if rng == 0:
            return "0"
        idx = int((f - min_v) / rng * n_bins)
        return str(min(idx, n_bins - 1))

    encoded = [_bin(v) for v in vals]
    comments = [f"# BINS {col} min={min_v} max={max_v} n={n_bins}"]
    return encoded, comments


# ---------------------------------------------------------------------------
# FK helpers
# ---------------------------------------------------------------------------

def _build_id_name_map(
    ref_table_name: str,
    all_data: dict[str, list[dict[str, str]]],
    schema: dict[str, TableMeta],
) -> dict[str, str]:
    """Return {pk_value: first_non_pk_column_value} for a referenced table."""
    meta = schema.get(ref_table_name)
    rows = all_data.get(ref_table_name, [])
    if not rows:
        return {}
    pk = meta.pk if meta else None
    cols = list(rows[0].keys())
    label_col = next((c for c in cols if c != pk), cols[0] if cols else None)
    if not pk or not label_col:
        return {}
    return {r[pk]: r[label_col] for r in rows}


def _dict_block(col: str, ref_table: str, id_name: dict[str, str]) -> str:
    """Emit a ## DICT block: one mapping per line, compact."""
    pairs = " ".join(f"{k}={v}" for k, v in id_name.items())
    return f"## DICT {col} (ref {ref_table}.nome)\n{pairs}"


def _hint_line(col: str, ref_table: str, id_name: dict[str, str]) -> str:
    """Emit a > hint comment inline after the column."""
    pairs = " ".join(f"{k}={v}" for k, v in id_name.items())
    return f"> {col} ref {ref_table}.nome -> {pairs}"


# ---------------------------------------------------------------------------
# Stats helpers (LLM facilitator hints)
# ---------------------------------------------------------------------------

def _numeric_stats_line(col: str, vals: list[str]) -> str:
    """Build a # STATS comment with count, sum, min, max, avg for a numeric column."""
    floats = [float(v) for v in vals if _try_float(v) is not None]
    if not floats:
        return ""
    n = len(floats)
    s = sum(floats)
    avg = s / n
    mn = min(floats)
    mx = max(floats)

    def _compact(f: float) -> str:
        return str(int(f)) if f == int(f) else f"{f:.4g}"

    return f"# STATS {col} n={n} sum={_compact(s)} min={_compact(mn)} max={_compact(mx)} avg={_compact(avg)}"


def _categorical_stats_line(col: str, vals: list[str]) -> str:
    """Build a # STATS comment with distinct count and mode for a categorical column."""
    if not vals:
        return ""
    distinct = len(set(vals))
    counter = Counter(vals)
    mode_val, mode_count = counter.most_common(1)[0]
    return f"# STATS {col} n={len(vals)} distinct={distinct} mode={mode_val}({mode_count})"


# ---------------------------------------------------------------------------
# Table encoder
# ---------------------------------------------------------------------------

def encode_table(
    name: str,
    meta: TableMeta,
    config: EncoderConfig,
    all_data: dict[str, list[dict[str, str]]],
    schema: dict[str, TableMeta],
) -> str:
    """Encode one CSV table to a TCF block string."""
    rows = all_data[name]
    n = len(rows)
    if not rows:
        return f"## {name} n=0"

    columns = list(rows[0].keys())

    # Collect DICT blocks (emitted before the ## table header)
    dict_blocks: list[str] = []
    if config.fk_mode == "dict":
        for col in columns:
            if col in meta.fks:
                ref = meta.fks[col]
                id_name = _build_id_name_map(ref, all_data, schema)
                if id_name:
                    dict_blocks.append(_dict_block(col, ref, id_name))

    lines: list[str] = [f"## {name} n={n}"]

    for col in columns:
        vals = [r[col].strip() for r in rows]
        is_pk = col == meta.pk
        is_fk = col in meta.fks

        # ── Primary key ────────────────────────────────────────────────
        if is_pk:
            lines.append(f"{col}[key]: " + " ".join(vals))
            continue

        # ── Foreign key ────────────────────────────────────────────────
        if is_fk:
            ref = meta.fks[col]
            id_name = _build_id_name_map(ref, all_data, schema)

            if config.fk_mode == "inline":
                resolved = [id_name.get(v, v) for v in vals]
                col_label = col.removeprefix("id_")  # id_pessoa → pessoa
                lines.append(f"{col_label}: " + " ".join(resolved))
                if config.include_sorted:
                    sorted_resolved = sorted(resolved, key=_sort_key)
                    lines.append(f"{col_label}[sorted]: " + _rle(sorted_resolved))
            else:
                # id_raw, dict, hint — all emit original IDs
                lines.append(f"{col}: " + " ".join(vals))
                if config.fk_mode == "hint" and id_name:
                    lines.append(_hint_line(col, ref, id_name))
                if config.include_sorted:
                    sorted_vals = sorted(vals, key=_sort_key)
                    lines.append(f"{col}[sorted]: " + _rle(sorted_vals))
            continue

        # ── Numeric ────────────────────────────────────────────────────
        if _is_numeric(vals):
            if config.numeric == "int_scaled":
                encoded, comments = _encode_numeric_int_scaled(vals, config.int_scale)
            elif config.numeric == "bins_16":
                encoded, comments = _encode_numeric_bins(vals, config.n_bins, col)
            else:
                encoded, comments = _encode_numeric_raw(vals)

            for c in comments:
                lines.append(c)
            if config.include_stats:
                stats = _numeric_stats_line(col, vals)
                if stats:
                    lines.append(stats)
            lines.append(f"{col}: " + " ".join(encoded))
            continue

        # ── Categorical ────────────────────────────────────────────────
        if config.include_stats:
            stats = _categorical_stats_line(col, vals)
            if stats:
                lines.append(stats)
        lines.append(f"{col}: " + " ".join(vals))

    block = "\n".join(lines)
    if dict_blocks:
        return "\n\n".join(dict_blocks) + "\n\n" + block
    return block


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def _build_header(config: EncoderConfig) -> str:
    lines = ["# TCF v0.1"]
    lines.append("> N:val = val repeated N times consecutively. No prefix = single occurrence.")
    lines.append("> Columns marked [sorted] are sorted — do NOT correlate their positions across columns.")
    lines.append("> Columns marked [key] are primary keys.")
    if config.numeric == "int_scaled":
        lines.append(f"> SCALE: integer values = original × {config.int_scale}. Divide to recover float.")
    if config.numeric == "bins_16":
        lines.append(f"> BINS: integer values are bin indices 0..{config.n_bins - 1}. See # BINS comments for min/max.")
    if config.fk_mode == "dict":
        lines.append("> DICT blocks map FK id → name for each FK column.")
    if config.fk_mode == "hint":
        lines.append("> Lines starting with '>' after a FK column map id → name.")
    if config.fk_mode == "inline":
        lines.append("> FK columns are resolved to names — original IDs not present.")
    if config.include_stats:
        lines.append("> Lines starting with '# STATS' provide pre-computed statistics for each column.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = EncoderConfig()


def encode(
    meta_path: str | Path,
    data_dir: str | Path,
    config: EncoderConfig | None = None,
) -> str:
    """Encode all tables defined in metadata.json to a TCF string.

    Args:
        meta_path: Path to metadata.json
        data_dir:  Directory containing the CSV files
        config:    EncoderConfig controlling encoding variants (default: raw_float, id_raw)

    Returns:
        TCF-formatted string
    """
    if config is None:
        config = _DEFAULT_CONFIG

    meta_path = Path(meta_path)
    data_dir  = Path(data_dir)
    schema    = load_schema(meta_path, data_dir)

    # Load all tables up-front (needed for FK resolution)
    all_data: dict[str, list[dict[str, str]]] = {}
    for name, meta in schema.items():
        with meta.file.open(newline="", encoding="utf-8") as fh:
            all_data[name] = list(csv.DictReader(fh))

    header = _build_header(config)
    blocks = [header]
    for name, meta in schema.items():
        blocks.append(encode_table(name, meta, config, all_data, schema))

    return "\n\n".join(blocks) + "\n"


def encode_with_report(
    meta_path: str | Path,
    data_dir: str | Path,
    config: EncoderConfig | None = None,
) -> EncodeReport:
    """Encode and return TCF text with telemetry (timing, sizes, ratio).

    Same as encode() but wraps the result in an EncodeReport with metrics.
    """
    if config is None:
        config = _DEFAULT_CONFIG

    meta_path = Path(meta_path)
    data_dir  = Path(data_dir)

    # Measure input size (sum of CSV files)
    schema = load_schema(meta_path, data_dir)
    input_bytes = 0
    for _, meta in schema.items():
        input_bytes += meta.file.stat().st_size

    # Encode with timing
    t0 = time.perf_counter()
    tcf_text = encode(meta_path, data_dir, config=config)
    elapsed = time.perf_counter() - t0

    output_bytes = len(tcf_text.encode("utf-8"))

    # Table row counts
    table_counts = {}
    all_data: dict[str, list[dict[str, str]]] = {}
    for name, meta in schema.items():
        with meta.file.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
            all_data[name] = rows
            table_counts[name] = len(rows)

    return EncodeReport(
        tcf_text=tcf_text,
        elapsed_s=round(elapsed, 6),
        input_bytes=input_bytes,
        output_chars=len(tcf_text),
        output_bytes=output_bytes,
        compression_ratio=round(input_bytes / output_bytes, 4) if output_bytes else 0.0,
        tables=table_counts,
        config={
            "numeric": config.numeric,
            "n_bins": config.n_bins,
            "int_scale": config.int_scale,
            "fk_mode": config.fk_mode,
            "include_sorted": config.include_sorted,
            "include_stats": config.include_stats,
        },
    )
