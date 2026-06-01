# tpch-sf01 (canonical dataset)

> Metadata + small samples tracked in git. Full data lives in
> `Z:/tcf-data/external/tpch-sf01/` + hub in `Z:/tcf-data/interim/tpch-sf01.db`
> (see `config/storage.json`). Neither is committed.

TPC-H benchmark at **Scale Factor 0.1** (~10× the sibling `tpch-sf001`,
which is SF=0.01). Larger-volume multi-table relational dataset for TCF
experiments that need scale.

## Source

- **Origin**: TPC-H Benchmark — https://www.tpc.org/tpch/
- **Generator**: DuckDB `tpch` extension (`CALL dbgen(sf=0.1)`), local, no network
- **License**: TPC Fair Use Agreement (academic use permitted)
- **Download**: `python scripts/setup_tpch.py --sf 0.1`
- **Build hub**: `python scripts/csv_to_sqlite.py tpch-sf01`

## Volume (SF=0.1)

| Table | Rows |
|-------|------|
| region | 5 |
| nation | 25 |
| supplier | 1,000 |
| customer | 15,000 |
| part | 20,000 |
| partsupp | 80,000 |
| orders | 150,000 |
| lineitem | 600,572 |

Total ~866k rows. Full CSV set ~107 MB; SQLite hub ~118 MB.

## FK topology

Star + chain (verified by `csv_to_sqlite.py --verify`, 0 violations):

```
region <- nation <- supplier <- partsupp -> part
                 <- customer <- orders <- lineitem -> part
                                                   -> supplier
```

`lineitem` is the fact table (FKs to orders, part, supplier).

## Caveats

- **Shaper**: the shaper is validated only for ≤100k-row inputs
  (T-SHAPER-CODE-HARDENING A1, filter-before-load). For this dataset use
  direct `encode()` on table columns, or the schema/volume strategies on
  the smaller dimension tables — not full-`lineitem` sampling via shaper.
- Same 8-table schema as `tpch-sf001`; only the scale factor differs.
