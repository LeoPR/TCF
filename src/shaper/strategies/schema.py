"""Schema strategy — filter tables by complexity level.

Named levels per dataset:
  minimal: smallest single table
  core:    2 tables with 1 FK relationship
  chain:   3+ tables in a FK chain
  full:    all tables
  custom:  explicit list of table names
"""

from __future__ import annotations

from typing import Any

from ..pipeline import register_strategy

# Per-dataset schema level definitions.
# Each level maps to a list of table names.
SCHEMA_LEVELS: dict[str, dict[str, list[str]]] = {
    "adult-census": {
        "minimal": ["adult"],
        "core":    ["adult"],
        "chain":   ["adult"],
        "full":    ["adult"],
    },
    "tpch-sf001": {
        "minimal": ["customer"],
        "core":    ["customer", "orders"],
        "chain":   ["customer", "orders", "lineitem"],
        "full":    ["region", "nation", "supplier", "customer",
                    "part", "partsupp", "orders", "lineitem"],
    },
}


def _apply(reader, tables, request, trace):
    schema = request.schema

    if isinstance(schema, list):
        # Custom list of tables
        keep = set(schema)
        trace.append(f"schema: custom tables {schema}")
    elif schema == "full":
        trace.append("schema: full (no filtering)")
        return tables
    else:
        # Named level
        dataset_levels = SCHEMA_LEVELS.get(request.dataset, {})
        if schema not in dataset_levels:
            trace.append(f"schema: level '{schema}' not defined for {request.dataset}, using full")
            return tables
        keep = set(dataset_levels[schema])
        trace.append(f"schema: level={schema} -> tables={sorted(keep)}")

    filtered = {name: rows for name, rows in tables.items() if name in keep}

    # Warn about requested tables not found
    missing = keep - set(tables.keys())
    if missing:
        trace.append(f"schema: WARNING tables not found: {sorted(missing)}")

    removed = set(tables.keys()) - keep
    if removed:
        trace.append(f"schema: removed tables: {sorted(removed)}")

    return filtered


register_strategy("schema_filter", _apply)
