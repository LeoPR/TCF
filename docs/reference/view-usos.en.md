<!-- l10n: doc_id=view-usos · lang=en · canonical -->
**English** · [Português](view-usos.pt-BR.md)

# What you can ask a TCF blob

Usage map for [`tcf.view`](../../src/tcf/view.py): the questions it answers, what each one
costs, and where the limits are. The API reference is in [`lazy-view.md`](lazy-view.md);
here the cut is by **question**, not by method.

Every number on this page comes from
`experiments/lab/.../2026-08-24-0800-view-capacidades/`, measured at n=1000 and checked
against `decode()` cell by cell.

## The idea in one line

The TCF header already states, per column, the name, the mode and the size. The view uses
that information opportunistically: it answers from the header or compact structure when
that is sufficient, and only then advances to indices, selected positions, a full column
or a correctness fallback. In dictionary mode it can often answer from K uniques and the
index stream without building the N values.

The route changes cost, not meaning. Every shortcut must agree with the materialized
answer; an unproven shortcut is deferred to a lab rather than guessed. The complete rule is
in the [API reference](lazy-view.md#governing-principle-opportunistic-in-cost).

```python
from tcf import encode, view

blob = encode({"uf": ["SP", "SP", "RJ"], "valor": [120, 80, 200]})
v = view(blob)                         # connects: decompresses nothing
v.count()                              # 3, materializing no value at all
v.where("uf", "SP").sum("valor")       # 200.0, touching only uf and valor
```

## The questions, cheapest first

### How many rows? (`count`, `nrows`)

**Cost: 0.0% to 0.4% of the wire**, with one exception. Counting does not need the values,
and the structure already states them: dense routes write the number in the header as hex;
the core body carries counters (`*N|`) declaring how many rows each one stands for; the raw
body is one line per value; and in the dictionary the number is `len(stream) // width`.

In those cases no value object is built, and after a plain `count()`,
`report()["materialized_bytes"]` is 0.

`count` is row cardinality, not a count of non-empty payloads. An empty string is a real
value and occupies one row:

```python
v = view(encode(["", "a", ""]))
v.count()                  # 3
v.where(0, "").count()     # 2
v.n_unique(0)              # 2: "" and "a"
```

The boundary case `view(encode([""])).count() == 1` is the semantic contract. The current
implementation violates that contract and is tracked in
[`BUG-VIEW-UMA-STRING-VAZIA`](../../tickets/BUG-VIEW-UMA-STRING-VAZIA.md). The distinction
between counting rows, non-null values and empty strings across TCF, NumPy, pandas, Polars
and SQL is shown in [`mimetizar-pandas-sql-polars.md`](../how-to/mimetizar-pandas-sql-polars.md).

**The exception is `split` mode**, which declares the count nowhere. One column in another
mode is enough for `count` to stay cheap, because every column has the same number of rows
and it uses the cheapest one. But in a table where *every* column is `split`, there is
nothing to read from, and `count` decodes the smallest column: measured, 49.7% on a
two-column table.

### Which columns exist, and how big are they? (`columns`, `column_bytes`, `report`)

**Cost: 0%.** It all comes from the header.

`column_bytes` gives the **compressed** size of the column, useful for deciding what to
query before querying. `report()` shows how much has been materialized, and serves to check
whether a query was as selective as expected.

### Which rows match? (`where`)

| column mode | cost |
|---|---:|
| dictionary (`@`) | **0.4%** |
| raw (`!`) | 26.1% |
| core | 39.7% |
| split (`%`) | 95.4% |
| single column | 100% |

In the dictionary the filter compares the value against the K uniques and scans a stream of
indices, without decoding the N rows. In the other modes the column is materialized,
because there is no way to know a row's value without rebuilding it.

Two cases never even scan the stream: when **no** unique matches the answer is empty, and
when **all** match the answer is every row. The unique table is the closed list of what the
column holds, so it settles both ends by itself.

The filter takes equality (`where(col, value)`) or a predicate
(`where(col, pred=lambda x: ...)`), and chaining is AND:

```python
v.where("uf", "SP").where("plano", "Premium").sum("valor")
```

### What is the total, the minimum, the maximum? (`sum`, `min`, `max`, `avg`)

**Cost: 1.6% to 48.6%,** depending on the mode of the **numeric** column (not the filter's
column). Empty values are ignored; a non-numeric value raises, on purpose, so dirty data is
not silenced.

### Which values does this column hold? (`distinct`, `n_unique`)

`SELECT DISTINCT` and `COUNT(DISTINCT col)`. In a dictionary column both come off the
unique table the body already carries, in O(K):

```python
v.distinct("uf")      # ['SP', 'RJ', 'MG'], in order of appearance
v.n_unique("uf")      # 3
```

The two cost different things, and it is worth knowing: `n_unique` only needs the **size**
of that table, so it builds no value at all and `report()` stays at zero. `distinct` builds
the K uniques, because that is what it returns. The K, not the N: in a 600-row column with
3 distinct values, three.

Both take a list of columns and work after a `where`, like the rest of the family.

### How many per value? (`group_count`)

| mode | cost |
|---|---:|
| dictionary | **0.4%** |
| raw | 26.1% |
| core | 39.7% |
| split | 95.4% |

In the dictionary the per-group count comes from tallying the stream's indices, without
expanding the rows. In the other modes it falls back to decoding the column and counting.

### Sum, minimum, maximum, average per group? (`group_sum`, `group_min`, `group_max`, `group_avg`)

**Cost: 52% to 97%, the most expensive on the surface.** It materializes the columns
involved and crosses them row by row, without using the structure of either.

```python
v.group_sum("uf", "valor")            # {'SP': 200.0, 'RJ': 200.0}
v.group_avg("uf", "valor")            # average per group
v.group_sum(["uf", "plano"], "valor") # GROUP BY uf, plano: the key becomes a tuple
```

**A null key forms a group**, as in SQL and polars. Pandas drops it by default
(`dropna=True`), and there is deliberately no equivalent flag here: dropping the null is a
filter, and the filter already exists.

```python
v.group_count("uf")                                        # the null shows up
v.where("uf", pred=lambda x: x is not None).group_count("uf")   # the "dropna"
```

Writing the filter keeps what is being thrown away in plain sight, and a flag would hide
that behind a piece of semantics. In a dictionary column the predicate still runs over the K
uniques, not the N rows, so the explicit form costs no more: measured, three evaluations for
600 rows.

A group with no usable value at all (every value null or empty) sums to `0.0`, because the
sum of the empty set is zero, and that is a definition rather than a convention. But `min`,
`max` and `avg` return `None` there, because there is no answer: the minimum of no values
does not exist, and returning `0.0` would invent a number the column does not hold. The
group shows up in both cases instead of vanishing, so the key being there is not hidden.

`group_sum` alone does not distinguish a group that really summed to zero from one with no
values, but the information is not lost: `group_min` returns `0.0` for the first and `None`
for the second. To get SQL's `NULL`, and the behaviour of the other tools in general, see
[how to match pandas, SQL and polars](../how-to/mimetizar-pandas-sql-polars.md).

### Filter and group (`where(...).group_*`)

The `WHERE … GROUP BY`. The aggregation runs on the rows that matched:

```python
v.where("plano", "A").group_sum("uf", "valor")
v.where("plano", "A").group_count("uf")
```

### The rows themselves (`select`)

**Cost: proportional to what you ask for,** and here that is not waste: `select` returns
the values, so materializing the column *is* the work. The number that matters is the
comparison: in the dictionary, `select` of one column costs 49.1% and of all of them 99.1%.

```python
v.select("uf")                 # only the uf column
v.select(["uf", "valor"])      # two
v.select()                     # all of them, equivalent to decode()
```

## How to name a column

Across the whole surface: `str` is a **name**, `int` is a **position**. Same rule as
`schema=` ([ADR-0047](../adr/0047-schema-parametro-unico-de-spec.md)). A column *called*
`"2"` is found by the `str`; position 2, by the `int`.

## What the view does not do

**It does not write.** No operation changes the blob.

**It is not SQL.** There is no parser, no joins, no `ORDER BY`, no `LIMIT`, no computed
expressions and no multi-table plan. What exists are query paths that resemble SQL. `OR`
does not exist **between** columns, because chaining `where` is always AND, but within one
column the predicate expresses OR:
`where("uf", pred=lambda x: x in ("SP", "RJ"))`.

**It does not read what is not a table.** Nested, ragged and optional fields are not a
rectangular table, and the view refuses with a message telling you to use `decode()`. Null
is not absence: `encode([{"a": 1}, {"a": None}])` is a table (the column exists in every
row) and the view reads it, since 2026-08-28, with the same answers as the equivalent
`.8M` table.

**It does not read legacy formats.** `#TCF.6` and `#TCF.7` were cut
([ADR-0032](../adr/0032-tcf8-default-format.md)); for older blobs, `git checkout` an earlier
version.

## What the structure would allow, and does not yet do

This is not a release promise, it is the map of what has been measured as possible. The full
record, including what was **refuted**, lives in the labs of 2026-08-24.

The obvious paths already closed in the current surface are header introspection, structural
row count, dictionary `distinct`/`n_unique`/`group_count`, no-match/all-match filter
extremes, and column pruning. In `0.8.x`, the remaining obvious work is correctness such as
the single-empty-string count, not a new query planner.

| opportunity | how | evidence | classification |
|---|---|---|---|
| `group_*` from the structure, without materializing | cross the two columns' index streams without building any row value | prototype measured: 71.8% fewer bytes | direct `.9` optimization; preserve null/empty semantics |
| `sum`/`min`/`max`/`avg` over a dictionary | aggregate the K uniques weighted by frequency | measured: 99.6% fewer bytes; `min`/`max` are exact by construction | direct `.9` candidate; filtered and typed cases still gate it |
| answering "does any row match?" without building the index list | defer index construction inside the `where` result | not implemented | latent-result design; lab before API |
| emit a filtered/projected child TCF | slice raw, dictionary and split bodies; fallback for core | `.8M` mechanism and differential oracle proven | `.9` API; [`T-CODE-VIEW-SUBTCF-RECORTE`](../../tickets/T-CODE-VIEW-SUBTCF-RECORTE.md) |

And what is **not** possible, for structural reasons rather than for lack of work:

- **Resolving a row's value in the core body without replay.** Fragment ids do not travel on
  the wire; encoder and decoder keep mirrored counters. Skipping a declaration returns the
  wrong value **with no error**.
- **Prefiltering by substring in the core body.** OBAT fragments the value, so the escaped
  form of a value that is present is not a substring of the body: it gives false negatives.
- **`min`/`max` in the dense bit-pack.** The domain is ordered by first appearance, not by
  value.

## Stability

The L1 to L4 surface (introspection, aggregators, `where`, `select`) is **stable**.
`group_ranges` and `agg_by` are **experimental** and may evolve in `.9`; both require the
table already sorted by `sort_by` and raise if it is not.

## See also

- API reference: [`lazy-view.md`](lazy-view.md)
- Encode knobs (`fallback`, `sort_by`): [`encode-knobs.md`](encode-knobs.md)
- Format and modes: [`../algorithms/TCF-format.md`](../algorithms/TCF-format.md)
