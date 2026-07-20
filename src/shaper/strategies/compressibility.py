"""Compressibility strategy — score rows by rarity and filter by quantile.

Score = sum of -log2(freq/total) for each categorical column value.
Rows with rare values get high scores (harder to compress via RLE).

The score is cached on disk per table per dataset to avoid recomputation.
Cache is invalidated if the SQLite file hash changes.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "scripts"))  # _paths/dataset_reader ficam em scripts/ (gadget movido p/ src/, 2026-07-19)
from _paths import data_root  # noqa: E402
from dataset_reader import is_text  # noqa: E402

from ..pipeline import register_strategy


CACHE_DIR_NAME = "shaper-cache"


def _cache_dir(dataset: str) -> Path:
    return data_root() / CACHE_DIR_NAME / dataset


def _db_hash(dataset: str) -> str:
    """Quick hash of the SQLite file for cache invalidation."""
    from _paths import interim_db
    db_path = interim_db(dataset)
    if not db_path.exists():
        return ""
    # Hash first 64KB + file size (fast, good enough for change detection)
    h = hashlib.md5()
    with open(db_path, "rb") as f:
        h.update(f.read(65536))
    h.update(str(db_path.stat().st_size).encode())
    return h.hexdigest()


def _compute_rarity_scores(
    rows: list[dict], schema: dict[str, dict]
) -> list[float]:
    """Compute rarity score for each row based on categorical columns."""
    # Identify categorical columns
    cat_cols = [col for col, meta in schema.items() if is_text(meta)]
    if not cat_cols:
        return [0.0] * len(rows)

    # Count frequencies
    freqs: dict[str, Counter] = {}
    for col in cat_cols:
        freqs[col] = Counter(row.get(col) for row in rows)

    total = len(rows)
    scores = []
    for row in rows:
        score = 0.0
        for col in cat_cols:
            val = row.get(col)
            freq = freqs[col].get(val, 1)
            if freq > 0 and total > 0:
                score += -math.log2(freq / total)
        scores.append(round(score, 4))

    return scores


def _load_or_compute_scores(
    reader, table_name: str, rows: list[dict], dataset: str
) -> list[float]:
    """Load cached scores or compute and cache them."""
    cache = _cache_dir(dataset)
    cache.mkdir(parents=True, exist_ok=True)

    score_file = cache / f"{table_name}_rarity.json"
    meta_file = cache / f"{table_name}_rarity_meta.json"

    current_hash = _db_hash(dataset)

    # Check cache
    if score_file.exists() and meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        if meta.get("db_hash") == current_hash and meta.get("n_rows") == len(rows):
            return json.loads(score_file.read_text(encoding="utf-8"))

    # Compute
    schema = reader.schema(table_name)
    scores = _compute_rarity_scores(rows, schema)

    # Cache
    score_file.write_text(json.dumps(scores), encoding="utf-8")
    meta_file.write_text(json.dumps({
        "db_hash": current_hash,
        "n_rows": len(rows),
        "dataset": dataset,
        "table": table_name,
    }), encoding="utf-8")

    return scores


def _apply(reader, tables, request, trace):
    cr = request.compressibility_range
    if cr is None:
        return tables  # passthrough

    lo, hi = cr
    result = {}

    for name, rows in tables.items():
        if not rows:
            result[name] = rows
            continue

        scores = _load_or_compute_scores(reader, name, rows, request.dataset)

        # Compute quantile thresholds
        sorted_scores = sorted(scores)
        n = len(sorted_scores)
        lo_idx = int(round(lo * n))
        hi_idx = int(round(hi * n))
        lo_thresh = sorted_scores[min(lo_idx, n - 1)]
        hi_thresh = sorted_scores[min(hi_idx, n - 1)] if hi_idx < n else sorted_scores[-1] + 1

        # Filter rows in range
        filtered = [
            row for row, score in zip(rows, scores)
            if lo_thresh <= score <= hi_thresh
        ]

        avg_score_all = sum(scores) / len(scores) if scores else 0
        avg_score_filtered = (
            sum(s for s in scores if lo_thresh <= s <= hi_thresh) /
            max(1, len(filtered))
        )

        result[name] = filtered
        trace.append(
            f"compressibility: {name} range=({lo},{hi}) "
            f"-> {len(filtered)} of {len(rows)} rows "
            f"(avg_score: {avg_score_all:.2f} -> {avg_score_filtered:.2f})"
        )

    return result


register_strategy("compressibility", _apply)
