"""FK-preserving volume strategy — multi-table sampling with referential integrity.

The default `volume` strategy samples N rows from each table independently,
which breaks FK integrity in multi-table scenarios: sampled fact rows may
reference dim rows that were NOT sampled.

This strategy instead:
  1. Samples N rows from the fact table (the one with FKs pointing out)
     - Random by default
     - Stratified by `request.stratify_by` if column exists in fact
  2. Filters dim tables to keep only rows referenced by the sampled fact rows
  3. Cascades recursively if dims have FKs to other dims

Runs at the same pipeline position as `volume`. Activated when
`request.fk_preserving=True`; otherwise no-op. The `volume` and `stratify`
strategies skip when FK-preserving is active (exclusive).

Fact table detection:
  - If `request.fact_table` is set: use it
  - Otherwise: pick the table with the most outgoing FKs (heuristic)

Stratified sampling on fact:
  - If `request.stratify_by` is set and column exists in fact, samples
    proportionally across distinct values of that column (≥1 per group).
  - Falls back to random sampling with trace warning if column is missing.

Requires metadata.json with `tables[name].fk` to know which columns are FKs.
"""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Any

from ..pipeline import register_strategy
from .._stratify_metrics import compute_stratification_metrics, format_metrics_summary


def _stratified_sample_indices(rows, stratify_col, n_target, seed, trace, table_name):
    """Return sorted indices for a stratified sample of `n_target` rows from `rows`.

    Uses **proportional allocation** (Neyman-style): each group's contribution
    to the sample is proportional to its share of the population. Maintains
    "general representativeness" of the original distribution.

    Edge cases:
      - Group with 0 expected rows after rounding: still gets 1 row if possible
        (so all groups appear in the sample, preserving categorical coverage)
      - Rounding shortfall/surplus: distributed to largest groups in the
        population (preserves their dominance)
    """
    if stratify_col not in rows[0]:
        trace.append(
            f"fk_preserving: stratify_by='{stratify_col}' not in fact "
            f"'{table_name}', falling back to random sampling"
        )
        rng = random.Random(seed)
        return sorted(rng.sample(range(len(rows)), n_target))

    groups: dict[Any, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        groups[row[stratify_col]].append(i)

    total_pop = len(rows)
    sorted_keys = sorted(groups.keys(), key=lambda k: (k is None, str(k)))

    # Proportional allocation with min-1 per group
    targets: dict = {}
    for key in sorted_keys:
        pop = len(groups[key])
        share = round(n_target * pop / total_pop)
        # Min 1 per group if we have budget; min 0 only if any non-empty group must drop
        if share == 0 and pop > 0:
            share = 1
        targets[key] = min(share, pop)

    # Adjust to match n_target (rounding may produce ±k off)
    current_sum = sum(targets.values())
    diff = n_target - current_sum

    if diff != 0:
        # Sort groups by population descending: largest groups absorb adjustments
        keys_by_pop = sorted(sorted_keys, key=lambda k: -len(groups[k]))
        idx = 0
        while diff != 0 and idx < len(keys_by_pop) * 2:
            k = keys_by_pop[idx % len(keys_by_pop)]
            if diff > 0 and targets[k] < len(groups[k]):
                targets[k] += 1
                diff -= 1
            elif diff < 0 and targets[k] > 1:
                targets[k] -= 1
                diff += 1
            idx += 1

    rng = random.Random(seed)
    indices = []
    for key in sorted_keys:
        group_idx = groups[key]
        n_take = targets[key]
        if n_take >= len(group_idx):
            indices.extend(group_idx)
        else:
            indices.extend(rng.sample(group_idx, n_take))
    indices.sort()

    summary = ", ".join(f"{k}:{targets[k]}/{len(groups[k])}" for k in sorted_keys)
    trace.append(
        f"fk_preserving: fact '{table_name}' stratified PROPORTIONAL by "
        f"'{stratify_col}' ({len(sorted_keys)} groups, {len(indices)} rows): {summary}"
    )

    # Compute and log representativeness metrics
    pop_counts = {k: len(groups[k]) for k in sorted_keys}
    sample_counts = {k: targets[k] for k in sorted_keys}
    metrics = compute_stratification_metrics(pop_counts, sample_counts)
    trace.append(f"stratify_metrics: {format_metrics_summary(metrics)}")
    # Structured payload for programmatic extraction
    import json as _json
    trace.append(f"METRICS_JSON: {_json.dumps({'stratify_by': stratify_col, 'table': table_name, **metrics})}")

    return indices


def _detect_fact_table(tables: dict, meta: dict) -> str | None:
    """Heuristic: table with the most outgoing FKs is the fact."""
    tables_meta = meta.get("tables", {})
    best_name = None
    best_fk_count = -1
    for name in tables:
        fk_count = len(tables_meta.get(name, {}).get("fk", {}))
        if fk_count > best_fk_count:
            best_fk_count = fk_count
            best_name = name
    return best_name


def _apply(reader, tables, request, trace):
    if not getattr(request, "fk_preserving", False):
        return tables

    meta = reader.metadata
    tables_meta = meta.get("tables", {})

    # Determine fact table
    fact_name = getattr(request, "fact_table", None) or _detect_fact_table(tables, meta)
    if fact_name is None or fact_name not in tables:
        trace.append(f"fk_preserving: SKIP (fact table not found in {list(tables.keys())})")
        return tables

    fact_rows = tables[fact_name]
    fact_meta = tables_meta.get(fact_name, {})
    fk_map = fact_meta.get("fk", {})

    if not fk_map:
        trace.append(f"fk_preserving: fact={fact_name} has no FKs; single-table sampling")
        vol = request.volume
        if vol is None or vol >= len(fact_rows):
            return tables
        n_target = int(vol) if isinstance(vol, int) else max(0, int(round(len(fact_rows) * vol)))
        n_target = min(n_target, len(fact_rows))

        stratify_col = getattr(request, "stratify_by", None)
        if stratify_col:
            idx = _stratified_sample_indices(
                fact_rows, stratify_col, n_target, request.seed, trace, fact_name
            )
        else:
            rng = random.Random(request.seed)
            idx = sorted(rng.sample(range(len(fact_rows)), n_target))
            trace.append(
                f"fk_preserving: {fact_name} -> {len(idx)} of {len(fact_rows)} rows "
                f"random (seed={request.seed})"
            )
        tables[fact_name] = [fact_rows[i] for i in idx]
        return tables

    # Step 1: sample fact table (random or stratified)
    vol = request.volume
    if vol is None or vol >= len(fact_rows):
        sampled_fact = fact_rows
        trace.append(f"fk_preserving: fact={fact_name} no volume filter ({len(fact_rows)} rows)")
    else:
        n_target = int(vol) if isinstance(vol, int) else max(0, int(round(len(fact_rows) * vol)))
        n_target = min(n_target, len(fact_rows))

        stratify_col = getattr(request, "stratify_by", None)
        if stratify_col:
            idx = _stratified_sample_indices(
                fact_rows, stratify_col, n_target, request.seed, trace, fact_name
            )
        else:
            rng = random.Random(request.seed)
            idx = sorted(rng.sample(range(len(fact_rows)), n_target))
            trace.append(
                f"fk_preserving: fact={fact_name} sampled {n_target} of {len(fact_rows)} rows "
                f"random (seed={request.seed})"
            )
        sampled_fact = [fact_rows[i] for i in idx]

    # Step 2: filter each dim to FKs referenced in sampled fact
    # fk_map: {"ps_partkey": "part.p_partkey", "ps_suppkey": "supplier.s_suppkey"}
    result = dict(tables)
    result[fact_name] = sampled_fact

    for fk_col, ref in fk_map.items():
        ref_table, ref_col = ref.split(".")
        if ref_table not in tables:
            trace.append(f"fk_preserving: WARN ref table {ref_table} not in tables, skipping filter")
            continue
        referenced_values = {r[fk_col] for r in sampled_fact if r[fk_col] is not None}
        dim_before = len(tables[ref_table])
        filtered_dim = [r for r in tables[ref_table] if r[ref_col] in referenced_values]
        result[ref_table] = filtered_dim
        trace.append(
            f"fk_preserving: {ref_table} filtered {len(filtered_dim)} of {dim_before} rows "
            f"(keep FK {fk_col} -> {ref_table}.{ref_col})"
        )

    # Step 3: cascade — if any dim has outgoing FKs, filter those too
    # (handles chain topologies like customer -> nation -> region)
    changed = True
    max_depth = 10
    depth = 0
    while changed and depth < max_depth:
        changed = False
        depth += 1
        for name in list(result.keys()):
            name_meta = tables_meta.get(name, {})
            name_fks = name_meta.get("fk", {})
            if not name_fks or name == fact_name:
                continue
            for fk_col, ref in name_fks.items():
                ref_table, ref_col = ref.split(".")
                if ref_table not in result:
                    continue
                referenced_values = {r[fk_col] for r in result[name] if r[fk_col] is not None}
                dim_before = len(result[ref_table])
                filtered = [r for r in result[ref_table] if r[ref_col] in referenced_values]
                if len(filtered) < dim_before:
                    result[ref_table] = filtered
                    changed = True
                    trace.append(
                        f"fk_preserving[cascade d={depth}]: {ref_table} {len(filtered)}/{dim_before} "
                        f"(keep FK {name}.{fk_col} -> {ref_table}.{ref_col})"
                    )

    return result


register_strategy("fk_preserving", _apply)
