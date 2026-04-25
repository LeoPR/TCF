"""FK-preserving volume strategy — multi-table sampling with referential integrity.

The default `volume` strategy samples N rows from each table independently,
which breaks FK integrity in multi-table scenarios: sampled fact rows may
reference dim rows that were NOT sampled.

This strategy instead:
  1. Samples N rows from the fact table (the one with FKs pointing out)
  2. Filters dim tables to keep only rows referenced by the sampled fact rows
  3. Cascades recursively if dims have FKs to other dims

Runs at the same pipeline position as `volume`. Activated when
`request.fk_preserving=True`; otherwise no-op. The `volume` strategy
checks the same flag and skips when FK-preserving is active (exclusive).

Fact table detection:
  - If `request.fact_table` is set: use it
  - Otherwise: pick the table with the most outgoing FKs (heuristic)

Requires metadata.json with `tables[name].fk` to know which columns are FKs.
"""
from __future__ import annotations

import random
from typing import Any

from ..pipeline import register_strategy


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
        trace.append(f"fk_preserving: fact={fact_name} has no FKs; falling back to single-table volume")
        vol = request.volume
        if vol is None or vol >= len(fact_rows):
            return tables
        rng = random.Random(request.seed)
        idx = sorted(rng.sample(range(len(fact_rows)), int(vol)))
        tables[fact_name] = [fact_rows[i] for i in idx]
        trace.append(f"fk_preserving: {fact_name} -> {len(idx)} of {len(fact_rows)} rows (seed={request.seed})")
        return tables

    # Step 1: sample fact table
    vol = request.volume
    if vol is None or vol >= len(fact_rows):
        sampled_fact = fact_rows
        trace.append(f"fk_preserving: fact={fact_name} no volume filter ({len(fact_rows)} rows)")
    else:
        rng = random.Random(request.seed)
        n_target = int(vol) if isinstance(vol, int) else max(0, int(round(len(fact_rows) * vol)))
        n_target = min(n_target, len(fact_rows))
        idx = sorted(rng.sample(range(len(fact_rows)), n_target))
        sampled_fact = [fact_rows[i] for i in idx]
        trace.append(
            f"fk_preserving: fact={fact_name} sampled {n_target} of {len(fact_rows)} rows (seed={request.seed})"
        )

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
