# Changelog

History of TCF condensed into logical versions. For commit-level detail see `git log`.

The project is **pre-1.0**. The package version is `0.<format>.<release>`: the minor tracks
the format number (`#TCF.8` today), and there is **no compatibility guarantee between
pre-1.0 versions**: an older format is reproduced by checking out the tag that emitted it,
not by carrying compatibility code ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md),
[ADR-0028](docs/adr/0028-pre-1.0-versioning-minor-format-coupling-release-cadence.md)).
Semver starts when the format freezes at 1.0.

Entries below are dated and append-only: this is where the chronology lives, so the reference
documentation does not have to carry it. Headings that read "STABLE" or "frozen format" are
internal milestones of their moment, not contracts. Date in parentheses = when the milestone
was consolidated.

Lab narratives, kept outside the package: v0.5 per-experiment timeline in
[`docs/archive/workbench/_archive/DEVELOPMENT.md`](docs/archive/workbench/_archive/DEVELOPMENT.md); the
compositional cycle in
[`experiments/lab/dirty/notas/2026-05/historia-dirty-lab.md`](experiments/lab/dirty/notas/2026-05/historia-dirty-lab.md).

---

## 0.8.4 (2026-09-01): the spelling of the input stops choosing the arsenal

> **Read this first if you already have data on disk, or a consumer you do not upgrade
> together with the producer.** Compatibility differs **by surface**, not by package, and
> stating it by package is the mistake this changelog already had to publish an errata for
> one release ago. Measured against `tcf-format==0.8.3` installed from PyPI:
>
> | | `decode` | `view` |
> |---|---|---|
> | **0.8.4 reading a 0.8.3 wire** | reads all of them | reads them; refuses only what 0.8.3 also refused |
> | **0.8.3 reading a 0.8.4 `#TCF.8R` wire** | **refuses, loudly** (`discriminador 'R' desconhecido`) | **answers, and is wrong, in silence** |
>
> That bottom-right cell is the one that costs you. A 0.8.3 `view` opens a `#TCF.8R` blob as
> if it were single-column: on a 100-row table it reports `columns == ['0']` and
> `nrows == 17`, raises nothing and warns nothing. It cannot be fixed from here, because the
> code that misreads is already published; the only defence is knowing.
>
> **Who is exposed**: every flat rectangular `list[dict]`, which is the whole records route,
> not an edge. If a 0.8.3 consumer uses `view()`, upgrade it before, or at the same time as,
> the producer. A 0.8.3 consumer that uses `decode()` is safe: it fails loudly.

Two welds, both about the encoder deciding instead of the caller guessing.

### What breaks

Calls that worked on 0.8.3 and now raise. All of them are the same shape: something that was
accepted and silently ignored is now refused, so the fix in your code is to drop the argument.

| call | now | why |
|---|---|---|
| `encode(list_of_str, fallback=False \| min_header=False \| drop_names=True \| parallel=True)` | `ValueError` | the `encode` docstring already declared all four multi-col, and they moved zero bytes on a single column. Passing the **default** value still works, because that asks for nothing |
| `encode(list_of_str, sort_by=...)` | `ValueError` | a list of one column has no named column to sort by |
| `encode({"col\r": [...]})` and any column name carrying `\r` | `ValueError` | the wire is LF-only and the LF separates the meta; 0.8.3 emitted a raw CR inside the meta |
| `encode([True, "a\rb"])`, a bool+str union with `\r` in the string | raises | same cause, in the union route |
| a `.8H` blob rewritten in transit (LF turned into CRLF) | raises | 0.8.3 decoded it with the `\r` **inside the data**, which is corruption that looks like a value |
| `decode(w, schema={key_that_names_no_column: ...})` | emits `UserWarning` | it was silent. Suites running with `-W error` will see this as a failure |
| `view(...).where(no_match).sum(col)` | returns `0.0`, not `0` | the signature promised `float` and `group_sum` already returned `0.0` |

And one change of promise rather than of API: **a blob asked for with `sort_by` may come back
in the original order.** 0.8.3 stated in writing that the decode returns the sorted order;
0.8.4 sorts only when sorting shrinks the wire. Consequently `view.group_ranges` can now
refuse a blob that it used to accept, and `view.agg_by` falls back on its own so it never
raises for that reason.

### `#TCF.8R`: a flat rectangular `list[dict]` is a table, not a tree ([ADR-0049](docs/adr/0049-marcador-r-a-forma-da-entrada-e-metadado.md))

The same table written three ways used to cost three prices. A column of 50 booleans cost
30 B as `list[str]`, 68 B as `dict[1 col]` and **159 B** as `list[dict]`, because the
spelling of the input picked the route, and the route picked the techniques: `.8H` emits
only the `tcf` candidate, while `.8M` emits `min(tcf, raw, dict, split)`.

A flat rectangular `list[dict]` (same keys in the same order, scalar cells, no `\n` or `\r`
in a name or a value) is now canonized into columns and travels the `.8M` route. One byte
changes: the family discriminator at index 6, which comes out `R` instead of `M`. `decode`
reads it and rebuilds the list of dicts; `view` opens it as the table it is.

- **It cannot get worse**, by construction rather than by measurement:
  `body(.8M) = min(tcf, raw, dict, split) <= body(.8H) = tcf`. Six adversarial cases built to
  inflate the `.8M` meta produced zero regressions.
- **The marker costs zero bytes**: the one-character slot already existed.
- Measured on the project's own hierarchical control synthetics: the five rectangular cases
  fell **36% to 68%** (7476 B to 3555 B in total), and the seven genuinely hierarchical ones
  are **byte for byte** what they were.
- Still `.8H`: ragged, nested, array in a cell, non-`str` key, and anything carrying `\n` or
  `\r` in a name or a value, because escaping leaves is a `.8H` capability and routing those
  would have taken it away. `[]` is still `#TCF.8`.
- Seven kwargs that used to raise on records now work (`layers`, `min_len`, `stamp`,
  `parallel`, `fallback`, `min_header`, `drop_names`). `sort_by` and `name` still refuse.
- A `#TCF.8R` wire is **not readable by earlier releases**. Pre-1.0 that is the declared
  regime ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)).

### `sort_by` becomes a candidate, not an order ([ADR-0050](docs/adr/0050-sort-by-vira-candidato-o-floor-decide.md))

Sorting groups the key and scrambles every other column at the same time, so it pays or costs
depending entirely on the data: **-43.0%** when the companion columns are a function of the
key, **+52.1%** when they are independent of it, on a six-column table. The caller had to
guess, and could not know without encoding both.

Passing `sort_by` already meant giving up row order, so the encoder was already authorized to
reorder. It is now also free not to. Both versions are encoded and the smaller one is emitted,
which makes the kwarg **never worse**: across seven measured cases it avoids 734 B of loss
without giving up any gain. Cost: one extra encode, only when `sort_by` is passed.

- `view.agg_by` now falls back to the order-free path when the key is not contiguous, so it
  never raises because of a layout the caller did not choose. `view.group_ranges` stays strict
  on purpose: it is the layout inspector.
- The claim that `agg_by` was "cheaper" than `group_sum` **was measured and did not hold**:
  same columns materialized, same rows decoded, same result, and the contiguous path came out
  3.6% slower. The docstring is corrected.
- `group_count` over a dictionary column was calling a Python-level index decoder once per
  **row**; it now counts in C and decodes once per **distinct index**. On 20,000 rows that is
  10.7 ms to 1.4 ms, and the structural path went from 6.5x slower than materializing to
  faster than it, while still building no N-sized list.
- Four surface defects of the same kwarg, fixed or documented: it was **silently ignored** on
  `list[str]` (and the silence was pinned in a test) and now refuses; an unreachable `raise`
  was removed; the `str(value)` sort key (`'10'` before `'2'`) is documented rather than
  changed, because any total order groups equally well and order stopped being a promise.

### The query surface agrees with itself

A consistency matrix ran every view path against `decode` plus plain Python, over 7 tables ×
2 spellings × 3 column modes. The aggregators, the filters, their composition and the two
group-by paths came out **identical everywhere**, and that is now a permanent gate rather
than a lab finding (`TestViewConcordaComODecode`, 48 parametrised cases).

What it did find was in the messages and in the surface:

- `min`/`max`/`avg` **raise** on an empty selection while `group_min`/`group_max`/`group_avg`
  return `None` for a group with no usable value. The divergence stays, because the two are
  different questions: the group has a **key to preserve**, the plain aggregator has none,
  and returning `None` there would break the caller's arithmetic far from the cause. The
  message now says which of the two empties happened (nothing matched the filter, or the
  matched rows are all null) and points at the path that does not raise.
- `view.group_ranges` used to advise `use encode(table, sort_by=...)`, advice this same
  release made unreliable: it fires on blobs that were **already** encoded with `sort_by` and
  that the FLOOR chose not to sort. It now says what to do instead.
- **`Filtered` gained nine methods**: `columns`, `nrows`, `agg_by`, `strict()` and the whole
  telemetry (`total_bytes`, `column_bytes`, `materialized_bytes`, `report()`). The absence was
  an accident, not a decision, and telemetry is the one that mattered: the filter **is** the
  query, so "how much did this cost" is a question about the slice, and
  `view(blob).where(...).sum(...)` keeps the view nowhere to ask it. `group_ranges` stays off
  the slice deliberately, because filtering breaks the contiguity it requires and both ends of
  its ranges would be ambiguous.
- `schema=` scalar now treats a record list as the table it is: one column applies in either
  spelling, two or more raise in either. On 0.8.3 a record list refused it in **both** cases,
  with the generic not-flat message, so what changed is that one column now **works**; the
  silent discard this entry first described was a state of the tree during 0.8.4's own
  development, never a published behaviour.
- **The single-column route stops swallowing multi-column knobs.** `fallback`, `min_header`,
  `drop_names` and `parallel` now raise on a `list[str]`, joining `sort_by` and `name`. The
  `encode` docstring already declared all four multi-col, the `.8H` route already refused
  them, and measurement across six corpora confirmed they move zero bytes there. **`min_len`
  does not join them**, and that correction matters more than the fix: it was listed as a
  no-op and it is not, it is the one knob of the group that works on a single column
  (46 B to 23 B on a column of IDs, 363 B to 56 B on long unique values). Refusing it would
  have removed a real capability, which is what testing one corpus instead of six nearly did.
- **The `.8H` stops pricing the spec against a header it never emits.** It delegated the
  decision to the flat encoder, which compares `'#TCF.8 :id\n' + body` against the bare body,
  charging the candidate an 11-byte header this container discards on the very next line. The
  price it actually pays is the `:id` inside the column meta. Fixed to charge
  `:<size>:<id>`, the real worst case, which flips three short date columns from discard to
  apply and saves 443 B across the twelve measured columns, with zero never-worse violations
  and no gate re-pin.

  The conservative pricing is deliberate. Charging only the `:id` under-estimates, because a
  column without a nature may omit its size while one with a nature must declare it: the meta
  `#TCF.8Hc` (8 B) becomes `#TCF.8Hc:32:dt` (14 B), and a wire grew from 46 B to 47 B in
  testing. Erring toward emitting less nature costs bytes; erring the other way breaks
  never-worse, which is the invariant every candidate in this format rests on.

  The other two accountings were examined and are **correct**. The single-column route
  compares against a baseline carrying polarity and domain-bN, and that is not unfairness: the
  grammar makes a polarity suffix and a `:spec` mutually exclusive in the same header slot, so
  the candidate cannot carry that arsenal at all. Comparing the best *emittable* wire on each
  side is precisely what a FLOOR does. The multi route was already the fair one.

---

## 0.8.3 (2026-08-29): the edges stop disagreeing across families

> **Errata (2026-08-29, after publication).** Three claims in this entry were wider than the
> evidence, and are corrected below with the measurement that settles each one. The text is
> corrected in place rather than appended to, because a reader deciding whether to upgrade
> reads the entry, not its footnotes; what the errata preserves is the fact that they were
> wrong. (1) The title promised that the three families answer alike, which overstates: the
> bool+str union is still accepted by the single-column route and refused by `.8M` and
> `.8H`, by decision, not by oversight. (2) The entry said one emission change and *nothing
> else*; there are **two**. (3) It said 0.8.3 reads every 0.8.2 wire, which holds for
> `decode` and not for `view`. Raised by the owner in `T-DOC-RELEASE-083-SUPERFICIE`.

An audit measured the three wire families (`#TCF.8`, `#TCF.8M`, `#TCF.8H`) along five axes
and found them agreeing on clean, homogeneous data and disagreeing on almost every edge.
This release closes that gap on the edges: seven welds, six bug tickets, and two changes to
what the encoder emits. It does not make the three families equivalent in capability, and
does not try to: the bool+str union stays a single-column capability
([ADR-0039](docs/adr/0039-lazytype-bool-cabeca-congelada-extras.md)).

**Read this first if you already have data on disk.** Two emission changes, both measured:

| input | 0.8.2 | 0.8.3 |
|---|---|---|
| `.8H` column dense with nulls (key in every row, some `None`) | `#TCF.8Ha?:5`, 19 B | `#TCF.8Ha?0:5`, 20 B |
| `{"v": []}` (named column, zero rows) | `#TCF.8H#Ov#:3[`, 18 B | `#TCF.8M@v`, 12 B |

Both round-trip exactly in both versions, so neither is a regression; they are changes in
which wire the encoder chooses. The byte-canonical gates are untouched.

Compatibility, stated per surface because the two surfaces differ:

| | `decode` | `view` |
|---|---|---|
| 0.8.3 reading a 0.8.2 wire | reads the eight cases measured, including the dense-with-nulls one | **refuses** the dense-with-nulls one, as 0.8.2's own view did |
| 0.8.2 reading a 0.8.3 wire | **refuses** the dense-with-nulls one, failing loudly rather than reading it wrong | same |

The `view` line is the point of the change: the old spelling could not tell "key missing"
from "key present, value null" by the header, so the view refused the whole table. 0.8.3
fixes that going forward, not retroactively, because the information is not in the old wire.

These four cells are what was measured, on eight representative wires. They are not a claim
about every wire the two versions can produce.

**Mixed-type columns stop losing data silently.** A column mixing `int` and `str` used to
pass through `#TCF.8M` and come back wrong: `[1, ""]` returned `[1, None]`, `[1, "1"]`
collapsed both values into one, and `[1, "a"]` produced a wire the decoder itself could not
read. The multi-column gate now uses the same homogeneity judge as `#TCF.8H`, so all three
families refuse the same column, which is what the API reference already promised. Nine of
thirty-nine routes changed verdict; the fourteen that round-tripped correctly are byte-identical.

**Null is not absence, in the hierarchical family too.** `encode([{"a": "x"}, {"a": None}])`
is a rectangular table, and the view refused it as ragged: the header spelled "key missing"
and "key present, value null" the same way. The dense-with-nulls scalar column now carries
a two-state element mask, the same one arrays already used, so the view can tell a table
with nulls from a ragged one by the header alone. This is the emission change above.

**The union column can be filtered on both sides.** In `#TCF.8bB` (bool and str together)
the view read the tag at index 6 and declared the column pure bool, ignoring the `B` at
index 7 that marks the union. Filtering by a string returned the boolean's row, or nothing,
or raised. Four ways to ask are now available, and three of them already worked:
`where(col, True)` for the boolean, `where(col, "true")` for the string as it is, and
`pred=` for the semantic and case-insensitive sets.

**A mixed column now says so.** The union route emitted the wire silently, while the same
column is refused as a `dict` and as a dataset: the same data passed or not depending on
how it was written. It warns now, counting each type.

**Four more places where the view answered about a table that does not exist**: a `#O` with
columns of different lengths was accepted and then accused an intact blob of being corrupt;
a magic-less wire (`stamp=False`) was refused though `decode` reads it; a zero-row column
invented a `''`; and a truncated wire got a silent row count where a full `decode` would
refuse. The last one now warns instead of going quiet.

**Errors that teach.** The mixed-type message named a family the caller never invoked,
cited a date (none of the other 210 messages in the package do), and named neither the
column nor the value (182 of 211 do). It now names both and, more importantly, says what
each of the two ways out costs: separating by type preserves the type but scrambles the
order when types are interleaved, and converting to string preserves the order but erases
the type and merges values that differed only by it. A non-`str` dict key stops raising a
raw `TypeError` and gets the typed error the hierarchical route already had.

**Also**: the `.8H` gained the spec telemetry the other two families already had, and warns
when a spec is dropped because a value cannot be represented; the view undoes leaf escaping
in `.8H`, so text columns holding a backslash or CR are read as the data, not as the escape.

Suite: 1693 tests. Byte-canonical gates: 33, unchanged. Two navigation pins re-pinned
(`c05` 842→843, `c12` 1453→1454), both `.8H` synthetics with a dense-with-nulls column.

---

## 0.8.2 (2026-08-25): the view learns to read the structure

Ten welds on top of 0.8.1, all in the read-only query layer except one, which does change
what the encoder emits.

**Format change (emission)**: a typed column no longer pushes the whole table out of
`#TCF.8M` into `#TCF.8H`. The type now travels as a one-byte tag in the meta, so
`encode({"uf": [...], "qtd": [1, 2, 3]})` stays multi-column and keeps the
`min(tcf, raw, dict, split)` competition. Measured cost of the type: **+1 byte** when the
typed column sits anywhere but last, **+3** when it is last (the tag brings back the size
that `min_header` was omitting; the minimal wire would be +1, and that header optimisation
is not done).

**The view reads everything that is a table**: `#TCF.8M`, `#TCF.8H` when rectangular, and
the single-column route in all its forms. Until now a single `int` or `bool` column made
`view()` refuse the table outright.

**`count()` stopped materialising anything**, in every mode. Counting rows never needs the
values, and the structure already states them: dense routes write `n` in the header as hex;
the core body carries counters (`*N|`) declaring how many rows each one stands for; the raw
body is one line per value; the dictionary is `len(stream) // width`. `report()` reflects
it: after a plain `count()`, `materialized_bytes` is 0. The one exception is a table where
*every* column is `split`, which declares no count anywhere.

**`view(blob)` no longer decodes on open** in the single-column route. It used to call
`decode()` in `__init__`, so connecting to a blob already materialised 100% of the wire
before any question was asked.

**`where` answers the two extremes without scanning**: in a dictionary column, when no
unique matches the answer is empty, and when all match it is every row. The unique table is
the closed list of what the column holds, so it settles both ends by itself.

**Two silent bugs fixed**, both of the same class (two spellings of one marker, two
readers): the new counter reader missed the multi-delta `*29+0,1|` that the encoder emits
for any date or datetime column, which made `view` report 63 rows out of 1000 and, worse,
`select()` return the table truncated with no error; and the fast filter path agreed with
the slow one only on text columns.

**The grouping surface is complete.** `where(...).group_count(...)`, the most basic
`WHERE ... GROUP BY` in SQL, used to raise `AttributeError`: the filtered result knew how
to aggregate the whole set but not how to group it. Added along with `group_min`,
`group_max`, `group_avg` (only `count` and `sum` existed) and grouping by several columns,
where the key becomes the tuple of values. Where the market disagrees with itself, the
choices are documented rather than assumed: a null key **forms a group** (as in SQL and
polars, unlike pandas' default, which drops it); a group with no usable value sums to
`0.0`, because the empty sum has an answer, while `min`/`max`/`avg` return `None` there,
because they do not; and the group shows up either way instead of vanishing.

**`distinct` and `n_unique`**, the `SELECT DISTINCT` and `COUNT(DISTINCT col)`. In a
dictionary column both come off the unique table the body already carries, in O(K). They
cost different things and the docs say so: `n_unique` only needs its size and builds no
value at all, while `distinct` builds the K uniques, because that is what it returns.

**`None` no longer blows up the encoder.** A null anywhere in a column raised a raw
`TypeError` from three layers below `encode`, with no column or row named, whenever the
first value formed a digit template with 2+ fields. The `%split` candidate now declines
columns with nulls, the same refusal for the same reason the raw candidate already made:
the mode has nowhere to represent a null, and the tcf candidate, which has a proper null
slot, serves those columns. Measured before welding: across 6 strong-template shapes x 4
null fractions, the serving mode already beats the ceiling of a null-tolerant split in all
24 combinations, so declining costs zero bytes and no wire changes.

**Grouping semantics are now decisions, not defaults.** A null key forms a group and there
is deliberately no `dropna` flag: dropping the null is a filter, and
`where(col, pred=lambda x: x is not None)` already does it while keeping the discard
visible (on a dictionary column the predicate runs over the K uniques, so the explicit
form costs no more). A group with no usable value sums to `0.0` because the empty sum has
a mathematical answer, while `min`/`max`/`avg` return `None` there because they do not.
A new how-to (`docs/how-to/mimetizar-pandas-sql-polars.md`) gives the one-line recipe for
matching pandas, SQL or polars behaviour, each recipe verified by execution against what
the original tool would return.

**`where` now reads the filter value in the column's type** (soft by default, with a
warning and a record in `v.coercoes`), replacing the `TypeError` that 0.8.1 raised. A
`.strict()` opt-in keeps the old rigour.

Test suite 1252 → 1497. Byte-canonical gates green throughout, with a deliberate re-pin
only where the typed route changed emission.

---

## 0.8.1 (2026-08-23): fail-loud: wire concatenado, contador RLE, view posicional

Três comportamentos silenciosos eliminados do decode/view, cada um re-provado em lab
dedicado com verificação adversarial independente antes do fix. **Zero mudança de emissão**:
o encode está intocado e o wire é byte-idêntico ao 0.8.0 (gates verdes sem re-pin).

- **`decode` rejeita header no meio do corpo**: concatenar dois wires prontos corrompia
  **calado** (as refs do segundo resolviam na tabela acumulada do primeiro; na pior variante
  até `n_rows` batia). Agora `ValueError` nomeando a causa: cortar um wire é seguro,
  concatenar exige decode + re-encode. Falso-positivo zero em corpo tcf (literais escapam
  dígitos); **limite**: corpo raw é verbatim e a junção lá segue indetectável.
- **Contador RLE exige `N >= 2` em dígitos ASCII**: `*0|`, `*1|`, negativo e grafias com
  sinal eram aceitos: linha sumindo ou fantasma sem erro (no seq-RLE, `*0+1|` emitia o
  template: 1 linha que o contador declara não existir). Todo o espaço rejeitado é
  inemissível pelo encoder.
- **`view`: `int` = POSIÇÃO em toda a superfície**, a mesma regra e faixa do `schema=`
  (ADR-0047: `str` = nome, `int` = posição, `0 <= pos < n`, bool excluído), na terceira
  porta pública que faltava. Junto: `select(0)` não é mais engolido por truthiness (escalar
  = sobrecarga de 1 coluna; `select([])` passa a significar *nenhuma* coluna) e `where` com
  `value` não-`str` levanta `TypeError` ensinante (respondia 0 linhas calado; valores
  decodados são `str`, `None` casa nulo).

## 0.8.0 (2026-08-23): `#TCF.8` default

**Mudança de formato**: `#TCF.8` vira o formato **DEFAULT** de emissão
([ADR-0032](docs/adr/0032-tcf8-default-format.md); minor acompanha o formato, ADR-0028). O ciclo
`0.7.2` (lazy+poda) foi **absorvido** neste release (sem release intermediário). Publicado no
PyPI (`tcf-format`) em 2026-08-23 via Trusted Publishing, tag `v0.8.0`.

### Formato e rotas

- **`#TCF.8M` é o default multi-col**: todo `encode(dict)` sai `#TCF.8M`, meta INLINE na
  assinatura (sem prefixo `# `), byte-sizes em **HEX**, última coluna sem size (`min_header`).
- **Single-col ganha header por default, 100% dos casos** (`#TCF.8\n`,
  [ADR-0034](docs/adr/0034-header-default-100-porcento-single-col.md)): o arquivo se
  auto-explica em vez de depender de quem o produziu (+7 B, inevitável e assumido).
- **`#TCF.8H` hierárquico SOLDADO** ([ADR-0033](docs/adr/0033-hierarchical-codec-weld.md)): o
  dataset aninhado que sua linguagem monta do JSON (objetos/arrays aninhados, `null`
  (distinto de ausente e de `"null"`), registros ragged, qualquer raiz) faz round-trip
  exato pela MESMA porta `encode`/`decode` (rota por tipo de entrada, simétrica ao decode
  por magic). O objeto é fatiado em colunas: nomes de campo escritos UMA vez, não por
  registro. Paridade com a classe D_json mapeada em
  [`docs/reference/json-equivalence.md`](docs/reference/json-equivalence.md).
- **Rota TIPADA single-col**: `list[bool]` / `list[int|float]` preservam o TIPO no wire
  (`#TCF.8b`/`#TCF.8n`): bool denso a 1–2 bits/elemento
  ([ADR-0037](docs/adr/0037-denso-b2-ternario-dominio-implicito.md)), união bool+str lazy
  `#TCF.8bB` ([ADR-0039](docs/adr/0039-lazytype-bool-cabeca-congelada-extras.md)), grafias
  canônicas congeladas ([ADR-0038](docs/adr/0038-indice-interno-default-core-tipado-bool.md)).
- **Candidatos novos no mesmo `min()` nunca-pior**: delimitador de POLARIDADE
  ([ADR-0035](docs/adr/0035-delimitador-de-polaridade-single-col.md); 1 byte por transição em
  vez de 1 por literal), **bN de domínio** para cardinalidade baixa
  ([ADR-0036](docs/adr/0036-bn-de-dominio-cardinalidade-baixa.md); k distintos em
  ceil(log2 k) bits/linha), **seq-RLE periódico** `*N~d1,..,dp|`
  ([ADR-0040](docs/adr/0040-seq-rle-periodico.md); o delta CICLA: 600 dias úteis em 1 marcador).
- **Todo nome de coluna é representável**: separadores escapados com `\`
  (único proibido: `\n`); nome VAZIO `''` preservado via sentinela `\z`
  ([ADR-0046](docs/adr/0046-nome-vazio-8m-porta-o-z-do-8h.md); fecha o único caso em que o
  TCF alterava o dado); coluna anônima/posicional SÓ via `drop_names`.
- **Legado `#TCF.6`/`#TCF.7` cortado** de `src/tcf` (emit E decode): fail-loud com dica de
  git. Git-as-compat ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)): versão
  antiga se reproduz por checkout, não por bagagem no código. Sem modos de compatibilidade
  até o 1.0 (decisão reafirmada do owner).

### Specs (natures)

- **`schema=` é o parâmetro ÚNICO de spec** nas duas portas
  ([ADR-0047](docs/adr/0047-schema-parametro-unico-de-spec.md)); `nature=`/`nature_per_col=`
  CORTADOS (seco, sem alias: mesmo regime do legado). Formas: `"cpf"` (name do registry) ·
  objeto spec · `{coluna: spec}` com chave str=NOME / int=POSIÇÃO. É **incremental**
  (default = string semântico; o schema muda um ou mais) e tem **sobrecarga** (tabela/wire de
  UMA coluna aceita a forma escalar). Exports novos: `SPEC_DATA_ISO`, `SPEC_INT_PAD`,
  `SPEC_REGISTRY`.
- **Registry com 5 specs**: cpf, cnpj, ip, **data-iso** (`:dt`, ISO→ordinal, casa com o
  seq-RLE) e **int-pad** (`:ipad`). Identidade em DOIS planos
  ([ADR-0041](docs/adr/0041-spec-id-tres-planos.md)): `name` legível na API, `wire_id` curto
  no header; fail-loud de grafia, colisão e mascarada; header autoritativo no decode.
- **CNPJ alfanumérico** (IN RFB nº 2.229/2024, vigente desde jul/2026): **UM spec só**
  ([ADR-0044](docs/adr/0044-cnpj-um-so-alfanumerico.md)); corpo 100% decimal segue emitindo
  os 7 chars **byte-idênticos** ao wire legado (compacto por valor,
  [ADR-0043](docs/adr/0043-cnpj-um-so-compacto-por-valor.md)); o decode discrimina pelo
  comprimento.
- **Bordas em valor de spec** ([ADR-0045](docs/adr/0045-bordas-em-valor-de-spec.md)): regex
  fechada com `\Z` (o `$` do Python também casa antes de um LF final; o RT perdia o
  caractere); telemetria `format_bordered` distingue "dado certo, pipeline sujo" de "forma
  desconhecida".
- Telemetria (`SideOutputs`) virou **opt-in**: 3,9–31,1% do tempo de encode devolvidos ao
  caminho comum; wire byte-idêntico.

### API e congelamento do `.8`

- **Porta única**: `encode()` roteia por tipo de entrada (list/dict/aninhado/tipado);
  `decode()` pelo magic. `encode_hierarchical` e afins fora da superfície pública.
- **Congelado por teste executável**: assinaturas de `encode`/`decode` (nome, ordem, kind e
  default de cada parâmetro) e a superfície de exports (`EXPECTED_PUBLIC_API`) pinadas em
  `tests/test_regression_v1_baseline.py`; header e corpo pinados pelos gates byte-canônicos.
- **Baselines na data desta entrada**: D1-D9 = **1545 B** · D17a = **300 B** (`#TCF.8M` hex
  inline) · real-world = **89 430 B** · suíte **1344 passed**. Números vivos SEMPRE nos
  testes; re-pináveis com registro (ADR-0024).
- `view()` lazy/consultável segue a API read-only do `.8M` (count/sum/where/select/group
  sem materializar o que a pergunta não toca).

> ADRs do ciclo: **0032–0047**. Narrativa por sessão: `experiments/lab/dirty/notas/diario/`.

## 0.7.x (pré-1.0, superado por 0.8.0): `#TCF.7` default (histórico)

Ciclo "perseguir bytes" (abertura do que era chamado v2.0; agora pré-1.0).
`encode(dict)` multi-col sai em `#TCF.7` por default. Single-col inalterado.

- **V2-A fallback identity** ([ADR-0022](docs/adr/0022-v2a-fallback-identity-weld.md)):
  por coluna `min(tcf, raw)`, marcador `!`.
- **Header minimo** ([ADR-0023](docs/adr/0023-v2-minimal-header-weld.md)):
  meta sem prefixo `# ` + ultima coluna sem size.
- **V2-B dicionario/categorico** ([ADR-0025](docs/adr/0025-v2b-dictionary-categorical-weld.md)):
  3o candidato do fallback `min(tcf, raw, v2b)`, marcador `@`. Coluna low-card
  vira [tabela de unicos]+[stream de indices]. 13.9% weighted em 8 datasets reais.
- **Split estrutural** ([ADR-0026](docs/adr/0026-structural-split-weld.md)):
  4o candidato `min(tcf, raw, dict, split)`, marcador `%`. Valor estruturado
  (decimal/data/datetime/id) com template uniforme vira campos (template 1x) ->
  cada campo low-card cai no V2-B. **19.39% weighted** (maior lever do ciclo).
- **`sort_by` order-free** (O-FMT-02): `encode(table, sort_by="col")` reordena
  linhas pela chave (decode retorna a ordem ordenada).
- **Knobs**: `fallback`/`min_header` (opt-out, default True), `min_len` (override).
- **0.7 default** ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)):
  baseline D17a re-pinado 322->303B (#TCF.6 legado lido pelo decoder). D1-D9=1523B
  (single-col) inalterado. Suite 398 passed.
- **Fechamento do ciclo (2026-06-15)**: decisao do owner, **0.7 permanece
  lossless-puro**; V2-C round e Pacote 10 (loss amplo) viram roadmap v2.0. Nome de
  distribuicao = **`tcf-format`** (mantendo `import tcf`); `pyproject` `1.0.0` ->
  `0.7.0` (alinha ADR-0024). [ADR-0018](docs/adr/0018-v2-format-roadmap.md) ->
  `accepted` (V2-D refutado; V2-C/J/K/L defer). Higiene de tickets: 3 fases welded
  fechadas + 5 parks v2.0/pos-0.7.
- **`0.7.1`, primeira release publicada no PyPI** (`tcf-format`): o **patch** e'
  contador de release/correcao, desacoplado do minor do formato (`#TCF.7`) e do
  comportamento (nao muda logica nem byte-output). D1-D9=1523B / D17a=303B intactos.

---

## 1.0.0 (2026-05-27): **STABLE**, format #TCF.6 + API congelados

Primeira versao estavel. Decisao formal de freeze em
[ADR-0017](docs/adr/0017-format-spec-v1-frozen.md).

### Estabilidade garantida (semver)

- **Format `#TCF.6` imutavel** ate' v2.0.0: nenhum byte de arquivo TCF
  v1 muda entre versoes 1.x.y
- **API publica congelada**: `encode`, `decode`, `SideOutputs`,
  `PipelineConfig`, `build_schema`, `TableSchema`, `ColumnSchema`,
  `TemplatedCheckedSpec`, `TemplatedPaddedSpec`, `SPEC_CPF`, `SPEC_CNPJ`,
  `SPEC_IP` (+ deprecated `encode_table`/`decode_table`)
- **Semver**: 1.0.x bug fixes / 1.x.0 additive / 2.0.0 breaking

### Validado

- D1-D9 sinteticos: 1523B (53.2% ratio), RT 9/9
- D17a multi-col: 322B INVARIANT (preservado em 16 ADRs)
- Real-world: Adult Census + TPC-H 9 tabelas (-33.02% weighted) + 3 UCI
  novos (wine 90.9%, beijing 71.7%, online-retail 23.7%)
- Benchmark vs csv/jsonl + gzip/brotli/zstd: TCF vence 7/9 datasets
- Suite: 262 passed + 2 xfailed (test_regression_v1_baseline.py: 24
  tests gate byte-canonical + API surface)

### Bug fixes incluidos (categoria 1, output era invalido)

- HCC seq-RLE multi-delta: marker `*N+-1,0|...` (primeiro delta negativo
  double-signed) era emitido mas decoder rejeitava com `ValueError`.
  Fix em `src/tcf/composicional/hcc_seqrle.py`. Descoberto em validacao
  real-world wine-quality (2026-05-27). 2 testes regressao.

### Packaging

- `pyproject.toml`: version 1.0.0; wheel empacota `src/tcf` canonical
  (corrigido de `old/tcf` v0.5 stale); `requires-python = ">=3.10"`
- `src/tcf/__init__.py`: `__version__ = "1.0.0"`
- CI: gate bloqueante `test_regression_v1_baseline.py` + PYTHONHASHSEED=0
  + matrix py 3.10-3.13

### Deprecated (removido em 2.0.0)

- `encode_table(table)` → use `encode(dict)`
- `decode_table(text)` → use `decode(text)`

---

## v0.6 (2026-05-10 → 2026-05-27): TCF (Tabular Compact Format), superseded por 1.0.0

**Reset em 2026-05-10**: foco do projeto migrou de "formato textual
columnar para LLMs" (v0.5) para **algoritmo de compressao de strings
tabulares** em duas camadas. Trabalho em `experiments/lab/dirty/`
(macros M0-M14) consolidado e welded para `src/tcf/`. Estabilizado
como 1.0.0 em 2026-05-27.

### Naming oficializado (2026-05-17, META-NAMING)

- **TCF** = **Tabular Compact Format** (projeto)
- **OBAT** = **Online Bidirectional Affix Tokenizer** (codnome `alg16`)
- **HCC** = **Hierarchical Compositional Coding** (codnome `M8.A`)

Ver `docs/algorithms/` para documentacao tecnica detalhada de cada
camada.

### Componentes canonicos

- **OBAT** (camada 1, tokenizacao): online incremental via LCP+LCS
  bidirecional. Tokens raiz: TokLit / TokRefPref / TokRefSuf.
  Intocado desde M0 (exp 16 do alg16).
- **HCC** (camada 2, compactacao): detector unificado (refs atomicos
  + virtuais no mesmo espaco) + emit composicional (`~` cria ref
  auto-nomeado, `,` concat efemero); restricao body-order para
  inline expansion correto; range `a..b` como caso particular.
- **Convencao output**: sem brackets `[`/`]`, LF only.

### Resultados validados

- D1-D9 (stress 9 datasets sinteticos): 1615 bytes em 2981 raw =
  **54.2% ratio medio**. Varia 26% (D8 cabeca-cauda) a 72% (D4 caos).
- RT 9/9 OK em todos os datasets.
- Cadeia byte-canonica: M9 → M10 → M11 → M12 → M13 → M14 (welding
  validado por contra-prova).

### Estado da API

```python
from tcf import encode, decode  # API publica v0.6

text = encode(["abc", "abcd", "abcde"])
values = decode(text)
```

### Phase 1 LLM (acessorio)

LLM benchmark (Q01-Q38 em `docs/findings/`) e' agora **acessorio**
ao foco. Codigo v0.5 (`old/tcf/`, antes `src/tcf/`) mantido para
referencia historica.

Ver:
- [`experiments/lab/dirty/notas/2026-05/historia-dirty-lab.md`](experiments/lab/dirty/notas/2026-05/historia-dirty-lab.md): narrativa M0-M14
- [`experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md`](experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md): 12 direcoes futuras
- [`docs/algorithms/`](docs/algorithms/): OBAT, HCC, TCF-format

---

## v0.3-research (2026-04-27): research-grade (HISTORICA)

**Repository reorganization**: GitHub-style README, manual with 7 chapters
(EN + 3 PT-BR), findings catalogue split by theme into `docs/findings/`,
workbench (tickets + research notes + dev/science timelines) under
`docs/workbench/`, theory snapshot under `docs/theory/`. Removed obsolete
`data/` and `data-local/` from repo root. Tickets moved from
`tickets/` to `docs/workbench/tickets/`.

**M-schema-scope finished**: F-Q37 (schema scope doesn't degrade N0;
sub-finding: models infer `Supplier#NNN` from lexical patterns even
without `supplier` table visible; TPC-H memorization caveat) and F-Q38
(schema reduced **helps** in natural wordings: -33pp in N3 between
minimal and full schemas; empirically justifies schema pruning literature).

## v0.2.6-anthropic (2026-04-26): Anthropic family added

`commercial_client.py` extended for Anthropic Messages API:
- haiku 4.5 + sonnet 4.6 with `thinking={"type":"enabled","budget_tokens":2048}`
- opus 4.7 with `thinking={"type":"adaptive"}` + `output_config.effort`
  (different API!)
- 1968 records over 4 paradigms × 7 commercial models. Total spend
  $9.46 USD with prompt caching (~75% savings).

Findings:
- **F-Q36**: Anthropic ≈ OpenAI in Linha B (96-99% Adult, 80-88% TPC-H);
  OpenAI wins Linha A Adult (gpt-5.x 82-95% vs Anthropic 76-80%);
  paridade in Linha A TPC-H. claude-sonnet-4-6 wins TPC-H Linha B
  (88.1% > gpt-5.4 85.7%).

## v0.2.5-openai (2026-04-26): OpenAI commercials

Migrated `commercial_client.py` to **OpenAI Responses API** (recommended
2026 path), added structured outputs via Pydantic, prompt caching with
`prompt_cache_key`, tiktoken-based count_tokens.

Models: gpt-5.4, gpt-5.4-mini, gpt-5.4-nano, gpt-4o-mini (control).
1008 records (Linha A + B × Adult + TPC-H), $3.17 USD.

Findings:
- **F-Q31**: commercial reasoning models break the local Linha A ceiling
  (gpt-5.4 95% vs locals capped ~57%). The discriminating axis is
  REASONING, not size.
- **F-Q32**: gpt-5.4 + mini = **100% in all naturalness levels** for
  Adult Linha B.
- **F-Q33**: locals lose -30 to -45pp in TPC-H Linha B with N2
  wording; schema ambiguity systematic in multi-table.
- **F-Q34**: same applies to commercial top models; schema ambiguity
  is universal/paradigm-independent.
- **F-Q35**: Linha A commercial in TPC-H caps at 60-76%; even
  gpt-5.4 falls 21pp from Adult to TPC-H.

## v0.2.4-naturalness (2026-04-26): naturalness axis (locals only)

Introduced **N0..N3 naturalness taxonomy** for question wordings:
- N0: schema-aware (literal column names, technical hints)
- N1: system-aware (domain-aware prose)
- N2: business-intent (no schema mentions)
- N3: business + implicit context

Implementation: `experiments/eval/llm_eval/question_naturalness.py` with
28 wordings × 2 datasets, runners adapted with `--naturalness` flag.
N0 byte-identical to legacy questions for backwards compat.

Findings:
- **F-Q29**: naturalness does NOT degrade Linha A in 13 local models
  0.6B-20B (delta < 5-14pp, within Wilson CI). Mechanism: arithmetic
  ceiling dominates; wording is invisible below it.
- **F-Q30**: naturalness DEGRADES Linha B in locals selectively (qwen3:14b
  immune; qwen2.5-coder -15pp). Two mechanisms: domain-semantic ambiguity
  + hyphenated columns.

ScoringConfig dataclass added with `string_match=lenient` default
(strict still available for legacy comparability).

## v0.2.3-canonical (2026-04-25): canonical datasets baseline

`scripts/setup_adult.py` and `setup_tpch.py` for reproducible canonical
ingestion. `scripts/csv_to_sqlite.py` builds SQLite hubs in
`<data_root>/interim/`. Stratification metrics inline (TVD/JSD/Hellinger/
Wilson CI).

Findings:
- **F-Q24**: canonical TPC-H ≈ synthetic retail in accuracy under same
  protocol; synthetic was representative.
- **F-Q25**: H-TCF2 generalizes to single-table (Adult Census) with
  hyphenated columns. 100% Linha B local.
- **F-Q26**: random ≈ stratified in Adult; paradigm robust to sampling
  choice ("floor effect" of 100% accuracy).
- **F-Q27**: SQL quality structural metric correlates **inversely** with
  accuracy. Discarded.
- **F-Q28**: Linha A in canonical Adult = 52% bimodal (100% on full-table
  agg, 0-11% on filter+agg). Refines F-Q12.

## v0.2.2-shaper (2026-04-25): unified data pipeline

`scripts/shaper/` framework with 7 strategies (schema_filter, join,
compressibility, stratify, fk_preserving, volume, ordering).
`experiments/eval/data_sources.py` provides single entry point
`load_dataset(source, **kwargs)` for both synthetic and canonical.

All M-runners migrated to `load_dataset` (no more direct fixture imports).

## v0.2.1-mseries (2026-04-15..04-23): M1..M9 experiment runs

13 M-series runners exploring Linha B (LLM → SQL) systematically across
synthetic and canonical datasets. Findings F-Q13..F-Q23 (schema-only,
fewshot, cross-domain, format, intermediate forms, filter questions,
HAVING, complex queries, error types, style hints).

## v0.2.0-encoder (2026-04-10..04-13): encoder/decoder v0.2

Rewrote encoder/decoder with separated `compression.py` module.
Public API: `encode`, `encode_rows`, `decode`, `EncodeConfig`. CLI
modernized.

## v0.1-llm-comprehension (2026-04-04..04-10): Phase 1 LLM testing

Phase 1 ran 12 local models × 4 formats × 4 questions to test LLM
comprehension of TCF. **TCF 43% < JSONL 63%** in raw accuracy: pivot
to Linha B as the high-value path. F-Q1..F-Q12 catalogued.

## v0.0-prototype (2026-04 first week): initial sketch

First handcrafted draft of the columnar text format. Encoder/decoder
v0.1 written in two weeks (`src/tcf/encoder.py`, `decoder.py`).
Roundtrip CSV → TCF → CSV verified. Format had conceptual issues
(DICT with `=`, `[sorted]` confusing, redundant IDs); kept as
historical reference in `docs/archive/`.

---

## Roadmap (open)

- v0.3: schema_qualifier (auto-prune schema for N2/N3 wordings before LLM)
- v0.3: numeric precision (open issue 23)
- Future: TOON benchmark integration (head-to-head Adult/TPC-H)
- Future: Shaper as standalone pip package
