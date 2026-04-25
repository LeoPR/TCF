"""Stratification strategy — proportional allocation by group.

Per-table stratified sampling: distributes `volume` proportionally across
distinct values of `stratify_by` column, preserving the original population
distribution ("general representativeness").

Min 1 row per group when budget allows (preserves categorical coverage).

When `fk_preserving=True`, stratification is delegated to fk_preserving
strategy (applied to fact table; dims filtered by FK afterwards).
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

    # When fk_preserving is active, stratification is handled there
    # (applied to fact table; dims are filtered by FK afterwards).
    # Running stratify here would duplicate sampling.
    if getattr(request, "fk_preserving", False):
        trace.append(
            f"stratify: SKIP (fk_preserving active, stratify_by='{col}' "
            f"will be applied to fact table)"
        )
        return tables

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

        # Proportional allocation (Neyman-style) with min-1 per group
        sorted_keys = sorted(groups.keys(), key=lambda k: (k is None, str(k)))
        targets: dict = {}
        for key in sorted_keys:
            pop = len(groups[key])
            share = round(n_target * pop / n_total)
            if share == 0 and pop > 0:
                share = 1
            targets[key] = min(share, pop)

        # Adjust to match n_target (rounding may produce ±k off)
        diff = n_target - sum(targets.values())
        if diff != 0:
            keys_by_pop = sorted(sorted_keys, key=lambda k: -len(groups[k]))
            i = 0
            while diff != 0 and i < len(keys_by_pop) * 2:
                k = keys_by_pop[i % len(keys_by_pop)]
                if diff > 0 and targets[k] < len(groups[k]):
                    targets[k] += 1
                    diff -= 1
                elif diff < 0 and targets[k] > 1:
                    targets[k] -= 1
                    diff += 1
                i += 1

        rng = random.Random(request.seed)
        sampled = []
        for key in sorted_keys:
            group_rows = groups[key]
            n_take = targets[key]
            if n_take >= len(group_rows):
                sampled.extend(group_rows)
            else:
                indices = sorted(rng.sample(range(len(group_rows)), n_take))
                sampled.extend(group_rows[i] for i in indices)

        result[name] = sampled
        summary = ", ".join(f"{k}:{targets[k]}/{len(groups[k])}" for k in sorted_keys)
        trace.append(
            f"stratify: {name} by '{col}' PROPORTIONAL "
            f"({n_groups} groups, {len(sampled)}/{n_total}): {summary}"
        )

    return result


register_strategy("stratify", _apply)
