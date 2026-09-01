<!-- l10n: doc_id=readme · lang=en · canonical -->
**English** · [Português](README.pt-BR.md)

# TCF · Tabular Compact Format

[![CI](https://github.com/LeoPR/TCF/actions/workflows/ci.yml/badge.svg)](https://github.com/LeoPR/TCF/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-0.8.4%20(pre--1.0)-orange)
![Format](https://img.shields.io/badge/format-%23TCF.8%20default-blue)

> **What if you could transmit the same table with far fewer bytes,
> without turning it into a binary blob nobody can open and read anymore?**

**Documentation**: [the manual](docs/README.md) · [short guide](README.pypi.md) · [step-by-step tutorial](docs/tutorials/getting-started.md)

## What TCF is

A **textual**, **lossless** format (`decode(encode(x)) == x`) for tables of strings.

It compresses somewhat like a zip/gzip, with one difference: the result **stays ASCII text that you
open and inspect**, without decompressing. Each column goes through its own pipeline.

The more TCF factors, the denser that text gets, so it reads less obviously than the original. It
never turns into an opaque blob, though.

That is the niche TCF occupies: **compact like a compressor, inspectable like text**.

Need maximum ratio? You can run gzip/brotli on top: they compose.

## Getting started (1 minute)

```bash
pip install tcf-format        # or: uv pip install tcf-format
```

The **distribution** is called `tcf-format`; the **importable package** is `tcf`, with no
runtime dependencies.

```python
from tcf import encode, decode

# Single-column: a list of strings
text = encode(["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"])
assert decode(text) == ["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"]

# Multi-column: a dict of columns
table = {
    "id":    ["1", "2", "3"],
    "email": ["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"],
}
text = encode(table)
assert decode(text) == table  # lossless round-trip

```

`encode` dispatches on the **shape** of the input. A list of values becomes a single
column, a dict of columns becomes a table, and a list of flat records becomes that same
table, with the record form noted in the header so `decode` hands the list back. `decode`
itself routes by the format signature.

Pre-1.0 (ADR-0024): the package is at `0.8.4`. The *minor* tracks the format
(`#TCF.8`) and the *patch* is a release counter, decoupled from behavior.

Structured values (CPF, CNPJ, IP) have opt-in *natures* that shrink the column further:
see [Nature filters](#nature-filters-opt-in).


Step-by-step tutorial: [`docs/tutorials/getting-started.md`](docs/tutorials/getting-started.md).
Practical guides: [`docs/how-to/`](docs/how-to/).

## Why it is smaller: the same data in three formats

A small record set, in three formats (real bytes, real output):

**JSON** *(451 B)*: repeats every field name on every row. Measured **compact**
(`separators=(',', ':')`), the same footing as the CSV and JSONL below; indented here only so
you can read it.

```json
[ { "nome": "Ana Souza",  "email": "ana@acme.com.br",
    "cidade": "Sao Paulo", "plano": "Premium",
    "cpf": "111.111.111-11" },
  { "nome": "Bruno Lima", "email": "bruno@acme.com.br",
    "cidade": "Sao Paulo", "plano": "Premium",
    "cpf": "222.222.222-22" }, … ]
```

**CSV** *(277 B)*: drops the repeated names, one line per record.

```csv
nome,email,cidade,plano,cpf
Ana Souza,ana@acme.com.br,Sao Paulo,Premium,111.111.111-11
Bruno Lima,bruno@acme.com.br,Sao Paulo,Premium,222.222.222-22
Carla Nunes,carla@acme.com.br,Sao Paulo,Basic,333.333.333-33
Diego Rocha,diego@acme.com.br,Rio de Janeiro,Premium,444.444.444-44
```

**TCF** *(242 B, format 0.8, real `encode` output)*: what repeats becomes a reference; what is unique
stays raw.

```
#TCF.8M!2c=nome,2a=email,1c=cidade,14=plano,!cpf
Ana Souza
Bruno Lima
Carla Nunes
Diego Rochaan*a*@acme.com.br
brun*o3
carl2,3
dieg5,3
*3|Sao Paulo
Rio de Janeiro
*2|Premium
Basic
^1
111.111.111-11
222.222.222-22
333.333.333-33
444.444.444-44
```

**TCF + CPF nature** *(210 B)*. Here an opt-in CPF filter, called the `cpf` *nature*, shrinks even
a column with no repeated values.

```
#TCF.8M!2c=nome,2a=email,1c=cidade,14=plano,!cpf:cpf
Ana Souza
Bruno Lima
Carla Nunes
Diego Rochaan*a*@acme.com.br
brun*o3
carl2,3
dieg5,3
*3|Sao Paulo
Rio de Janeiro
*2|Premium
Basic
^1
%g$.u
)K%7l
.1&Cc
0r(LU
```

The `cpf` column carries no factorable repetition, so the default pipeline stores it raw (`!cpf`).

The `cpf` *nature* takes another route. It removes the punctuation and the check digit, keeps the 9
useful digits in a compact form, then rebuilds the original value on `decode`. The header records
`:cpf` only when the result comes out smaller. Each value then goes from 14 characters to 5
(`%g$.u` = `111.111.111-11`).

**How to read it**. The example data uses Portuguese field names, `nome`=name, `cidade`=city,
`plano`=plan and `cpf`=Brazilian tax ID, kept verbatim because the byte counts are measured from it.

- Line 1, the format signature and inline meta: `#TCF.8M` is format 0.8, multi-column;
  sizes are hexadecimal.
- The column meta (`size=name`) uses `!` for raw, `@` for dictionary and `%` for structural
  split, whichever candidate wins. So `!` marks a column stored **raw**, meaning raw came out
  smaller than TCF.
- The last column (`cpf`) carries no size, since it runs to the end. It shows `!cpf:cpf`: the `!`
  says the general pipeline kept the body raw, and `:cpf` names the filter, so `decode` reverses it
  without being handed that filter.
- The bodies come concatenated, **delimited by size, not by line break**.
  That is why the raw `nome` column (`…Diego Rocha`) runs straight into the email (`an*a*…`).
- In the body: `*3|Sao Paulo` means *"Sao Paulo, 3×"* (a repetition).
  `^1` means *"same as line 1"* (a substitution).
- In the **email** column TCF goes deeper (unique prefix + a referenced common domain).
  That is where it saves the most, and where the text gets densest.
- The **`cpf`** nature is opted in via `schema={"cpf": SPEC_CPF}`, as in the two blocks above.
  *Those CPFs are repeated-digit placeholders: mod-11-valid, but never issued by the tax office,
  so they are safe fakes. See "Nature filters" below.*

**And now the same records, nested**: the JSON your API actually sends.

Since 0.8, TCF round-trips the **dataset your language builds from JSON**, meaning nested
objects/arrays, `null`, and typed `true`/`false`/numbers. It reads the *dataset* (dict / list /
scalar), never the JSON text.

**JSON** *(184 B)*:

```json
[ {"nome":"Ana Souza","cpf":"111.111.111-11","ativo":true,"fones":["11 98765-4321","11 3555-0100"]},
  {"nome":"Bruno Lima","cpf":"999.999.999-99","ativo":false,"fones":["21 99888-7766"]} ]
```

TCF *shreds the object into columns*, one per field. Field names are therefore written **once** in
the header, not once per record, and the same opt-in `cpf` nature from the flat table applies here.

**TCF + CPF nature** *(144 B, real `encode` output)*. Nested input routes to `#TCF.8H`:

```
#TCF.8Hnome:21,cpf:12:cpf,ativo:11b,fones#:6[
Ana Souza
Bruno Lima
%g$.u
AJ/}}
true
false
\2
\1
\11 *\98765-\4321
1\3555-\0100
\21 \99888-\7766

```

- `cpf:12:cpf` is the same opt-in **`cpf` nature** as the flat table above: it strips the punctuation
  and check digit, so the two values compress to `%g$.u` / `AJ/}}`; the trailing `:cpf` lets `decode`
  rebuild them without being told the filter.
- `ativo:…b` is a **typed bool**: `true`/`false`, distinct from the string `"true"`; a number field
  would carry a type tag too.
- `fones#:…[` is an **array** column; the lengths are their own column (`\2`, `\1`: *2 phones, then 1*),
  so you count the structure **without expanding it**. Digits get a `\` escape so they never collide
  with the reference syntax (`\11 ` = `11 `); `decode` reverses it exactly.

The whole JSON class round-trips byte-exact: nested objects/arrays, `null` (distinct from absent and
from `"null"`), ragged records, any value at the root. Full mapping and the declared frontier:
[`docs/reference/json-equivalence.md`](docs/reference/json-equivalence.md).

JSON repeats the whole structure.
CSV repeats the values.
**TCF factors out what repeats**, references the rest and **keeps unique data raw** without
inflating, all while staying **ASCII text you can open and read**.

But the deeper it factors (look at the email), the denser the text gets.
*Readable does not mean obvious at first glance.*

On large tables the gap grows: see [Results](#results).

## How it does it: OBAT + HCC

Two layers, explained by purpose. The specs live in [`docs/algorithms/`](docs/algorithms/).

**OBAT** (Online Bidirectional Affix Tokenizer) *finds what the strings have in common*.

For each value, it looks for the longest prefix **and** suffix shared with earlier ones: email
domains, URL roots, codes of the same family. It writes the shared piece once and references the
rest.

This is **bidirectional front-coding**: it generalizes the classic front-coding of string
dictionaries (Witten et al.; HTFC/RPDac, Brisaboa et al.). The "bidirectional" part is what
captures the shared **suffix** (`@acme.com.br`), not just the prefix.

The affix search belongs to the **prefix/suffix tree** family: tries, **Patricia/radix tree**
(Morrison 1968), suffix trees. In practice OBAT speeds that search up with a **trigram index**,
which drops the naive O(N²) cost to ~O(N^1.42), sub-quadratic and near-linear.

Swapping the index for a Patricia trie is a future candidate:
[exploration](docs/theory/estrutura/patricia-trie-exploration.md).

**HCC** (Hierarchical Compositional Coding) *decides what is worth naming and groups repetitions*.

It takes OBAT's tokens and factors recurring compositions into **reusable named references**, built
with the `~` operator. It also collapses repeated runs, including near-identical sequences like IDs
that only change at the end.

Since a reference can point to another reference, the result forms a **directed acyclic graph (DAG)
of fragments**: in practice a *grammar*, or straight-line program, of the content.

That is the spirit of **Re-Pair** (Larsson & Moffat 1999) and **Sequitur** (Nevill-Manning & Witten
1997). The difference: TCF operates on OBAT's **tokens** rather than on bytes, and brings its own
operators (`~` creates a named node, `,` just concatenates).

That is what keeps the output small **and** inspectable: the `*N|...` repetition groups stay
in plain sight.

**Speed.** The expensive side is the **encode**, meaning OBAT's affix search. The trigram index
brings it to near-linear, with the optional Cython accelerator on top.

The **decode** takes a **single linear pass**: it expands references with O(1) lookups, expands
repetition groups, and searches for nothing at all. Fast and predictable.

## Nature filters (opt-in)

**A spec is not a type, and the difference is the point.** Two separate claims live here. The *wire*
is always text, and the **data comes back in the type it went in as**.

Strings return byte for byte. `True` and `3.14` come back as a **bool** and a **float**, never as
the spelling `"True"`. TCF reads the type on the way in, marks it in the header (`#TCF.8b`,
`#TCF.8n`), then reconstructs the **value** rather than the text that represented it:

```python
from tcf import encode, decode

assert decode(encode([True, False])) == [True, False]    # bool, not "True"
assert decode(encode(["True", "False"])) == ["True", "False"]   # here, strings
```

A spec is a different layer: a hypothesis about the **shape** of a text.

| | input type (`bool`, `int`, `float`) | semantic spec (`cpf`, `cnpj`, `ip`) |
|---|---|---|
| who asserts it | **your language**: the value already is a bool | **TCF**, as a hypothesis: *"has the shape of a CPF"* |
| what comes back | the same value, same type (`True`, not `"True"`) | the **original string**, byte for byte |
| when it does not match | not applicable, the type is a fact | falls back to literal: **no failure, no loss** |
| what you gain | the type preserved, plus bits (1-2 per bool) | bytes on the wire |

So a spec is a **compression hypothesis about the form**, not a claim about the data's identity.

It is opt-in per value, and **never-worse**: it competes with the ordinary pipeline and wins only
when it shrinks. A value that does not match the shape becomes a literal in the same column.

It is also **self-describing**. When it wins, the header carries the id (`:cpf`) and `decode`
reverses it without being told.

TCF never validates semantics: it does not check whether a CPF *exists*.

Some values have **known structure** that a generic compressor does not exploit. A CPF
`123.456.789-09` is really just **9 useful digits**: the punctuation is fixed, and the final 2
digits, the check digits, are **derivable** from the other 9.

A *nature filter*, opt-in, uses that:

- **encode** strips the punctuation, stores the 9 digits as a short number (safe base, ~5 chars;
  the current alphabet has 80 usable characters)
  and **discards the check digit**;
- **decode** **recomputes** the check digit (mod-11) and reinserts the punctuation, an **exact** reconstruction.

Each nature is a candidate, not a mandatory transformation. For each column, TCF compares the
complete blob, including the header that identifies the filter.

If the filtered version comes out larger, TCF keeps the ordinary encoding and omits `:id`. Tests
showed why that matters for CNPJ: the filter reduced synthetic columns but increased a real ordered
table, and the measured cases are recorded in [`T-SPEC-STATUS-08`](tickets/T-SPEC-STATUS-08.md).

Filters already implemented ([ADR-0015](docs/adr/0015-natures-templated-checked-weld.md)):

| filter | format | what decode reconstructs |
|---|---|---|
| `SPEC_CPF`  | `NNN.NNN.NNN-DD`     | punctuation + 2 check digits (mod-11) |
| `SPEC_CNPJ` | `AA.AAA.AAA/AAAA-DD` | punctuation + 2 check digits (mod-11) |
| `SPEC_IP`   | IPv4 `N.N.N.N`      | dots + canonical octets (normalizes to make subnet repetitions visible) |

`A` = alphanumeric `[0-9A-Z]`, `N` = digit, `D` = check digit.

**The CNPJ body is alphanumeric** since IN RFB 2.229/2024, in force from Jul/2026. The 12 body
positions accept `0-9A-Z`, and only the 2 check digits stay numeric.

A fully numeric CNPJ is a *case* of the alphanumeric one. It still encodes to the same 7 chars as
before, and `decode` tells the two apart by length.

The same filter mechanism works for **numbers**. `SPEC_IP` above is already numeric, over octets,
and the difference-based pipeline captures numeric sequences and IDs with cadence on its own, via
`*N+delta|`.

**Decimal / monetary / precision** specs are on the roadmap. They cross into lossy → 2.0.

```python
from tcf import encode, decode
from tcf import SPEC_CPF

# Repeated-digit placeholders: they PASS the mod-11 check (so the nature
# compresses them), but the tax office never issues them, so they do not map
# to a real person: safe for public examples.
cpfs = ["111.111.111-11", "222.222.222-22", "333.333.333-33", "444.444.444-44"]

blob = encode(cpfs, schema=SPEC_CPF)   # the nature WINS here (4 distinct CPFs)
print(blob)
# #TCF.8 :cpf     <- self-describing single-col header: the spec IS applied
# %g$.u           <- "111.111.111-11" (14 B) -> 5 chars: 9-digit body in base-80,
# )K%\7l             the mask and the 2 check digits dropped (decode recomputes them)
# .\1&Cc
# \0r(LU
assert decode(blob) == cpfs            # decode reads `:cpf` from the header, no spec needed

# Same 4 CPFs: 69 B single-col without the nature -> 39 B with it (-43%). In a table,
# pass it per column: encode(table, schema={"cpf": SPEC_CPF}); the cpf
# column's inline meta then carries `:cpf` (e.g. `#TCF.8M!15=nome,!cpf:cpf`).
```

Three honest details:

- Core natures are **opt-in and self-describing when they win**: single-column output carries
  `#TCF.8 name:id`; multi-column output carries `:id` in the inline meta. `decode(blob)` recognizes
  the official `cpf`, `cnpj` and `ip` filters automatically.
- A custom spec can also be used, but its decoder declaration must match the header ID exactly:
  `decode(blob, schema=custom_spec)` or `decode(blob, schema={"col": custom_spec})`.
- A value that does not match (invalid check digit, masked format) falls back to **literal** (`_`) without
  ever breaking the round-trip: the filter **never corrupts** the data.

> **Scope note.** CEP, RG, driver identification, telephone and generic fixed-alphabet codes were
> explored in a separate lab. They are not canonical `.8` specs yet; see the measured decision in
> [`T-SPEC-STATUS-08`](tickets/T-SPEC-STATUS-08.md).

## Format 0.8 (default): where the bytes go

Multi-column `encode` emits **0.8 / `#TCF.8M`** by default, see
[ADR-0032](docs/adr/0032-tcf8-default-format.md). Five things happen, all automatic (no flag), with
each column choosing the smallest representation:

- **Per-column fallback.**
  Stores the column raw when raw is smaller than TCF ("never worse than raw").
  Marked with `!` in the meta, see [ADR-0022](docs/adr/0022-v2a-fallback-identity-weld.md).
- **Low-cardinality dictionary.**
  A column with few distinct values becomes a table of uniques + compact indices,
  instead of one ref per row. Marked with `@` in the meta, see
  [ADR-0025](docs/adr/0025-v2b-dictionary-categorical-weld.md).
- **Structural split.**
  A structured value (decimal, date, datetime, CPF) with a uniform template becomes separate
  fields, the template stored once, and each low-card field then falls into the dictionary.
  Marked with `%` in the meta, see [ADR-0026](docs/adr/0026-structural-split-weld.md).
- **Minimal header.**
  The `M` flag in the signature already declares that columns follow. So the meta goes inline,
  sizes are hexadecimal, separators in names are escaped, and the last column carries no size.
  See [ADR-0023](docs/adr/0023-v2-minimal-header-weld.md).
- **Filters for structured values.**
  CPF/CNPJ/IP are optional candidates, and the encoder compares each option with the ordinary
  column encoding, using the complete blob. If the filtered version is not smaller, it keeps the
  original column and emits no `:id`.

A **list of flat records** takes the same route. A rectangular `list[dict]` is canonicalized
into columns and comes out as `#TCF.8R`, the very `#TCF.8M` wire with the discriminator
swapped, so `decode` knows to hand the list of dicts back. See
[ADR-0049](docs/adr/0049-marcador-r-a-forma-da-entrada-e-metadado.md). An input the
canonicalization refuses stays in `#TCF.8H`: a ragged record, nesting, an array in a cell,
a key that is not a string, or a line break inside a name or a value.

```python
text = encode(table)        # 0.8 / #TCF.8M, the default, no flags

# opt-out knobs (default True): to change the behavior / inspect:
text = encode(table, fallback=False, min_header=False)  # only TCF candidates, verbose meta
text = encode(table, min_header=False)                  # #TCF.8M with all sizes
text = encode(table, min_len=5)                         # override OBAT's min_len (default: auto)
text = encode(table, sort_by="email")                   # ALLOWS sorting rows by that column (order-free)
```

> `sort_by` **allows** reordering the rows by that column, and grouping equal
> values may buy fewer bytes. It is **order-free**: `decode` returns the same set
> of rows, and the original order does not come back. Use it only when row order
> does not matter.
>
> Since 0.8.4 the sort is a **candidate**, not an order: the encoder emits both
> versions and keeps the smaller one, so passing `sort_by` never grows the wire.
> That matters because sorting groups the key and scrambles every other column:
> measured, −43.0% when the companion columns are a function of the key, and
> +52.1% when they are independent of it. In practice the result may come back in
> the original order, when sorting did not help.

For the 5-column record set at the top, the default `#TCF.8M` output is **242 B**, with meta
`!2c=nome,2a=email,1c=cidade,14=plano,!cpf`.

That comes from the current fallback candidates and the minimal inline header. The `cpf` column
falls to **raw** (`!cpf`) instead of inflating, sizes are hexadecimal, and the last column carries
no size.

The gain is proportionally larger on **small payloads**.

Pre-1.0, the encoder only writes the newest format. Older blobs are reproduced via `git checkout`,
see [ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md).

The low-card dictionary (V2-B) and the structural split are already in the default. Lossy
compression stays on the [roadmap](docs/adr/0018-v2-format-roadmap.md).

## Status (pre-1.0)

- **Pre-1.0** ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)).
  The current format minor (`#TCF.8`) is a development iteration toward a **solid 1.0**, with no
  rigid compat between minors: git reproduces older versions. v2.0 comes later.
- Canonical implementation in [`src/tcf/`](src/tcf/).
  Round-trip is always lossless (`decode(encode(x)) == x`).
- Default **0.8 / `#TCF.8M`**: fallback, dictionary, structural split, hexadecimal inline meta,
  escaping and header-authoritative filter IDs, see the section above. Legacy `.6/.7` are recovered through git.
- Test suite: **2000 passed, 3 skipped** in the current local full run; run `pytest` for the
  number in your environment. Byte baselines = regression guards, re-pinnable on an intentional
  change, see [ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md).
- Changes: [`CHANGELOG.md`](CHANGELOG.md).
  M0-M14 history: [`experiments/lab/dirty/notas/2026-05/historia-dirty-lab.md`](experiments/lab/dirty/notas/2026-05/historia-dirty-lab.md).

> The **v0.5** cycle (columnar format for the LLM benchmark) is accessory and lives separately.
> See the "LLM Benchmark v0.5" section further down.

## Results

**With no compressor at all, TCF is the most compact _text_ format in the set.**
Across the 15 synthetic datasets in [EXP-008](experiments/lab/clean/EXP-008-compressao-comparada/):

| format (plain text, no compressor) | bytes |
|---|---:|
| **TCF** | **3131** |
| CSV | 4872 |
| JSON | 5409 |
| JSONL | 7001 |

~36% smaller than CSV and ~42% smaller than JSON, while staying readable.

> One caveat on the JSON and JSONL rows: EXP-008 renders them with Python's **default**
> `json.dumps` spacing, not compact, so both are larger than they need to be and the ~42%
> figure is an **upper bound**. The record-set table further down is measured compact and is
> the fair one to quote. Re-running EXP-008 compact is pending, not done.

Pinned in the test suite: D1-D9 = **1545 B**, 51.8% of raw, single-col; D17a multi-col = **300 B**,
in `#TCF.8M` with inline hexadecimal meta.

Real-world multi-column (9 Adult + TPC-H tables, 136k rows): **−33.02% weighted** vs raw CSV.

**And against gzip / brotli / zstd?** Not a competitor: a **layer underneath**. In transmission
`Content-Encoding` is negotiated by the transport and is **invisible to your code**. You do not
choose it against TCF, and you rarely see it at all: by the time your handler reads the body, it
has already been inflated. So the honest question is not *"TCF or brotli"*, it is *what does my
process hold and parse once the channel has done its invisible work*.

Where the compressor becomes a **visible** decision is at rest, in blocks on disk. There the
compressed blob is the thing you own, and opacity has a price you pay yourself: to read anything
at all you inflate everything, and `view()` cannot help, because there is nothing to read until
the whole payload exists again.

None of this makes the channel free. It spends memory and CPU to inflate, on every request; the
bill is just paid one layer down, where your code does not see it. It is part of the total, not
outside it.

On the **record set above**, under HTTP compression (`Content-Encoding`, max level):

| format | raw | gzip | br | zstd |
|---|---:|---:|---:|---:|
| JSON  | 451 | 206 | 195 | 197 |
| JSONL | 449 | **205** | 194 | 194 |
| TCF   | **242** | 206 | **185** | **193** |

Among the formats an API actually sends, TCF is the smallest **raw**: 242 B, against 449 for
JSONL and 451 for JSON, both measured compact. Compressed, it stays competitive. It wins under
`br` and `zstd`, ties JSON under `gzip` and lands within a byte of JSONL, all while staying
readable and queryable through `view()`.

CSV is smaller still: 277 B raw, and at this tiny size it edges TCF once compressed, 162 B
against 185 B under brotli.

Two honest caveats. CSV is rarely an API payload. And that gap closes and flips with volume,
as the next section shows.

The trade is explicit: **some ratio for readability**. And TCF **composes** with these compressors
rather than competing with them.

Its advantage in *ratio* shows up with volume. Inspecting, and querying selectively with
`view()`, hold at any size.

One difference only matters on small payloads. `gzip` carries fixed framing bytes in every
message, while `br` and `zstd` carry almost none.

> The numbers above use the compressors at **maximum level**, their best case. On a simple API
> compression is sometimes not even on, and when it is, it runs at a low default level: nginx
> gzip `1`, brotli `6`. See
> [compressor notes](experiments/lab/clean/EXP-008-compressao-comparada/notes/classificacao-compressores.md).

Across the aggregate of 15 synthetic **single-column** datasets (EXP-008, where the 0.7 multi-col welds
do not apply) the same story: `csv+brotli` = 1742 B against `tcf+brotli` = 2116 B. Full tables:
[EXP-008 reports](experiments/lab/clean/EXP-008-compressao-comparada/reports/).

**A note on scale: the record set above is tiny, 4 rows.**

On **real multi-column** data, thousands of rows, the picture **flips**: **full TCF + brotli beats
CSV + brotli**. Adult with 3,000 rows, `tcf-0.8+brotli` = **21.8 KB** vs `csv+brotli` = 30.4 KB (−28%).

On a tiny payload the framing dominates and there is nothing to factor. **TCF's advantage shows up
with volume**.

The same pattern holds across the **Parquet** compressor family (snappy, lz4, zstd), not just
the HTTP ones. What decides is not the container: it is the structure of the data.

On a **single dense free-text column**, the binary compressor wins on its own. Putting TCF
underneath generally hurts, and the loss reaches −41%, because TCF rewriting values as references
disturbs the compressor's entropy model.

A few cells come out roughly neutral. One of them, `lz4` on retail-description, actually gains 7%.

On a **structured multi-column table** the arithmetic flips. TCF wins on its own, −72% against CSV,
and it still composes, with `tcf+brotli` landing 30% below `brotli` over the raw data.

Measured with round-trip counter-proof. The lab is local and not versioned: the dirty lab
lives outside git, so the numbers here are the record, and the theory behind them is that
**structure decides, not the container**.

## Where 1.0 is headed: querying almost without decompressing

What TCF already does today points to the **1.0** goal: use the **compression's own structure
as an index**, to answer questions **almost without decompressing** and with **little memory**.

The textual output already carries hints that work as metadata:
- `*N|Sao Paulo` says there are **N equal rows** there, a **count/grouping** ready to go,
  without expanding the N items.
- `^1` says "same as line 1": multiplicity/dedup made visible.
- `*N+delta|template` describes a **progression** (e.g. sequential IDs) without listing
  each value.

In other words, you can **count elements, group, and even sum** by reading the markers,
materializing only the piece you need.

A compressed block on disk does the opposite. To scan it you **allocate memory and inflate
everything** first, and only then start reading. The same holds for a channel-inflated body: the
channel hands your process the whole payload, and from there the cost is yours.

That is the niche 1.0 wants to lock in: **compact and at the same time queryable**, not an opaque
blob.

The nature filters fit here, CPF/CNPJ/IP today and numeric ones on the roadmap. They add explicit
semantic structure without losing readability, and they are still evolving, as noted above.

### `view()`: SQL-like query paths with selective decompression *(core read-only API)*

A *lazy* API over the blob: it connects **without decompressing** and materializes only the column
(and rows) the aggregator needs. Filtering by something decompresses **only** what relates to it.

It is SQL-like in capability, not a SQL parser. Projection, equality/predicate filters, AND
chaining, aggregates and group operations are exposed as Python methods.

It does not implement joins, SQL parsing, NULL semantics, ordering/limit or a general query planner.

```python
from tcf import encode, view                    # public API since 0.8

# a small sales table: loaded from a CSV, a DB dump, wherever
table = {
    "cliente": ["Ana Souza", "Bruno Lima", "Carla Nunes", "Diego Rocha", "Eva Martins", "Ana Souza"],
    "cidade":  ["Sao Paulo", "Sao Paulo", "Sao Paulo", "Rio de Janeiro", "Sao Paulo", "Rio de Janeiro"],
    "plano":   ["Premium",   "Premium",   "Basic",     "Premium",        "Basic",     "Premium"],
    "valor":   [        120,          100,         170,              200,        80,               80],
}

blob = encode(table)                           # 187 B of ASCII text: this is what you store/transmit
v = view(blob)                                 # connects, decompresses nothing

v.count()                                      # 6        touches no column at all
v.distinct("cidade")                           # ['Sao Paulo', 'Rio de Janeiro']
v.n_unique("cliente")                          # 5
v.sum("valor")                                 # 750.0    touches: valor
v.where("cidade", "Sao Paulo").sum("valor")    # 470.0    touches: cidade, valor
v.group_sum("cidade", "valor")                 # {'Sao Paulo': 470.0, 'Rio de Janeiro': 280.0}
v.group_count("plano")                         # {'Premium': 4, 'Basic': 2}
```
*Real output: the table above `encode`s to a 187 B blob and round-trips exactly, with `valor`
coming back as `int`.*

The `touches:` line is the point. The filtered sum materialized **only** `cidade` + `valor`
(`report()` says 39.9% of the blob), and `cliente` and `plano` were never decompressed. A
`decode()`, or a gzip/brotli on top, would materialize all 4 columns **entirely** before any
computation.

Not every question is equally cheap, and the reference is explicit about which is which.
`count` reads the row count from the structure and builds nothing. On a dictionary column,
`where`, `distinct` and `group_count` answer over the K distinct values rather than the N
rows, walking the index stream **without expanding it**. The aggregators and `select` do
materialize the column they read. So the gain is largest on a wide table filtered by a
low-cardinality column, and near zero on a single high-cardinality column, which the docs
say out loud instead of hiding.

Aggregators: `count`, `sum`, `min`, `max`, `avg` + `where`. **L3–L5 already implemented**:
count and group **without expanding**, filtering through the dictionary index, and group-by, which
uses the sorted layout when it exists and falls back to the order-free path when it does not.

> Count and group without expanding work through dictionary/raw columns. The `*N|` of tcf-mode is
> interleaved, **not separable**.

On real data (online-retail, 5,000 × 8), answering *"how many items did user X buy"* with
`where(CustomerID=X).sum("Quantity")` **materializes 7.9% of the blob**, against 100% for a
`decode()`. A `count()` materializes **nothing at all**: the row count is declared in the
structure, so it is read without building a single value.

Low memory and latency fall straight out of that structure. And it is a **read-only core API, not
a format version**: it reads `#TCF.8M`, `#TCF.8R` (records), `#TCF.8H` when rectangular, and the
single-column route.

The current query-like surface: `count`, `sum`, `min`, `max`, `avg`, `where`, `select`,
`distinct`, `n_unique`, and the grouping family (`group_count`, `group_sum`, `group_min`,
`group_max`, `group_avg`), which also runs after a filter, so `where(...).group_sum(...)` is
the `WHERE ... GROUP BY`. Grouping keys accept a list of columns. Plus experimental
`group_ranges` and `agg_by`. `group_ranges` is the layout inspector, so it stays strict and
raises when the key is not contiguous; `agg_by` answers either way, falling back to the
order-free path.

Grouping has decisions with no single right answer, and this one follows the mathematics: a
null key **forms a group**, and a group with no usable value sums to `0.0` while `min`/`max`/
`avg` return `None` there. If you expect what pandas, SQL or polars would answer,
[the matching guide](docs/how-to/mimetizar-pandas-sql-polars.md) gives the one-liner for each,
every recipe verified by execution.

Dictionary and raw columns can be scanned structurally, while an interleaved `tcf` column may
require full materialization. The detailed contracts live in
[`docs/reference/lazy-view.md`](docs/reference/lazy-view.md).

**End-to-end: transmit the compact text, query it on arrival**. The blob stays small **and** stays
text, so the producer can `encode` once and send it as a normal HTTP body.

The consumer then runs `view()` and decompresses only the columns a given question touches. Nothing
else gets expanded to answer a `count()` or a filtered aggregate.

```mermaid
flowchart TB
    subgraph Producer
        direction TB
        A[table<br/>CSV / DB dump] -->|encode| B["blob<br/>183 B, #TCF.8M text"]
    end
    B -->|"HTTP body<br/>(gzip/brotli optional, on top)"| C
    subgraph Consumer
        direction TB
        C["view(blob)<br/>connects, decompresses nothing"] -->|"count()"| D["the header<br/>(no column read)"]
        C -->|"where(cidade=SP).sum(valor)"| E["materializes only<br/>cidade + valor"]
        C -->|"decode(blob)"| F[full table<br/>all columns]
    end
```

The same blob serves three access levels off one transmission: a cheap `count()`, a selective
filtered aggregate, or a full `decode()`. The caller picks how much to pay.

A compressed block cannot do this. To answer *any* question you inflate the **whole** payload
first, which is also where the memory goes. Over HTTP the inflating happens below you, so the
saving `view()` offers is not against the channel: it is against everything your process does
**after** the channel is done, which is the part the channel never touches.

![Memory: view() vs full decode (same blob, one query, two footprints)](docs/img/view-memory.svg)

Measured with round-trip counter-proof, timing throughput plus `tracemalloc` peaks, in
`2026-07-13-0156-compressores-http-parquet/`.

Answering `where(Country).sum(Quantity)` on online-retail (100×8) peaks at **10.4 KB**
through `view()`, versus **45.2 KB** through a full decode: **≈4.3× less**. For
cadastro 2000×5 it is 3.95×.

Decompression throughput is high for every codec (gzip ~60, zstd ~130, lz4 ~850 MB/s decompress).
But a compressor pays it over **100%** of the payload, while `view()` pays it over the touched
fraction, **6.3%** here.

The latency win is not decompressing *faster*. It is decompressing **less**.

## Roadmap 2.0

After a solid 1.0 (registered, **not** implemented, see
[ADR-0018](docs/adr/0018-v2-format-roadmap.md)):

- **Lossless aggregates even while lossy per row**: exact sums/averages in the aggregate when
  rounding with a residual, say installments where `valor = sum(installments)`, and *dropping* a
  derivable column such as `total = base + tax`. Crossing the lossless line needs an explicit
  decision plus a GATE, see Package 10 in
  `loss-taxonomia.md`.
- **Streaming / low latency (V2-J)** and **zero-copy disk / column-pruning (V2-K)**:
  transmit and read in chunks, without buffer-over-buffer.
- **Internal binary layer (V2-L)**: pack the body into bytes while keeping the textual header and
  visible groups (Parquet-style, but still explainable). It does not compete with gzip/brotli: it is
  a binary representation of the **same** logical content.
- **More specs** (templated/checksummed/numeric), gain limits, local query indexes and
  **intra-value repetition** (factoring `111.` inside a CPF), target `.9`/pre-1.0 with gates.

## How to cite

See [`CITATION.cff`](CITATION.cff). GitHub renders a "Cite this
repository" badge on the repo page automatically.

---

## LLM Benchmark v0.5 (accessory, parallel project)

> This section summarizes the **v0.5** cycle (a columnar format for LLM consumption).
> It is **not** the TCF core algorithm above. All the material lives separately.

The v0.5 cycle measured LLM comprehension of tables in CSV/JSON/TOON/TCF, across Track A "LLM reads
and computes" and Track B "LLM generates SQL". It covered 7 commercial models + 13 local,
2 datasets, 2256 records and 38 findings.

It used the **levels engine**, `EncodeConfig(level=N)`, in [`docs/archive/old/tcf/`](docs/archive/old/tcf/). See
[`docs/archive/old/tcf/LEVELS-REVIEW.md`](docs/archive/old/tcf/LEVELS-REVIEW.md) for the L0–L3 semantics.

- **Harness** (runners, llm_eval, scripts): [`docs/archive/old/llm-benchmark/`](docs/archive/old/llm-benchmark/)
- **Findings catalog** F-Q01..Q38: [`docs/archive/findings/`](docs/archive/findings/)
  + [`docs/archive/FINDINGS_SUMMARY.md`](docs/archive/FINDINGS_SUMMARY.md)
- **Manual / paper v0.5**: [`docs/archive/manual_v05/`](docs/archive/manual_v05/)
  + [`docs/archive/article_v05/`](docs/archive/article_v05/)

A spin-off candidate (`tcf-llm-tools`) for the future. It could re-validate against the current core
if Phase 2 is revived.

---

## Where to go next

- **I want to use TCF in my pipeline** → `from tcf import encode, decode`; the public
  surface contract is [docs/reference/api.md](docs/reference/api.md) *(Portuguese)*. Start at
  [getting started](docs/tutorials/getting-started.md), then the [how-to guides](docs/how-to/).
- **I want to read the findings** → [docs/archive/findings/](docs/archive/findings/) (v0.5 LLM, historical)
- **I want to run the LLM benchmark** → [old/llm-benchmark/](docs/archive/old/llm-benchmark/) (accessory v0.5)
- **I want to understand the architecture** → [docs/theory/](docs/theory/)
- **I want to see the roadmap** → [ROADMAP.md](ROADMAP.md) *(Portuguese)*: tiers pre-1.0 /
  2.0 / research; granular detail in
  [roadmap-hipoteses.md](experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md)
- **I want SQL-like query paths without full materialization** →
  [`tcf.view`](docs/reference/lazy-view.md) *(Portuguese)*: `count`/`sum`/`where`/group-by touching
  only what is needed, where the column mode permits
- **I want to share / pitch TCF** → [docs/divulgacao-tcf.md](docs/divulgacao-tcf.md)
  *(Portuguese)*: outreach material, post style
- **I want to read the paper** → v0.5 drafts:
  [docs/archive/article_v05/](docs/archive/article_v05/) (paper pending)
- **I want to see how it evolved** → [CHANGELOG.md](CHANGELOG.md) +
  [docs/archive/workbench/](docs/archive/workbench/)
- **I want to work on TCF itself** → [CONTRIBUTING.md](CONTRIBUTING.md): dev setup,
  repository layout and the tools that ship with the repo

---

## License

MIT. See [LICENSE](LICENSE).

## Acknowledgements

Project conceived as part of an academic dissertation (TCC). Datasets:
[UCI Adult Census](https://archive.ics.uci.edu/ml/datasets/adult) and
[TPC-H](https://www.tpc.org/tpch/) (via the DuckDB tpch extension).
(v0.5 cycle) Commercial LLM testing supported by personal credits;
total spend $9.46 USD for 1968 records (75% cache savings).
