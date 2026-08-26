<!-- l10n: doc_id=lazy-view · lang=en · canonical -->
**English** · [Português](lazy-view.pt-BR.md)

# Reference: `tcf.view` (query on demand)

`view(blob)` connects to a TCF blob and answers questions about it, decompressing only what
each question needs. It is read only: nothing here changes the blob, `encode` or `decode`.

You call `view()` once and then call methods on what it returns. Filtering returns another
object with the same methods, so filters chain.

## Governing principle: opportunistic in cost

The `view` seeks the **most complete answer from the least sufficient evidence** already
present in the wire. It starts with the cheapest safe source for that question:

1. header declarations;
2. compact structure such as counters, separators and sizes;
3. the K-value dictionary table and its fixed-width index stream;
4. only the requested columns and filtered positions;
5. a full column;
6. full materialization, only as a correctness fallback.

This is opportunism in **execution**, not in meaning. A structural path and a fallback
must return the same answer; changing a compression mode may change the cost, never the
semantics of empty values, nulls, groups or aggregates. If the structure cannot prove an
answer safely, the view decodes rather than guesses.

“Least” means the cheapest path currently demonstrated to be sufficient, not an unproven
claim of global optimality. Obvious structural paths and correctness fixes can close in
the current surface. Fusion, positional pushdown and new compact paths belong in a lab and
the `.9` optimization cycle when their lower cost still needs to be demonstrated.

**What it reads**: `#TCF.8M` (multi-column), `#TCF.8H` when it is a rectangular table, and
the single-column route in all of its forms (`#TCF.8`, `#TCF.8n`, `#TCF.8b`, `#TCF.8bB`,
`#TCF.8 :spec`, and the dense `B`/`C`). In a single column the name is `"0"`, as in any
anonymous column
([ADR-0029](../adr/0029-version-format-identification-semi-implicit.md)). `#TCF.6` and
`#TCF.7` are not accepted in the `0.8` package (historical compatibility through git).

## The whole surface on four rows

One table small enough to read, every operation on it, and the real output of each.

```python
from tcf import encode, view

table = {"uf":    ["SP", "SP", "RJ", "MG"],
         "valor": [  10,   20,   30,   40],
         "ativo": [True, False, True, True]}

blob = encode(table)          # 70 bytes
```

That blob, line by line:

```
#TCF.8M!b=uf,aN=valor,11B=ativo   header: name, mode and size per column.
                                  `N` and `B` are the type tags, one byte each.
SP                                body of `uf`: raw mode, one line per value
SP
RJ
MG*4+10|\10                       body of `valor`: core mode. `*4+10|` is a counter:
                                  4 rows, step 10, starting at 10
true                              body of `ativo`
false
*2|^1                             `*2|` repeats twice; `^1` refers back to `true`
```

Now the queries. Watch `report()["pct"]`, the fraction of the blob materialized so far:

```python
v = view(blob)                        # connects: decompresses NOTHING

v.columns                             # ['uf', 'valor', 'ativo']    pct: 0.0
v.count()                             # 4                           pct: 0.0
v.distinct("uf")                      # ['SP', 'RJ', 'MG']          pct: 28.9
v.n_unique("uf")                      # 3                           pct: 28.9
v.sum("valor")                        # 100.0                       pct: 55.3

v.where("uf", "SP").count()           # 2
v.where("uf", "SP").sum("valor")      # 30.0
v.group_count("uf")                   # {'SP': 2, 'RJ': 1, 'MG': 1}
v.group_sum("uf", "valor")            # {'SP': 30.0, 'RJ': 30.0, 'MG': 40.0}
v.select("uf")                        # [{'uf': 'SP'}, {'uf': 'SP'}, ...]
```

`columns` and `count` read only the structure, so nothing is materialized. `distinct`
brings in `uf`, `sum` brings in `valor`, and `ativo` is never touched. That is the whole
idea of the layer.

The rest of this page is one section per question, and then the details that only matter
once you hit them.

## Knowing the table

Everything here comes from the header, at no cost.

| call | returns | note |
|---|---|---|
| `v.columns` | `list[str]` | names in header order |
| `v.count()` | `int` | number of rows |
| `v.nrows` | `int` | the same number, as a property |
| `v.column_bytes(name)` | `int` | the column's **compressed** size, useful for deciding what to query before querying |
| `v.total_bytes` | `int` | sum of the bodies |
| `v.report()` | `dict` | `{total_bytes, materialized_bytes, pct, touched, n_cols}` |

`count` never materializes a value, in any mode: the structure already states the row
count. The one exception is a table where **every** column is `split`, which declares no
count anywhere; there it decodes the smallest column (measured: 49.7% on a two-column
table).

`count` is row cardinality, not a count of non-empty payloads. An empty string is one
present element; `None`/`NULL` is a separate missing-value convention. The cross-tool
recipes for counting rows, non-null values and empty strings are in
[`mimetizar-pandas-sql-polars.md`](../how-to/mimetizar-pandas-sql-polars.md). The single
empty-string boundary remains tracked in
[`BUG-VIEW-UMA-STRING-VAZIA`](../../tickets/BUG-VIEW-UMA-STRING-VAZIA.md).

## Filtering

```python
v.where("uf", "SP")                              # by equality
v.where("valor", pred=lambda x: x > 20)          # by predicate
v.where("uf", "SP").where("ativo", True)         # chained: AND
v.where("uf", None)                              # None matches null
```

`where` returns an object with the same query methods, restricted to the rows that matched.
You can count, aggregate, group, project or filter again on it.

It decompresses **only the filter's column**. On a dictionary column it compares against
the K unique values and scans a stream of indices, without decoding the N rows, and the two
extremes never even scan: when no unique matches the answer is empty, and when all match
the answer is every row.

## Aggregating

```python
v.sum("valor")                       # 100.0
v.min("valor")                       # 10.0
v.max("valor")                       # 40.0
v.avg("valor")                       # 25.0
v.where("uf", "SP").sum("valor")     # 30.0, only over the matched rows
```

Empty (`""`) and null (`None`) are ignored. A non-numeric value raises `ValueError`, on
purpose: dirty data is not silenced. With no numeric value at all, `min`/`max`/`avg` raise
and `sum` returns `0`, which is Python's `sum([])` and therefore an `int`.

## Distinct values

```python
v.distinct("uf")      # ['SP', 'RJ', 'MG'], in order of appearance
v.n_unique("uf")      # 3
```

`SELECT DISTINCT` and `COUNT(DISTINCT col)`. On a dictionary column both come off the
unique table the body already carries, in O(K). They cost different things: `n_unique` only
needs that table's size and builds no value, while `distinct` builds the K uniques, because
that is what it returns.

## Grouping

```python
v.group_count("uf")                        # {'SP': 2, 'RJ': 1, 'MG': 1}
v.group_sum("uf", "valor")                 # {'SP': 30.0, 'RJ': 30.0, 'MG': 40.0}
v.group_min("uf", "valor")                 # also group_max, group_avg

v.group_sum(["uf", "ativo"], "valor")      # GROUP BY uf, ativo: the key is a tuple
v.where("ativo", True).group_sum("uf", "valor")   # the WHERE ... GROUP BY
```

The whole family also works after a `where`, and the grouping key takes a list of columns.

Null and empty string **form a group**, as in SQL and polars, unlike the pandas default
which drops them. The key comes out in the **column's type**, so on an `N` column the keys
are numbers and on a `B` column they are booleans.

A group with no usable value at all sums to `0.0`, because the sum of the empty set is
zero. But `min`, `max` and `avg` return `None` there, because there is no answer, and
returning `0.0` would invent a value the column does not hold. The group shows up either
way instead of vanishing.

If you expect what pandas, SQL or polars would answer,
[the matching guide](../how-to/mimetizar-pandas-sql-polars.md) gives the one-liner for each.

## Getting the rows

```python
v.select("uf")                  # one column
v.select(["uf", "valor"])       # two
v.select()                      # all of them, equivalent to decode()
v.where("uf", "SP").select()    # only the matched rows
```

Rows come back aligned as dicts: the i-th position of every column is row `i`, which is how
a filter on one column can aggregate another. Here materializing the column **is** the
work, not overhead, because `select` returns the values. A scalar (`str` or `int`) means one
column; `[]` means none.

---

The sections below are details. They matter when you hit them, not before.

## Naming a column

`str` is a **name**, `int` is a **position**. Same rule as `schema=`
([ADR-0047](../adr/0047-schema-parametro-unico-de-spec.md): `0 <= pos < n`, no negatives).
A column *called* `"2"` is found by the `str`; position 2, by the `int`.

## Types, and comparing against them

The table declares each column's type in the header (one letter: `N` number, `B` bool,
absent = text), and values come back in the type they went in as. So you compare with that
type:

```python
v.where("valor", 30).count()     # 1   int, because the column is `N`
v.where("ativo", True).count()   # 3   bool, because the column is `B`
```

A typed column does **not** push the table out of `.8M`: the type costs a 1-byte tag in the
header.

### Soft by default, strict when you want it

The file is always text, and the type is the reading the header declares. So
`where(col, "true")` on a boolean column is a clear intent, not an error: the filter value
is read in the column's type, and the conversion is recorded in `v.coercoes`.

```python
blob = encode({"ativo": [True, False, True], "n": [1, 2, 3]})

view(blob).where("ativo", "true").count()            # 2, with a warning
view(blob).strict().where("ativo", "true")           # TypeError
view(blob).strict().where("ativo", True).count()     # 2, no warning
```

The cast is always on the **cheap side**: it converts the single filter value, never the N
rows of the column.

`.strict()` applies to the whole view and is one-way: there is no `.soft()` back. It only
affects `where` (and the chained `where`); `select`, `sum` and the `group_*` family ignore
the flag, because none of them takes a user value to convert.

It is the policy of Polars and DuckDB (which tightened in 0.10, removing the implicit cast
to `VARCHAR`), with the default inverted: here convenience is the default and rigour is
opt-in, because in TCF text is the medium, not a user's slip.

### The bool spellings, and one inconsistency

The bool spellings in **text** are a closed list (`true/1/t/yes/sim` and
`false/0/f/no/nao/não`, ignoring case and spaces), in the spirit of PostgreSQL. A non-empty
string does **not** become `True` by truthiness, which is the classic `astype(bool)` trap
in pandas, and anything with no possible reading (`"banana"` on a bool column) raises
`TypeError`.

An `int` on a bool column is another story: it goes through `bool(value)`, so `0` is
`False` and **any other integer** is `True`, including `5` and `-1`. That is Python's rule,
not PostgreSQL's, and it is an inconsistency with the paragraph above: the protection
against truthiness holds for text and does not hold for numbers.

## What it does not do

It is not SQL. There is no parser, no joins, no `ORDER BY`, no `LIMIT`, no computed
expressions and no multi-table plan. `OR` does not exist **between** columns, because
chaining `where` is always AND, but within one column the predicate expresses OR:
`where("uf", pred=lambda x: x in ("SP", "RJ"))`.

It does not read what is not a table. Nested, ragged and optional fields make the view
refuse with a message telling you to use `decode()`. One warning: in `#TCF.8H` an explicit
`None` marks the column as optional, so `encode([{"a": 1}, {"a": None}])` produces a blob
the view refuses, even though the column is present in every row.

## Reading `report()`

`materialized_bytes` is **coarse on purpose**: it counts the whole body of a column as soon
as the column is touched. So a `where` on a dictionary, which builds only the K uniques,
shows the same number as a `select`, which builds the N rows. Use `touched` to see *which*
columns a query reached; for the fine-grained cost of each path, the per-operation
measurements are in [`view-usos.md`](view-usos.md). Refining this is recorded for `.9`.

## Where it wins, and by how much

There is no single "wins / does not win": there are degrees, and the degree depends on the
mode the column was compressed into, on how wide the table is, and on which call you make.
The scale, cheapest first:

| degree | what it does | values built |
|---|---|---|
| **header** | answers without opening the body | 0 |
| **compact structure** | counts separators, fixed-width indices or core markers without rebuilding values | 0 |
| **K uniques** | builds only the distinct values | K |
| **K + compact** | builds the K, then walks the index stream **without expanding it** | K |
| **one column** | builds the N rows of one column | N |
| **several columns** | one column per call in the chain | N x touched |

The "K + compact" row is the one that is easy to miss. On a dictionary column a `where`
walks all N positions of the stream, but each position is a fixed-width index, not a value:
it reads the compact form and never expands it. Reading everything is not the same as
materializing everything.

### By operation and mode

Measured at n=2000:

| operation | `@dict` | dense (`b`/`B`/`C`) | `%split` | core |
|---|---|---|---|---|
| `count`, `nrows` | **compact structure** | **header** | one column | **compact structure** |
| `n_unique` | **K uniques** | one column | one column | one column |
| `distinct` | **K uniques** | one column | one column | one column |
| `where` | **K + compact** | one column | one column | one column |
| `group_count` | **K + compact** | one column | one column | one column |
| `sum`/`min`/`max`/`avg` | one column | one column | one column | one column |
| `group_sum` and family | two columns | two columns | two columns | two columns |
| `select(col)` | one column | one column | one column | one column |

`count` on a dense route comes straight out of the header: the row count is written there
in hex, so it reads 11 or 12 bytes and stops. In core mode it sums the counters and loose
lines in the compact body; it does not rebuild the column. Only an all-`split` table lacks
a structural count and decodes its smallest column.

**Known correctness limit:** a core body containing exactly one empty string is currently
counted as zero, which also truncates `select()`. This is tracked in
[`BUG-VIEW-UMA-STRING-VAZIA`](../../tickets/BUG-VIEW-UMA-STRING-VAZIA.md); use `decode()`
for that shape until it is fixed.

Which mode a column lands in is the encoder's decision, not yours, and it is made on bytes
alone. `fallback=True` (the 0.8 default) is what puts low-cardinality columns in `@dict`,
and therefore what enables the whole `@dict` column of the table above; see
[encode-knobs.md](encode-knobs.md). In `.8H` every column uses the core pipeline without
that competition, so the blob comes out 38.3% larger on the same 2,000-row by 5-column
table and nothing lands in `@dict`.

### How wide the table is changes the answer

`select` of one column always builds N values, but what matters is the fraction of the
table that is:

| columns in the table | `select("c")` | `select()` |
|---:|---:|---:|
| 2 | 50.1% | 100% |
| 5 | 20.0% | 100% |
| 10 | 10.0% | 100% |
| 20 | **5.0%** | 100% |

So calling `select` "materializes" is only half true. It materializes **one** column, and
on a wide table that is most of the saving there is.

### Chaining does not reduce what comes after it

This is the honest limit, and it is worth stating plainly because the intuition says
otherwise. Filtering first and aggregating after does **not** make the aggregation cheaper:

```
where(f, "sim").count()             2000 values built
where(f, "sim").sum("v")            4000
where(f, "sim").group_count("g")    4000
where(f, "sim").group_sum("g", "v") 6000
```

Those numbers are identical whether the filter keeps 1% or 100% of the rows. The filter
cuts the rows **after** the column has been materialized, not before. Making the filter
narrow the work downstream requires reading only the filtered positions, which the
dictionary's fixed-width stream would allow; it is measured and recorded for `.9`
(`H-QUERY-04f`).

### The short version

A table with one low-cardinality column and several wide ones is the shape the view was
built for: the filtering column answers from the structure, and the rest is never touched.
A table of one high-cardinality column is the shape where `view()` and `decode()` cost
nearly the same, and the honest thing is to say so.

This is a `.8` picture. The prototypes that would move `group_*` and the aggregators up the
scale are measured and recorded for `.9`.

## Sorted layout · **experimental**

For a blob **already sorted** by a key (`encode(table, sort_by=key)`), where the groups end
up contiguous. These two may evolve in H-QUERY-04 (0.9).

```python
blob = encode({"cliente": ["Ana","Bruno","Ana","Bruno"],
               "qtd": ["1","2","3","4"]}, sort_by="cliente")
view(blob).agg_by("cliente", "qtd", "sum")     # {'Ana': 4.0, 'Bruno': 6.0}
```

| call | returns | note |
|---|---|---|
| `group_ranges(key)` | `dict[str,(start,end)]` | contiguous ranges per group; `ValueError` if the column is not grouped |
| `agg_by(key, col=None, op="count")` | `dict` | group-by by slice; `op` ∈ `count/sum/min/max/avg` |

The precondition is **contiguity**, not `sort_by` itself: a table that happens to be
contiguous works without having been sorted. And `sort_by` reorders the rows, so `decode`
returns the table in the blob's order. Trade-off documented in
[encode-knobs.md](encode-knobs.md).

## Stability

Everything above except the sorted layout is **stable**: `columns`, `count`, `nrows`,
`column_bytes`, `total_bytes`, `report`, `where`, `select`, the aggregators, `distinct`,
`n_unique` and the `group_*` family. `group_ranges` and `agg_by` are **experimental**.

The objects that `view()` and `where()` return (`LazyTCF` and `Filtered`) are not meant to
be constructed directly; the entry point is `view(blob)`.

Compat: `from tcf_lazy import view` (shim) still works, re-exporting from here.

## See also

- What you can ask, with the measured cost of each question: [`view-usos.md`](view-usos.md)
- Matching pandas, SQL or polars: [`../how-to/mimetizar-pandas-sql-polars.md`](../how-to/mimetizar-pandas-sql-polars.md)
- Encode knobs (`fallback`/`sort_by`): [encode-knobs.md](encode-knobs.md)
- Format (modes `!`/`@`/`%`): [../algorithms/TCF-format.md](../algorithms/TCF-format.md)
- Implementation: [`src/tcf/view.py`](../../src/tcf/view.py)
- 0.9 expansion design (decode-DAG, indices): [`hquery01-decode-dag-indices-design.md`](../../experiments/lab/dirty/notas/2026-06/hquery01-decode-dag-indices-design.md)
