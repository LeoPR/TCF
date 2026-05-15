# 03 — Compression levels

TCF has 4 levels (`L0`..`L3`) that trade compactness for readability and
information loss.

| Level | Includes | Round-trip? | Typical size vs CSV |
|-------|----------|-------------|---------------------|
| L0 | Header + columns expanded | ✅ exact | 1.0× (no compression) |
| L1 | + DICT for repeated strings | ✅ exact | 0.7-0.9× |
| L2 | + RLE (`N*val`) for runs | ✅ exact | 0.4-0.6× |
| L3 | Schema-only, no data | ❌ schema | 0.05-0.10× |

## When to use each

### L0 — Debugging / inspection

```python
EncodeConfig(level=0, include_stats=False)
```

Plain expanded view. Use when round-trip + readability matter more than
size. Identical info content to CSV.

### L1 — General purpose

```python
EncodeConfig(level=1, include_stats=True)
```

Adds dictionary compression for high-cardinality string columns. Best
when you have many repeated values but not contiguous runs.

### L2 — Default for LLM input

```python
EncodeConfig(level=2, include_stats=True)
```

**Recommended for LLM Linha A** (LLM reads data and computes). Adds RLE
for runs of consecutive equal values — typically reduces 100-row Adult
Census from ~9 KB CSV to ~7 KB TCF L2.

Best paired with `sort_by="<low-cardinality-col>"` to maximize RLE
compression:

```python
EncodeConfig(level=2, include_stats=True, sort_by="sex")
```

### L3 — Schema only (Linha B)

```python
EncodeConfig(level=3, include_stats=True)
```

Drops all rows; outputs only schema + STATS. Use this for **Linha B**
(LLM generates SQL, SQLite executes) — gives the model the schema
shape without leaking row content. Smallest payload by far.

## What `include_stats=True` does

Adds a `# STATS col: n=N sum=S min=A max=B avg=M` line per numeric
column (`avg=...` for numerics, `cardinality=K samples=[...]` for
strings). Adds ~30-80 bytes per column but **massively** improves LLM
accuracy on aggregation questions — see
[../findings/01-origins-Q01-Q12.md](../findings/01-origins-Q01-Q12.md)
F-Q8 "STATS hint vs no-STATS".

## Compression vs accuracy data

From M-Acomm experiments (Adult Census, vol=100):

| Format | Bytes | gpt-5.4-nano accuracy (Linha A, N0) |
|--------|-------|-------------------------------------|
| CSV | ~9000 | not tested |
| JSON | ~14000 | not tested |
| TCF L0 | ~9000 | comparable to CSV |
| **TCF L2** | **~7188** | **86.9%** (cached: $0.0007/call) |
| TCF L3 (schema-only, Linha B) | ~470 | **90.5%** with SQL execution |

## Choosing the right level

```
       Want round-trip?
        |     |
       Yes    No
        |     |
        v     v
       L0-2  L3 (schema-only Linha B)
        |
   Need RLE?  ──── No: L0 or L1
        | Yes
        v
       L2 (default)
```

## Sort_by tip

For maximum RLE compression in L2:
- Identify the column with **lowest cardinality** that doesn't break
  meaning
- Sort rows by it before encoding

Example: Adult Census has `class` with 2 values (`<=50K`, `>50K`) and
75/25 distribution. Sorting by `class` creates a single `~75*<=50K`
run instead of scattered values.

```python
encode_rows("adult", rows, config=EncodeConfig(level=2, sort_by="class"))
```
