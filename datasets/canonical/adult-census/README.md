# Adult Census Income — UCI ML Repository

Single-table canonical dataset used in TCF M-series experiments
(F-Q25..F-Q32 in [docs/findings/](../../../docs/findings/)).

## Source

- **Name**: Adult, also known as "Census Income"
- **Origin**: US Census Bureau, 1994 extract
- **Curators**: Ronny Kohavi & Barry Becker (Silicon Graphics)
- **License**: public domain (US gov)
- **Citation**: Kohavi, R. (1996). "Scaling Up the Accuracy of Naive-Bayes
  Classifiers: a Decision-Tree Hybrid". KDD-96.
- **URL**: https://archive.ics.uci.edu/ml/datasets/adult

## Schema

15 columns × 48,842 rows (32,561 train + 16,281 test, merged here):

| Column | Type | Notes |
|--------|------|-------|
| age | INTEGER | 17-90 |
| workclass | TEXT | 9 categories incl. "?" (~6% null) |
| fnlwgt | INTEGER | sampling weight (US Census methodology) |
| education | TEXT | 16 ordinal categories |
| education-num | INTEGER | 1-16 |
| marital-status | TEXT | 7 categories |
| occupation | TEXT | 15 categories incl. "?" |
| relationship | TEXT | 6 categories |
| race | TEXT | 5 categories |
| sex | TEXT | Male / Female |
| capital-gain | INTEGER | mostly 0; max 99,999 |
| capital-loss | INTEGER | mostly 0 |
| **hours-per-week** | INTEGER | hyphenated — requires `"hours-per-week"` quoting in SQLite |
| native-country | TEXT | 42 countries incl. "?" |
| **class** | TEXT | `<=50K` (76%) / `>50K` (24%) — target |

## How to download

```bash
# Run from repo root
python scripts/setup_adult.py
```

This downloads `adult.data` and `adult.test` from UCI, merges, cleans
trailing whitespace, and writes to:

```
$TCF_DATA_ROOT/external/adult-census/adult.csv
```

`$TCF_DATA_ROOT` defaults to `Z:/tcf-data/` on Windows; configurable via
`config/storage.json`. See
[../../../docs/theory/architecture/storage.md](../../../docs/theory/architecture/storage.md).

## Build SQLite

```bash
python scripts/csv_to_sqlite.py adult-census
```

Creates `$TCF_DATA_ROOT/interim/adult-census.db` with PK + FK + types
declared per `metadata.json`.

## Use in experiments

```python
from experiments.eval.data_sources import load_dataset

tables, meta = load_dataset(
    "canonical:adult-census",
    volume=100, seed=42,
    stratify_by="class",  # preserves 76/24 ratio
)
# meta["_stratification_metrics"] has TVD/JSD/Hellinger/Wilson CI
```

## Caveats

- **`?` values** are textual nulls — code that uses `distinct_workclass`
  must explicitly exclude them (`WHERE workclass != '?'`)
- **`hours-per-week`, `marital-status`, etc.** require double-quoting
  in SQLite. Some local models (qwen2.5-coder:7b) consistently fail
  this — see manual [07-troubleshooting](../../../docs/manual/07-troubleshooting.md).
- **Train + test merged**: we treat the full 48,842 as our population.
  Use `stratify_by="class"` for fair sampling.
