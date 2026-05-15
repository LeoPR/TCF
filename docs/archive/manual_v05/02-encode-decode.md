# 02 — Encode / Decode API

The public API is minimal: 3 functions and 1 config dataclass.

```python
from tcf import encode, encode_rows, decode, EncodeConfig
```

## `encode_rows(table_name, rows, *, config) -> str`

Encode a single table to TCF text.

| Argument | Type | Description |
|----------|------|-------------|
| `table_name` | `str` | Logical name of the table (appears in header) |
| `rows` | `list[dict]` | List of row dicts. All rows must share keys |
| `config` | `EncodeConfig` | Compression and rendering options |

Returns a `str` with the TCF text.

## `encode(meta, data_dir, *, config) -> str`

Legacy CSV-based encoder. Reads CSVs from `data_dir/` according to a metadata
mapping (`{table_name: "file.csv#pk_col"}`). Used by the CLI when loading
from disk; new code should prefer `encode_rows`.

## `decode(text) -> list[dict]`

Reverse of `encode_rows`. Returns the row list. For multi-table TCF, returns
a `dict[str, list[dict]]`.

```python
text = encode_rows("people", rows, config=EncodeConfig(level=2))
restored = decode(text)
assert restored == rows  # round-trip
```

## `EncodeConfig`

```python
@dataclass
class EncodeConfig:
    level: int = 2          # compression level: 0, 1, 2, 3
    include_stats: bool = True   # add STATS hints at table top
    sort_by: str | None = None   # sort rows by a column before encoding
    rle_threshold: int = 2       # min run length to apply RLE (level >= 2)
```

See [03 — compression levels](03-compression-levels.md) for what each level
means.

## CLI

The `tcf` command exposes `encode`, `decode`, `info`:

```bash
# Encode a directory of CSVs
python -m tcf encode --meta data/metadata.json --data-dir data/ --level 2 --out out.tcf

# Decode back
python -m tcf decode out.tcf --out-dir restored/

# Inspect
python -m tcf info out.tcf
```

## Round-trip guarantees

- `decode(encode_rows(name, rows, config))` is **exactly** `rows` when:
  - `level <= 2` (level 3 is lossy schema-only; see ch. 03)
  - All values are JSON-serializable scalars (str, int, float, bool, None)
- Order of rows is preserved unless `sort_by` is set.
- Column order is preserved (Python 3.7+ dict ordering).

## Failure modes

| Error | Cause |
|-------|-------|
| `ValueError: rows must share keys` | Heterogeneous dicts in `rows` |
| `ValueError: invalid level` | Level outside 0..3 |
| `ValueError: sort_by column not found` | `sort_by` key missing from rows |
