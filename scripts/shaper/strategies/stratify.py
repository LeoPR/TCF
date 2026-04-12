"""Stratification strategy — sample with group representation.

Ensures at least one row per distinct value of `stratify_by` column.
If combined with volume, distributes proportionally across groups.
"""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Any

from ..pipeline import register_strategy


def _apply(reader, tables, request, trace):
    col = request.stratify_by
    if col is None:
        return tables  # passthrough

    result = {}
    for name, rows in tables.items():
        if not rows:
            result[name] = rows
            continue

        if col not in rows[0]:
            trace.append(f"stratify: WARNING column '{col}' not in {name}, skipping")
            result[name] = rows
            continue

        # Group rows by column value
        groups: dict[Any, list[dict]] = defaultdict(list)
        for row in rows:
            groups[row[col]].append(row)

        n_groups = len(groups)
        n_total = len(rows)

        # Determine target per group
        vol = request.volume
        if vol is None:
            # No volume limit — return all, grouped
            sampled = []
            for key in sorted(groups.keys(), key=lambda k: (k is None, str(k))):
                sampled.extend(groups[key])
            result[name] = sampled
            trace.append(f"stratify: {name} by '{col}' ({n_groups} groups, all rows)")
            continue

        if isinstance(vol, float):
            n_target = max(1, int(round(n_total * vol)))
        else:
            n_target = max(1, int(vol))

        # Proportional allocation (at least 1 per group if possible)
        per_group = max(1, n_target // n_groups)
        remainder = n_target - per_group * n_groups

        rng = random.Random(request.seed)
        sampled = []
        for i, key in enumerate(sorted(groups.keys(), key=lambda k: (k is None, str(k)))):
            group_rows = groups[key]
            # Some groups get +1 to use up remainder
            n_take = per_group + (1 if i < remainder else 0)
            n_take = min(n_take, len(group_rows))

            if n_take >= len(group_rows):
                sampled.extend(group_rows)
            else:
                indices = sorted(rng.sample(range(len(group_rows)), n_take))
                sampled.extend(group_rows[i] for i in indices)

        result[name] = sampled
        trace.append(
            f"stratify: {name} by '{col}' ({n_groups} groups, "
            f"~{per_group}/group, {len(sampled)} total from {n_total})"
        )

    return result


register_strategy("stratify", _apply)
