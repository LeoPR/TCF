"""Decoder: TCF text → dict of table_name → list[dict].

Handles all EncoderConfig variants:
  - raw_float  : values decoded as-is
  - int_scaled : values divided by SCALE factor (# SCALE factor=N comment)
  - bins_16    : bin indices mapped back to midpoints (# BINS col min=X max=Y n=N comment)
  - id_raw     : FK IDs kept as-is
  - dict       : ## DICT block is informational — IDs decoded as-is (original IDs)
  - hint       : > hint lines are ignored — IDs decoded as-is
  - inline     : resolved-name columns decoded as-is (no ID recovery)
"""

from __future__ import annotations
import re
from typing import Any


# ---------------------------------------------------------------------------
# RLE expansion
# ---------------------------------------------------------------------------

def _rle_expand(token: str) -> list[str]:
    """Expand 'N:val' → [val]*N; 'val' → [val]."""
    if ":" in token:
        n_str, _, val = token.partition(":")
        if n_str.isdigit():
            return [val] * int(n_str)
    return [token]


def _expand_line(values_str: str) -> list[str]:
    result: list[str] = []
    for token in values_str.split():
        result.extend(_rle_expand(token))
    return result


# ---------------------------------------------------------------------------
# Annotation parsers
# ---------------------------------------------------------------------------

_BINS_RE  = re.compile(r"#\s*BINS\s+(\w+)\s+min=([\d.eE+\-]+)\s+max=([\d.eE+\-]+)\s+n=(\d+)")
_SCALE_RE = re.compile(r"#\s*SCALE\s+factor=(\d+)")
_DICT_RE  = re.compile(r"^##\s+DICT\s+(\w+)")   # ## DICT col_name (ref ...)
_TABLE_RE = re.compile(r"^##\s+(\w+)\s+n=(\d+)")
_COL_RE   = re.compile(r"^(\w+)(?:\[(\w+)\])?:\s*(.*)")


def _midpoint(bin_idx: int, min_v: float, max_v: float, n_bins: int) -> str:
    """Convert a bin index back to the midpoint value of that bin."""
    rng = max_v - min_v
    if rng == 0:
        return str(min_v)
    step = rng / n_bins
    mid = min_v + (bin_idx + 0.5) * step
    # Compact formatting
    return str(int(mid)) if mid == int(mid) else f"{mid:.4g}"


# ---------------------------------------------------------------------------
# Main decoder
# ---------------------------------------------------------------------------

def decode(tcf_text: str) -> dict[str, list[dict[str, Any]]]:
    """Parse TCF text and return tables as row-oriented dicts.

    Returns:
        {"table_name": [{"col": "val", ...}, ...], ...}

    Notes:
        - [sorted] columns are skipped (derived views).
        - [key] columns are included.
        - ## DICT blocks are parsed for reference but do NOT alter column values
          (IDs remain as original IDs in id_raw / dict / hint modes).
        - # BINS and # SCALE comments are used to invert numeric encoding.
        - inline FK columns are decoded as name strings (no ID recovery).
    """
    tables:        dict[str, list[dict]] = {}
    current_table: str | None = None
    current_n:     int = 0
    current_cols:  dict[str, list[str]] = {}

    # Per-table annotations accumulated while parsing
    bins_map:  dict[str, tuple[float, float, int]] = {}  # col → (min, max, n)
    scale_val: int | None = None   # applies to next numeric column in this table
    in_dict_block: bool = False    # True while reading a ## DICT body line

    def _flush() -> None:
        if current_table and current_cols:
            tables[current_table] = _cols_to_rows(current_cols, current_n)

    for raw_line in tcf_text.splitlines():
        line = raw_line.strip()

        if not line:
            in_dict_block = False
            continue

        # ── File-level instructions (>) ──────────────────────────────
        if line.startswith(">"):
            continue

        # ── ## DICT block header ──────────────────────────────────────
        m_dict = _DICT_RE.match(line)
        if m_dict:
            in_dict_block = True   # next non-empty line is the pairs body
            continue

        # ── DICT body (id=name pairs) — skip, informational only ─────
        if in_dict_block:
            in_dict_block = False
            continue

        # ── ## Table header ───────────────────────────────────────────
        m_table = _TABLE_RE.match(line)
        if m_table:
            _flush()
            current_table = m_table.group(1)
            current_n     = int(m_table.group(2))
            current_cols  = {}
            bins_map      = {}
            scale_val     = None
            continue

        # ── Single-# comments ─────────────────────────────────────────
        if line.startswith("#"):
            # # BINS col min=X max=Y n=N
            m_bins = _BINS_RE.match(line)
            if m_bins and current_table:
                col   = m_bins.group(1)
                min_v = float(m_bins.group(2))
                max_v = float(m_bins.group(3))
                n     = int(m_bins.group(4))
                bins_map[col] = (min_v, max_v, n)
            # # SCALE factor=N  — applies to NEXT numeric column
            m_scale = _SCALE_RE.match(line)
            if m_scale:
                scale_val = int(m_scale.group(1))
            continue

        if current_table is None:
            continue

        # ── Column line ───────────────────────────────────────────────
        m_col = _COL_RE.match(line)
        if not m_col:
            continue

        col_name  = m_col.group(1)
        modifier  = m_col.group(2)   # "key", "sorted", or None
        vals_str  = m_col.group(3)

        if modifier == "sorted":
            continue   # derived view — skip

        raw_vals = _expand_line(vals_str)

        # Invert bins encoding
        if col_name in bins_map:
            min_v, max_v, n_bins = bins_map[col_name]
            raw_vals = [
                _midpoint(int(v), min_v, max_v, n_bins)
                if v.lstrip("-").isdigit() else v
                for v in raw_vals
            ]

        # Invert int_scaled encoding
        elif scale_val is not None:
            try:
                raw_vals = [
                    str(int(v) / scale_val) if v.lstrip("-").isdigit() else v
                    for v in raw_vals
                ]
                scale_val = None   # consumed for this column
            except (ValueError, TypeError):
                scale_val = None

        current_cols[col_name] = raw_vals

    _flush()
    return tables


def _cols_to_rows(cols: dict[str, list[str]], n: int) -> list[dict[str, str]]:
    keys = list(cols.keys())
    return [
        {k: (cols[k][i] if i < len(cols[k]) else "") for k in keys}
        for i in range(n)
    ]
