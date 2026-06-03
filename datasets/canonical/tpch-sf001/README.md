# TPC-H sf001 — Industry-standard relational benchmark

Multi-table canonical dataset used in TCF M-series experiments
(F-Q24, F-Q33..F-Q38).

## Source

- **Name**: TPC-H (Transaction Processing Council Benchmark H)
- **Scale factor**: sf001 (~1 MB raw; ~17,000 rows on largest table
  `lineitem` with our sampling)
- **Generator**: DuckDB `tpch` extension (no licensing for research)
- **License**: TPC fair-use for benchmarking
- **Spec**: https://www.tpc.org/tpch/

## Schema (full 8 tables)

| Table | Rows (sf001) | Role |
|-------|--------------|------|
| region | 5 | dim |
| nation | 25 | dim |
| supplier | 100 | dim |
| customer | 1,500 | dim |
| part | 2,000 | dim |
| partsupp | 8,000 | fact |
| orders | 15,000 | fact |
| lineitem | 60,175 | fact (largest) |

FKs follow the standard star/snowflake topology. See
`metadata.json` for the full FK map.

## How to generate

```bash
# Run from repo root (requires duckdb pip package)
python scripts/setup_tpch.py
```

This:
1. Spins up an in-memory DuckDB
2. Calls `INSTALL tpch; LOAD tpch; CALL dbgen(sf=0.01);`
3. Exports each of the 8 tables to CSV under
   `$TCF_DATA_ROOT/external/tpch-sf001/`

`$TCF_DATA_ROOT` defaults to `Z:/tcf-data/`. Configure via
`config/storage.json`.

## Build SQLite

```bash
python scripts/csv_to_sqlite.py tpch-sf001
```

Creates `$TCF_DATA_ROOT/interim/tpch-sf001.db` with all PK/FK declared.

## Use in experiments

```python
from llm_benchmark.eval.data_sources import load_dataset  # (v0.5 harness; movido p/ llm-benchmark/)

# 100-row sample on the partsupp fact, FK-preserving on supplier+part
tables, meta = load_dataset(
    "canonical:tpch-sf001",
    volume=100, seed=42,
    schema=["partsupp", "part", "supplier"],
    fact_table="partsupp",
)
```

`schema` can be:
- `["partsupp"]` — minimal (1 table)
- `["partsupp", "part"]` — core (2 tables)
- `["partsupp", "part", "supplier"]` — chain (3 tables, M9 baseline)
- `["region", "nation", "supplier", "customer", "part", "partsupp",
   "orders", "lineitem"]` — full (8 tables)

These 4 levels are the M-schema-scope axis (F-Q37, F-Q38).

## Schema ambiguity warning

TPC-H has multiple `$` columns that LLM may confuse for natural-language
wordings (F-Q33-F-Q38):
- `ps_supplycost` (partsupp) — what suppliers charge us
- `p_retailprice` (part) — list price
- `l_extendedprice` (lineitem) — line-item value
- `o_totalprice` (orders) — order total

For wordings like *"the most expensive item"*, **N0 (schema-aware,
mentioning `ps_supplycost`) is mandatory** — N2/N3 wordings drop to
0% accuracy across all commercial top models. See
[../../../docs/findings/05-schema-scope-Q37-Q38.md](../../../docs/findings/05-schema-scope-Q37-Q38.md).

## Memorization caveat

Most major LLMs trained pre-2026 know TPC-H by heart. They infer
`Supplier#NNNNNNNNN` patterns even when the `supplier` table isn't
in the payload (F-Q37 sub-finding). For methodologically clean
results on a non-canonical dataset, prefer Adult Census or your own
data.
