"""Volume strategy — sample N rows or a fraction from each table.

- volume=100   → first 100 rows (after ordering)
- volume=0.1   → 10% of rows
- volume=None  → all rows (passthrough)
- volume=0     → empty (with trace warning)

Uses request.seed for reproducible random sampling when combined
with order="random".
"""

from __future__ import annotations

import random
from typing import Any

from ..pipeline import register_strategy


def _apply(reader, tables, request, trace):
    # Skip when FK-preserving strategy is active — it handles volume with integrity
    if getattr(request, "fk_preserving", False):
        trace.append("volume: SKIP (fk_preserving active, handled by fk_preserving strategy)")
        return tables

    vol = request.volume

    if vol is None:
        trace.append("volume: None (all rows)")
        return tables

    result = {}
    for name, rows in tables.items():
        n_total = len(rows)

        if isinstance(vol, float):
            n_target = max(0, int(round(n_total * vol)))
        else:
            n_target = max(0, int(vol))

        if n_target == 0:
            trace.append(f"volume: {name} -> 0 rows (WARNING: empty)")
            result[name] = []
            continue

        if n_target >= n_total:
            trace.append(f"volume: {name} -> {n_total} rows (all, volume >= total)")
            result[name] = rows
            continue

        # Sample deterministically using seed
        rng = random.Random(request.seed)
        indices = sorted(rng.sample(range(n_total), n_target))
        result[name] = [rows[i] for i in indices]
        trace.append(f"volume: {name} -> {n_target} of {n_total} rows (seed={request.seed})")

    return result


register_strategy("volume_sampler", _apply)
