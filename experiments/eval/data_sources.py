"""Data manager — single entry point for loading experiment data.

The orchestrator-level adapter between experiments and data sources.
Experiments call `load_dataset("canonical:tpch-sf001", ...)` instead of
importing synthetic fixtures or DatasetReader directly.

Architectural principle (see docs/components/1-tcf-core.md):
  - TCF Core is naive; it receives dict[table, list[dict]] and encodes
  - This module (the orchestrator) calls Shaper/fixtures and hands result to TCF
  - TCF never sees Shaper or DatasetReader

Supported source schemes:
  canonical:<name>    → Shaper with FK-preserving sampling on Pipeline B
                        kwargs: volume (int), seed (int), schema (list[str]),
                                fact_table (str)
  synthetic:<name>    → wraps tests/fixtures generators
                        kwargs: n_orders (int), seed (int)
                        names: retail_sales, medical_consultations, financial_transactions

Returns (tables, meta) tuple compatible with existing M-series runners:
  tables: dict[table_name, list[row_dict]]
  meta:   dict (domain-specific — synthetic has different shape than canonical)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


# ---------------------------------------------------------------------------
# Canonical loaders (Shaper-based, Pipeline B)
# ---------------------------------------------------------------------------

# Pre-configured dataset profiles for canonical datasets.
# Maps a canonical dataset name to its fact_table + default schema list for
# the 3-table star topology analog used in M-series runners.
CANONICAL_PROFILES: dict[str, dict] = {
    "tpch-sf001": {
        "schema": ["partsupp", "part", "supplier"],
        "fact_table": "partsupp",
    },
    "adult-census": {
        "schema": ["adult"],
        "fact_table": "adult",  # single-table; fk_preserving is no-op but safe
    },
}


def _load_canonical(
    name: str,
    volume: int = 100,
    seed: int = 42,
    schema: list[str] | None = None,
    fact_table: str | None = None,
) -> tuple[dict, dict]:
    """Load canonical dataset via Shaper with FK-preserving sampling."""
    from shaper import Shaper, ShapeRequest

    profile = CANONICAL_PROFILES.get(name, {})
    effective_schema = schema or profile.get("schema", "full")
    effective_fact = fact_table or profile.get("fact_table")

    req = ShapeRequest(
        dataset=name,
        schema=effective_schema,
        volume=volume,
        seed=seed,
        fk_preserving=bool(effective_fact),
        fact_table=effective_fact,
    )
    result = Shaper().apply(req)
    return result.tables, result.metadata


# ---------------------------------------------------------------------------
# Synthetic loaders (fixture-based, Pipeline A — legacy compat)
# ---------------------------------------------------------------------------

def _load_synthetic(name: str, n_orders: int = 100, seed: int = 42) -> tuple[dict, dict]:
    """Load synthetic dataset via fixture generators.

    Kept for backward compatibility with M1-M8 runners and for ablations
    that require controlled dimensions (N_entities, null_rate, FK topology)
    which canonical datasets do not expose.
    """
    if name == "retail_sales":
        from tests.fixtures.synthetic_v2 import retail_sales
        return retail_sales(n_orders=n_orders, seed=seed)
    if name == "medical_consultations":
        from tests.fixtures.synthetic_domains import medical_consultations
        return medical_consultations(n_orders=n_orders, seed=seed)
    if name == "financial_transactions":
        from tests.fixtures.synthetic_domains import financial_transactions
        return financial_transactions(n_orders=n_orders, seed=seed)
    raise ValueError(f"Unknown synthetic dataset: {name!r}")


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------

def load_dataset(source: str, **kwargs) -> tuple[dict, dict]:
    """Load dataset from any configured source.

    Args:
        source: "canonical:<name>" or "synthetic:<name>"
        **kwargs: forwarded to the appropriate loader
                  canonical: volume, seed, schema, fact_table
                  synthetic: n_orders, seed

    Returns:
        (tables, meta) tuple. `tables` is dict[name, list[dict]];
        `meta` is domain-specific (canonical has metadata.json shape;
        synthetic has whatever the fixture returns).

    Raises:
        ValueError: unknown scheme or dataset name
        FileNotFoundError: canonical dataset SQLite not available
    """
    if ":" not in source:
        raise ValueError(
            f"source must be 'canonical:<name>' or 'synthetic:<name>'; got {source!r}"
        )
    scheme, name = source.split(":", 1)

    if scheme == "canonical":
        return _load_canonical(name, **kwargs)
    if scheme == "synthetic":
        return _load_synthetic(name, **kwargs)
    raise ValueError(f"Unknown source scheme: {scheme!r} (expected canonical|synthetic)")


__all__ = ["load_dataset", "CANONICAL_PROFILES"]
