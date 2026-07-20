"""Ordering strategy — reorder rows in the output.

- "natural"       → no change (SQLite insertion order)
- "random"        → shuffle with request.seed
- "sorted:col"    → ascending by column
- "reverse:col"   → descending by column

This is the OUTPUT order (presentation to consumer).
It is NOT the internal sort for compression (that's TCF's job).
"""

from __future__ import annotations

import random
from typing import Any

from ..pipeline import register_strategy


def _apply(reader, tables, request, trace):
    order = request.order

    if order == "natural":
        trace.append("ordering: natural (no change)")
        return tables

    result = {}

    for name, rows in tables.items():
        if not rows:
            result[name] = rows
            continue

        if order == "random":
            shuffled = list(rows)
            random.Random(request.seed).shuffle(shuffled)
            result[name] = shuffled
            trace.append(f"ordering: {name} -> random (seed={request.seed})")

        elif order.startswith("sorted:"):
            col = order.split(":", 1)[1]
            if col not in rows[0]:
                trace.append(f"ordering: WARNING column '{col}' not in {name}, skipping sort")
                result[name] = rows
            else:
                result[name] = sorted(rows, key=lambda r: (r[col] is None, r[col]))
                trace.append(f"ordering: {name} -> sorted by {col} ASC")

        elif order.startswith("reverse:"):
            col = order.split(":", 1)[1]
            if col not in rows[0]:
                trace.append(f"ordering: WARNING column '{col}' not in {name}, skipping sort")
                result[name] = rows
            else:
                result[name] = sorted(rows, key=lambda r: (r[col] is None, r[col]), reverse=True)
                trace.append(f"ordering: {name} -> sorted by {col} DESC")

        else:
            trace.append(f"ordering: unknown order '{order}', using natural")
            result[name] = rows

    return result


register_strategy("orderer", _apply)
