<!-- l10n: doc_id=lazy-view · lang=en · canonical -->
**English** · [Português](lazy-view.pt-BR.md)

# Reference: `tcf.view` (query on demand)

Reference for the read-only query layer [`tcf.view`](../../src/tcf/view.py): it connects to
a TCF blob and answers queries (`count/sum/min/max/avg`, `where`, group-by),
**decompressing only what is needed**. Filters recorded in the header are reapplied when
the column is read, and anonymous columns stay positional. Querying does not change
`encode`, `decode` or the format.

**What it reads**: `#TCF.8M` (multi-column), `#TCF.8H` when it is a rectangular table, and
the single-column route in all of its forms (`#TCF.8`, `#TCF.8n`, `#TCF.8b`, `#TCF.8bB`,
`#TCF.8 :spec`, and the dense `B`/`C`). In a single column the name is `"0"`, as in any
anonymous column
([ADR-0029](../adr/0029-version-format-identification-semi-implicit.md)). `#TCF.6` and
`#TCF.7` are not accepted in the `0.8` package (historical compatibility through git).

## The whole surface on four rows

One table small enough to read, every operation on it, and the real output of each. The
rest of this page is the contract behind these lines.

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
```

`columns` and `count` read only the structure, so nothing is materialized. `distinct`
brings in `uf`, `sum` brings in `valor`, and `ativo` is never touched.

Filtering and grouping, on a fresh view each time:

```python
v.where("uf", "SP").count()           # 2
v.where("uf", "SP").sum("valor")      # 30.0
v.group_count("uf")                   # {'SP': 2, 'RJ': 1, 'MG': 1}
v.group_sum("uf", "valor")            # {'SP': 30.0, 'RJ': 30.0, 'MG': 40.0}
v.select("uf")                        # [{'uf': 'SP'}, {'uf': 'SP'}, ...]
```

Values come back in the type they went in as, so you compare with that type:

```python
v.where("valor", 30).count()          # 1   int, because the column is `N`
v.where("ativo", True).count()        # 3   bool, because the column is `B`
```

And the filter value is read in the column's type, with the conversion recorded:

```python
v.where("ativo", "true").count()      # 3, plus a UserWarning:
                                      # "bool column: the value 'true' (str) was read as True"

view(blob).strict().where("ativo", "true")
# TypeError: this column is bool and the value is str ('true'). The view is in
#            STRICT mode, so the conversion is not automatic: pass True.
```

> **Stability**: the L1–L4 surface (below) is **stable**. `group_ranges`/`agg_by` (L5) are
> **experimental**: they may evolve in H-QUERY-04 (0.9). Marked per method.

## Model

- **Lazy**: `view(blob)` only parses the header (name/mode/size per column). No body is
  decoded until a query asks for that column; each column is decoded **at most once**
  (internal cache).
- **Row-aligned by position**: the i-th position of every column is row `i`. `where()`
  returns the indices of the rows that matched; aggregation and `select` on **any other**
  column use the same indices. That is how "a row in one column is the same row in
  another".
- **Numeric contract** (`sum/min/max/avg`): **ignores** empty (`""`) and null (`None`); a
  non-numeric value raises `ValueError` (intentional: it does not silence dirty data). With
  no numeric value at all, `min`/`max`/`avg` raise and `sum` returns `0`, which is Python's
  `sum([])` and therefore an `int`, not a `float`.
- **Read only**: no operation changes the blob.

## SQL-like querying, without SQL

`view()` offers query paths that resemble a SQL execution, but it does not interpret a SQL
string nor try to reproduce every semantic of a database:

Naming a column, across the whole view surface: `str` = **name**, `int` = **position**.
Same rule as `schema=` ([ADR-0047](../adr/0047-schema-parametro-unico-de-spec.md):
`0 <= pos < n`, no negatives; a column *called* `"2"` is found by the `str`, the position
by the `int`).

**Data type**: the table declares each column's type in the header (one letter: `N` number,
`B` bool, absent = text), and values come back in the type they went in as:

```python
v = view(encode({"cidade": ["SP", "SP", "RJ"], "valor": [120, 80, 200]}))
# shebang: '#TCF.8M!8=cidade,!aN=valor'  (multi-col, type tag on the 2nd column)
v.where("valor", 120).count()      # 1: compare with int, which is the column's type
v.sum("valor")                     # 400.0
```

A typed column does **not** push the table out of `.8M`: the type costs a 1-byte tag in the
header. `#TCF.8H` is another route, the one for `encode(list[dict])`, and the view reads it
too when it is rectangular.

### Comparing: soft by default, strict when you want it

The file is always text, and the type is the reading the header declares. So
`where(col, "true")` on a boolean column is a clear intent, not an error: the **filter
value** is read in the column's type, and the conversion is recorded.

```python
v.where("ativo", "true")     # bool column: 'true' is read as True, with a warning
v.where("ativo", True)       # right type: no conversion, no warning
v.coercoes                   # what was converted in this view, and how
```

The cast is always on the **cheap side**: it converts the single filter value, never the N
rows of the column. On a 5,000-row table, one conversion.

The bool spellings in **text** are a closed list (`true/1/t/yes/sim` and
`false/0/f/no/nao/não`, ignoring case and spaces), in the spirit of PostgreSQL. A non-empty
string does **not** become `True` by truthiness, which is the classic `astype(bool)` trap in
pandas, and anything with no possible reading (`"banana"` on a bool column) raises
`TypeError`: converting is reading the intent, not guessing.

An `int` on a bool column is another story, and it is worth knowing: it goes through
`bool(value)`, so `0` is `False` and **any other integer** is `True`, including `5` and
`-1`. That is Python's rule, not PostgreSQL's, and it is an inconsistency with the paragraph
above: the protection against truthiness holds for text and does not hold for numbers.

For code that wants to be strict, `.strict()` turns automatic conversion into an error:

```python
blob = encode({"ativo": [True, False, True], "n": [1, 2, 3]})

view(blob).where("ativo", "true").count()            # 2, with a warning
view(blob).strict().where("ativo", "true")           # TypeError
view(blob).strict().where("ativo", True).count()     # 2, no warning
```

`.strict()` applies to the whole view and is one-way: there is no `.soft()` back. It only
affects `where` (and the chained `where` on `Filtered`); `select`, `sum` and the `group_*`
family ignore the flag, because none of them takes a user value to convert.

It is the policy of Polars and DuckDB (which tightened in 0.10, removing the implicit cast
to `VARCHAR`), with the default inverted: here convenience is the default and rigour is
opt-in, because in TCF text is the medium, not a user's slip.

One difference worth knowing: in `.8H` each column uses the core pipeline, without the
`min(tcf, raw, dict, split)` competition of `.8M`. The blob comes out **38.3% larger** on
the same 2,000-row by 5-column table, and `group_count` falls back because there is no
dictionary mode on that route. Laziness holds in both, and `count()` costs 0.0% there too.

The cost of each operation, per column mode, is measured in
[`view-usos.md`](view-usos.md).

Out of scope: nested, ragged and optional fields are not a table, and the view refuses with
a message telling you to use `decode()`.

| capability | API | note |
|---|---|---|
| projection | `select(cols)` | materializes only the requested columns; scalar (`str`/`int`) = 1 column; `[]` = none |
| filter | `where(col, value=...)` or `where(col, pred=...)` | equality/predicate; chaining is AND; `value` is read in the column's type (soft), or required in it with `.strict()`; `None` matches null |
| aggregation | `count`, `sum`, `min`, `max`, `avg` | empty and null are ignored by the numeric aggregators |
| distinct values | `distinct(col)` · `n_unique(col)` | `SELECT DISTINCT` and `COUNT(DISTINCT)`; in `@dict` they come off the unique table, in O(K) |
| grouping | `group_count(col)` | structural path in `@dict` without a filter; fallback otherwise |
| aggregation per group | `group_sum`, `group_min`, `group_max`, `group_avg` `(por, col)` | the `GROUP BY x AGG(y)`; materializes only the columns involved |
| grouping by several columns | `group_*(["a","b"], col)` | the `GROUP BY a, b`: the key is the tuple of values |
| filter and group | `where(...).group_*(...)` | the `WHERE ... GROUP BY`: the aggregation runs on the rows that matched |
| grouped layout | `group_ranges`, `agg_by` | experimental; requires the contiguous order of `sort_by` |
| alignment | positional indices | row `i` of each column is the same row |

There is no SQL parser, no joins, no `ORDER BY`, no `LIMIT`, no computed expressions and no
multi-table plan. `OR` does not exist **between** columns (chaining `where` is always AND),
but `pred=` expresses OR within one column:
`where("uf", pred=lambda x: x in ("SP", "RJ"))`.

A column in `tcf` mode may require full materialization because its references are
interleaved. To see which columns a query reached, use `touched`; for the fine-grained cost
of each path, the per-operation measurements are in [`view-usos.md`](view-usos.md), because
`materialized_bytes` is too coarse for that (see the note in the table below).

The evolution of `QueryPlan`/`execute()` and local indices belongs to later query work, not
to the `.8` format.

## `view(blob) -> LazyTCF` · stable

Connects to a TCF blob. Accepts multi-column, rectangular table and single column;
`ValueError` with a message telling you to use `decode()` when the blob is not a table
(nested, ragged, optional field) or is from a legacy format.

## `LazyTCF`: introspection (cheap, header only) · stable

| member | returns | note |
|---|---|---|
| `columns` | `list[str]` | names in header order |
| `nrows` | `int` | number of rows by the shortest path: `n` declared in the header → raw (counts `\n`) → dict (`len(stream)//width`) → core counters. None of those materializes a value. `split` mode declares no count: if **every** column of the table is `split`, it falls back to decoding the smallest one (measured: 49.7% on a two-column table) |
| `column_bytes(name)` | `int` | size of the column's **compressed** body (without decoding) |
| `total_bytes` | `int` | sum of the bodies |
| `materialized_bytes` | `int` | sum of the bodies of the columns in `touched`. **Coarse on purpose**: it counts the WHOLE body of the column as soon as it is touched, so a `where` on `@dict`, which builds only the K uniques, shows the same number as a `select`, which builds the N rows. It serves to see WHICH columns the query reached, not the fine cost of each path. The refinement is recorded for `.9` |
| `report()` | `dict` | `{total_bytes, materialized_bytes, pct, touched, n_cols}` (selectivity) |

## `LazyTCF`: aggregators · stable

`idx` is internal (used by `Filtered`); normal use is without an argument or through
`where(...)`.

| method | returns | contract |
|---|---|---|
| `count(idx=None)` | `int` | number of rows (or of the filter) |
| `sum(col, idx=None)` | `float` | sum; ignores empty and null. With no numeric value it returns `0` (`int`, Python's `sum([])`) |
| `min(col, idx=None)` | `float` | minimum; `ValueError` if there are no numerics |
| `max(col, idx=None)` | `float` | maximum; same |
| `avg(col, idx=None)` | `float` | average; same |
| `group_count(col)` | `dict` | `{value: n}` **without expanding** the column when it is a dictionary (`@`) and there is no filter; otherwise fallback (decode + Counter). The key comes out in the **column's type**, so on an `N` column the keys are `int`/`float` and on a `B` column they are `bool`, not `str` |
| `distinct(col)` | `list` | distinct values, in order of appearance; in `@dict` it comes off the unique table (builds the K, not the N) |
| `n_unique(col)` | `int` | how many distinct; in `@dict` it is the size of the unique table, building no value |
| `group_sum(por, col)` | `dict` | sum per group; a group with no usable value gives `0.0` |
| `group_min/max/avg(por, col)` | `dict` | same; a group with no usable value gives `None`, because there is no answer (returning `0.0` would invent a value the column does not hold) |

In all of them, `por` takes one column or a list, and with a list the key is the tuple of
values. Null and empty string **form a group** (as in SQL and polars, unlike the pandas
default, which drops them); the key order is the order of appearance. There is no `dropna`
flag: dropping the null is a filter, and `where(col, pred=lambda x: x is not None)` already
does it, keeping what was thrown away in plain sight. On a dictionary column that predicate
runs over the K uniques, so the explicit form costs no more. The semantic divergences from
the market are recorded in
[`DECISAO-GROUPING-SEMANTICA`](../../tickets/DECISAO-GROUPING-SEMANTICA.md).

## `LazyTCF.where(col, value=None, *, pred=None) -> Filtered` · stable

Filters by equality (`value`) or predicate (`pred`), decompressing **only the filter's
column**. On a dictionary column (`@`) it scans the index stream without decoding the N
values (it evaluates `value`/`pred` over the K uniques). Returns [`Filtered`](#filtered).

On that column, the two extremes never even scan the stream. The unique table is the closed
list of what the column holds and every row points at some unique, so: when **no** unique
matches, no row can match and the answer is `[]`; when **all** match, every row matches and
the answer is `range(n)`. Filtering by a value the column does not have went from scanning
the N positions to not reading the stream. The middle case keeps scanning, because there the
answer depends on which rows point at what.

## `LazyTCF.select(cols=None, idx=None) -> list[dict]` · stable

Aligned rows as dicts; decodes only the requested columns (`cols=None` = all).

## `Filtered` · stable

The result of `where()`. Operates only on the rows that matched (aligned).

| method | note |
|---|---|
| `count()` | number of filtered rows |
| `sum/min/max/avg(col)` | aggregates `col` over the filtered rows |
| `select(cols=None)` | filtered rows as dicts |
| `distinct(col)` · `n_unique(col)` | distinct **over the filtered rows** |
| `group_count(col)` · `group_sum/min/max/avg(por, col)` | aggregates **over the filtered rows**: the `WHERE ... GROUP BY` |
| `where(col, value=None, *, pred=None)` | **chains** (AND): narrows the current indices |

```python
v.where("cidade", "SP").where("plano", "Premium").sum("valor")   # AND
```

## L5: layout for low latency · **experimental**

Meant for a blob **already sorted** by a key (`encode(table, sort_by=key)`), where the
groups end up contiguous. They may evolve in H-QUERY-04 (0.9).

| method | returns | note |
|---|---|---|
| `group_ranges(key)` | `dict[str,(start,end)]` | contiguous ranges per group; `ValueError` if the column is not grouped |
| `agg_by(key, col=None, op="count")` | `dict` | group-by by slice; `op` ∈ `count/sum/min/max/avg` |

```python
blob = encode({"cliente": ["Ana","Bruno","Ana","Bruno"],
               "qtd": ["1","2","3","4"]}, sort_by="cliente")
v = view(blob)
v.agg_by("cliente", "qtd", "sum")     # {'Ana': 4.0, 'Bruno': 6.0}  ("qtd per cliente")
```

## Measured example

```python
from tcf import encode, view
blob = encode({
    "cliente": ["Ana","Bruno","Carla","Diego","Ana","Bruno"],
    "cidade":  ["SP","SP","RJ","SP","RJ","SP"],
    "valor":   ["120","80","200","120","80","150"],
})
v = view(blob)
v.count()                                  # 6
v.group_count("cidade")                    # {'SP': 4, 'RJ': 2}
v.where("cidade", "SP").sum("valor")       # 470.0
v.report()                                 # {... 'pct': 55.6, 'touched': ['cidade','valor'], ...}
```

`report()['pct']` shows the fraction of the blob materialized, the lazy layer's whole pitch:
the query above touched ~56% (2 of 3 columns) instead of the 100% a `decode()` would.

## Notes / limits

- **A column in `tcf` mode** (interleaved OBAT+HCC): `group_count` and aggregation fall back
  (decoding the whole column). The clean structural gain lives in `@dict`/raw. Turning on
  `fallback=True` in `encode` (the 0.8 default) puts low-cardinality columns in `@dict`
  automatically, enabling the queries without expanding. See
  [encode-knobs.md](encode-knobs.md).
- `sort_by` (for L5) is **order-free** but reorders the rows: `decode` returns the table in
  the blob's order. Compression trade-off documented in [encode-knobs.md](encode-knobs.md).
- Compat: `from tcf_lazy import view` (shim) still works, re-exporting from here.

## See also

- Implementation: [`src/tcf/view.py`](../../src/tcf/view.py)
- What you can ask, with the cost of each question: [`view-usos.md`](view-usos.md)
- Encode knobs (`fallback`/`sort_by`): [encode-knobs.md](encode-knobs.md)
- Format (modes `!`/`@`/`%`): [../algorithms/TCF-format.md](../algorithms/TCF-format.md)
- 0.9 expansion design (decode-DAG, indices): [`hquery01-decode-dag-indices-design.md`](../../experiments/lab/dirty/notas/2026-06/hquery01-decode-dag-indices-design.md)
