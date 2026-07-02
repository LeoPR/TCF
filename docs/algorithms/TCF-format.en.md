<!-- l10n: doc_id=tcf-format · lang=en · canonical -->
**English** · [Português](TCF-format.pt-BR.md)

# TCF — Tabular Compact Format

## Overview

TCF is a textual format for representing **tabular data** in a
**compact** way, while preserving:

- **Text output** (no binary) — visual inspection and
  processing by LLMs/line-oriented pipelines
- **Lossless roundtrip** — `decode(encode(values)) == values` always
- **Structural compression** — exploits patterns in columns (shared
  affixes, recurring sub-patterns, detectable cadences,
  near-identical runs)

Format designed for:
- Columns of tabular data where values share structure
  (URLs, emails, IDs, dates, paths, structured identifiers)
- Medium volumes (does not replace gzip for massive logs; replaces
  CSV/JSON when readability matters)
- Multi-column tables where each column benefits from its own
  pipeline (independent per-column encoder)

## Versioning (ADR-0024 + ADR-0028 — pre-1.0; supersedes ADR-0017)

> **3-AXIS MODEL (ADR-0028, 2026-06-24; refines ADR-0024)** — distinguish:
> - **(A) FORMAT version** — the **format signature / magic number** `#TCF.N` (canonical term;
>   **not** "shebang", which is `#!` — analogous to `%PDF-1.7`; see [vocabulary.md](../vocabulary.md)).
>   On-disk contract; only changes with a format change. Today `#TCF.7` (default), `#TCF.6` (legacy, read).
> - **(B) Encoder generation** — internal milestone (M8A→M9→M10); NOT a public version (historical note).
> - **(C) Package version** (PyPI) — pre-1.0 = `0.<format>.<release>`: minor = format number
>   (`0.N` ↔ `#TCF.N`); release/patch = delivery WITHIN the format.
>
> **Bump rule**: a FORMAT change moves the minor (`0.(N+1).0`); a delivery without a format change moves the
> release (`0.N.x+1`). E.g.: lazy+prune (#TCF.7 unchanged) = `0.7.2`; cross-dict `#TCF.8` = `0.8.0`.
> `1.0` only when the final format freezes → then strict semver. The phrases "frozen v1.0"/"v2.0"/
> "stable since v1.0" below are from the old model (ADR-0017) — read them in that key.
> Terms: [`../vocabulary.md`](../vocabulary.md) §Versioning.

TCF distinguishes the **FORMAT version** (signature `#TCF.N`, axis A) from the **PACKAGE version**
(semver `0.N.x`, axis C) — do not confuse the two (ADR-0028).

### Format version (signature)

| Signature | Status | Introduced | Compatible with |
|---|---|---|---|
| `#TCF.8` | **opt-in** (self-describing natures) | 2026-06 | encode only if a nature exists; decode reads |
| `#TCF.7` | **0.7 (default)** | 2026-06 | encode default (multi-col); decode reads |
| `#TCF.6` | **legacy** (0.6) | 2026-05 | decode reads; producible internally |
| `#TCF.5` | superseded | 2026-04 (v0.5) | tcf 0.5.x (legacy, do not maintain) |

**`#TCF.8` (self-describing natures, [ADR-0027](../adr/0027-nature-mark-header-self-describing.md),
welded 2026-06-24)** — STRICTLY ADDITIVE and opt-in: emitted ONLY IF some column has a nature
(CPF/CNPJ/IP); otherwise byte-identical `#TCF.7`.

**1-char discriminator** ([ADR-0029](../adr/0029-version-format-identification-semi-implicit.md)):
the character right after `#TCF.8` decides structure+type. No collision (single has a SPACE
before the name; multi has `M` attached):

| after `#TCF.8` | type | header |
|---|---|---|
| `M` | multi | `#TCF.8M<NN[=name][:spec]>,<...>` (meta INLINE on the signature line) |
| ` ` (space) | single + spec | `#TCF.8 [name]:spec` (name optional, label only) |
| `\n` | single version-stamp | `#TCF.8` (opt-in stamp; magic number for `file`/libmagic) |

Examples (body on the following line(s)):

    #TCF.8M!7=doc:cnpj,!x        <- multi: 2 cols, doc with nature cnpj, x raw
    #TCF.8 docs:cpf              <- single + spec cpf, name 'docs'
    #TCF.8                       <- single version-stamp (pure single-col body)

- **self-describing nature**: the `:spec` (cpf/cnpj/ip) travels in the header; decode resolves it via
  a fixed core-only dict (zero eval), unknown id -> raw + warning (forward-compat),
  header-wins precedence. Multi: the validator forbids `:` in a column name when there is a nature.
- **byte-neutral** ([ADR-0029](../adr/0029-version-format-identification-semi-implicit.md)
  layer 1): `#TCF.8` only appears on opt-in (`nature=`/`nature_per_col=`/`stamp=True`).
  Flat single-col = pure **orphan** body (no signature, D1-D9=1523B intact); multi without
  a nature = `#TCF.7 M`. The version-stamp (`#TCF.8\n`) is opt-in (`encode(list, stamp=True)`).
- multi `#TCF.8M` drops the space before the `M` and puts the meta on the signature line (~2B less
  than `#TCF.7 M`+separate line).
- **anonymous columns** (`encode(dict, drop_names=True)`): omits the `=name` in the meta; decode
  reconstructs by ORDER (`{'0':..,'1':..}`, like SQL/CSV-without-header). Saves the name of
  each column in the header; forces `#TCF.8M` (the named `#TCF.7` stays intact). Natures follow
  (`:spec` positional). Position-aware parse: `=` disambiguates named vs anonymous.

**v1 promise**: `#TCF.6` is immutable until v2.0. No byte of a
TCF v1 file changes between tcf 1.x.y versions. New markers require `#TCF.7`.

**`#TCF.7` (v2, ADDITIVE and opt-in)** — two orthogonal capabilities, both multi-col,
both emitting `#TCF.7 M` only when activated (otherwise byte-identical `#TCF.6`).
**Every `#TCF.7` drops the `# ` prefix of the meta** (the `M` flag in the signature already
declares the columns, ADR-0023) — `#TCF.6` keeps the `# ` (frozen). Decoder
self-describing. The default preserves 100% of the v1 invariants:
- **V2-A fallback identity** ([ADR-0022](../adr/0022-v2a-fallback-identity-weld.md),
  `fallback=True`): per column chooses min(TCF, raw); a raw column is marked
  `!<size>=<name>`. Meta: `!<s1>=<n1>,<s2>=<n2>,...`.
- **Minimal v2 header** ([ADR-0023](../adr/0023-v2-minimal-header-weld.md),
  `min_header=True`): besides the prefix, OMITS the size of the LAST column (body up to
  EOF) -> meta `<s1>=<n1>,...,<nN>`. Aimed at small payloads.
- **V2-B dictionary** ([ADR-0025](../adr/0025-v2b-dictionary-categorical-weld.md),
  marker `@`) and **structural split** ([ADR-0026](../adr/0026-structural-split-weld.md),
  marker `%`): more per-column fallback candidates (welded; body detail in the ADRs).
- **V2-RLE-STREAM** (experimental follow-up to V2-B, **NOT welded**): RLE on the index stream
  of `@dict`. Characterized 2026-06-19 ->
  [lab](../../experiments/lab/dirty/old/refuted/2026-06-19-v2rle-stream-caracterizacao/result.md): CLOSED-general /
  pure-text niche open (owner's decision). `src/tcf` untouched.

### Library version (semver)

- **1.0.x** — bug fixes (without changing bytes in D1-D9, D17a, real-world snapshots)
- **1.x.0** — additive features: new `nature` specs, keyword-only
  parameters with defaults that preserve behavior (e.g.: `encode(data, *, new_param=def)`)
- **2.0.0** — breaking: format change, API removal, new marker in the body

### Public API frozen in v1.0

Stable imports until v2.0:

```python
from tcf import (
    encode, decode,                   # core
    SideOutputs,                       # debug/stats opt-in
    PipelineConfig,                    # toggle layers
    build_schema, TableSchema, ColumnSchema,  # schema introspection
    TemplatedCheckedSpec, TemplatedPaddedSpec,  # nature definitions
    SPEC_CPF, SPEC_CNPJ, SPEC_IP,    # canonical nature specs
)
```

Immutable signatures. New optional parameters with defaults allowed.

### Deprecated in v1.x (removed in v2.0)

- `encode_table(table)` → use `encode(dict)`
- `decode_table(text)` → use `decode(text)`

Emit `DeprecationWarning` on every use since v1.0.

### Formal regression suite

[`tests/test_regression_v1_baseline.py`](../../tests/test_regression_v1_baseline.py)
captures byte-canonical for D1-D9 (1523B total) and D17a (322B INVARIANT).
A failure in CI = regression. The snapshot can only be updated via an
explicit ADR + version bump.

Details: see [ADR-0017](../adr/0017-format-spec-v1-frozen.md).

## Full pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│  ENCODE — dispatch by type (ADR-0014)                               │
│  ┌──────────────────────────┐    ┌──────────────────────────┐       │
│  │  encode(list[str])        │    │  encode(dict[str,list])   │       │
│  │  single-column semantic   │    │  multi-column semantic    │       │
│  └────────────┬─────────────┘    └────────────┬─────────────┘       │
│               │                                │                    │
│               │                          ┌─────┴──── 1 per col ───┐ │
│               ▼                          ▼                         │ │
│         ┌───────────────────────────────────────────────┐         │ │
│         │   PRE-PASS (1 pass, O(N))                     │         │ │
│         │   ─────────────────────────                    │         │ │
│         │   analyze_column → ColumnFeatures              │ H-DA-11c│ │
│         │   ├─ n_rows, n_uniques, avg_len, cardinality  │         │ │
│         │   ├─ is_numeric, sample                       │         │ │
│         │   detect_cadence_from_features                 │ ADR-0008│ │
│         │   ├─ rule 1: wrapper+counter (unified LCP/LCS)│         │ │
│         │   └─ rule 2: numeric AND cardinality > 0.5    │         │ │
│         │   detect_min_len_from_features                 │ ADR-0010│ │
│         │   └─ heur v3 (avg_len + card + is_numeric)    │         │ │
│         │      + gating n>=100 (preserves baseline)     │         │ │
│         └─────────────────────┬─────────────────────────┘         │ │
│                               │                                   │ │
│              cadence?         │                                   │ │
│              ┌──── yes ──────►│                                   │ │
│              │                ▼                                   │ │
│              │     ┌───────────────────────────────────┐         │ │
│              │     │   OBAT (layer 1)                   │         │ │
│              │     │   ─────────────                    │         │ │
│              │     │   alg16: LCP+LCS bidirectional     │         │ │
│              │     │   greedy cover, min_len threshold  │         │ │
│              │     │   root tokens:                     │         │ │
│              │     │   • TokLit(text)                   │         │ │
│              │     │   • TokRefPref(string_id, length)  │         │ │
│              │     │   • TokRefSuf(string_id, length)   │         │ │
│              │     │   ─────                            │         │ │
│              │     │   processar_with_hint              │ ADR-0011│ │
│              │     │   (shape-preserve per-length)      │         │ │
│              │     │   OR                                │         │ │
│              │     │   processar canonical              │         │ │
│              │     │   ─────                            │         │ │
│              │     │   Trigram hash O(N^1.42)           │ ADR-0009│ │
│              │     └────────────────┬──────────────────┘         │ │
│              │                      │                            │ │
│              │       ┌──────────────┴──────────────────┐         │ │
│              │       │   HCC (layer 2)                  │        │ │
│              │       │   ─────────────                  │        │ │
│              │       │   M8.A: virtual refs unified    │        │ │
│              │       │   greedy detector (net > 0)     │        │ │
│              │       │   emit text:                    │        │ │
│              │       │   • `~` creates auto-named ref  │        │ │
│              │       │   • `,` ephemeral concat        │        │ │
│              │       │   • `1..5` range (sugar)        │        │ │
│              │       │   • `*N|line` RLE               │        │ │
│              │       │   • `\X` escape                 │        │ │
│              │       │   • `*` separator (ADR-0007)    │        │ │
│              │       │   ─────                          │        │ │
│              │       │   HCCSeqRLE (M10, ADR-0011):    │        │ │
│              │       │   `*N+delta|template` runs       │        │ │
│              │       │   near-identical                 │        │ │
│              │       └────────────────┬─────────────────┘        │ │
│              │                        │                           │ │
│              │                        │  body per column          │ │
│              │                        ▼                           │ │
│              └────────────────────────┘                           │ │
│                                       │                           │ │
│                multi-col              │                           │ │
│            ┌── concat ────────────────┘                           │ │
│            ▼                                                      │ │
│   ┌──────────────────────────────────────────────┐               │ │
│   │  #TCF.7 M   (default 0.7; #TCF.6 = legacy)     │ ADR-0004/0013 │ │
│   │  meta V2:  !<s1>=<n1>,...,<nN>   (no `# `)     │ +0022/23/24/25│ │
│   │  <body1><body2><body3>...                      │               │ │
│   │  (byte-precise concat, no delimiter)           │               │ │
│   └──────────────────────────────────────────────┘               │ │
│   #TCF.6 legacy: `# <s1>=<n1>,...` (with `# `, no markers).        │ │
│                                                                  │ │
│   single-col: pure body, no signature                            │ │
└─────────────────────────────────────────────────────────────────────┘
```

### Decode (mirror)

```
decode(text) → list[str] | dict[str, list[str]]
         │
         ├─ startswith("#TCF.7 M") OR "#TCF.6 M" ──► _decode_multi → dict
         │
         └─ otherwise                             ──► _decode_column → list
```

Self-describing: the signature (`#TCF.7 M` default, `#TCF.6 M` legacy) identifies
the format. The decoder dispatches automatically on both; the caller does not need
to know whether the output is single or multi.

## Detailed layers

### Layer 0 — Pre-pass

Before entering OBAT, each column goes through an O(N) analysis that
produces `ColumnFeatures` + heuristic hints. These hints calibrate
OBAT (shape-preserve or canonical) and the optimal min_len.

Modules:
- [`column_features.py`](../../src/tcf/column_features.py) — `analyze_column()` (H-DA-11c)
- [`auto_cadence.py`](../../src/tcf/auto_cadence.py) — `detect_cadence_from_features()` (ADR-0008)
- [`auto_min_len.py`](../../src/tcf/auto_min_len.py) — `detect_min_len_from_features()` (ADR-0010)

### Layer 1 — OBAT

Tokenizes each string of the column into refs (prefix/suffix of previous
strings) + literals. Produces **discrete tokens** that HCC consumes.

Doc: [OBAT.md](OBAT.md). Implementation: [`src/tcf/core/online.py`](../../src/tcf/core/online.py)
+ [`src/tcf/obat_shape.py`](../../src/tcf/obat_shape.py).

### Layer 2 — HCC

Detects recurring compositions in the tokens (refs that repeat
together become pairwise named refs) + compacts near-identical runs
into `*N+delta|template`. Produces the final **TCF text** of the body.

Doc: [HCC.md](HCC.md). Implementation: [`src/tcf/composicional/syntax.py`](../../src/tcf/composicional/syntax.py)
+ [`src/tcf/composicional/hcc_seqrle.py`](../../src/tcf/composicional/hcc_seqrle.py).

### Layer 3 — Multi-column wrapper

For `dict[str, list[str]]` input, each column goes through layers
0-2 independently. The bodies are concatenated byte-precise with a
`#TCF.7 M` header (default 0.7) + meta line.

> **Default 0.7 (ADR-0024)**: `encode(dict)` emits **`#TCF.7 M`** with
> `fallback` + V2-B dictionary + `min_header` **automatic** — meta without the
> `# ` prefix, per-column mode markers (`!` raw, `@` dict, `%` split) and the
> last column without a size. `#TCF.6 M` is **legacy** (read by the decoder; producible
> via `_encode_multi(fallback=False, min_header=False)`). Real ex.:
> `#TCF.7 M\n!5=id,!15=name,!plan\n...`.

**V2-A fallback identity (ADR-0022, `fallback`)**: per column chooses min(TCF, raw);
a raw column becomes `!<size>=<name>`. **On by default** in 0.7.

**Minimal v2 header (ADR-0023, `min_header`)**: every `#TCF.7` drops the `# ` prefix
of the meta (the signature's `M` already declares the columns); `min_header` additionally omits the size of the
last column (body up to EOF): meta `<s1>=<n1>,...,<nN>`. **On by default** in 0.7.
Focus: small payload (fixed header dominates). To emit byte-identical `#TCF.6` (legacy),
explicit opt-out (`fallback=False, min_header=False`).

**V2-B dictionary (ADR-0025, `@`) + structural split (ADR-0026, `%`)**: extra
per-column fallback candidates (categorical dictionary; structural field split).
They enter the default when they reduce the column.

Restrictions:
- Column names cannot contain `,` or `=` (reserved by the header)
- All columns must have the same number of values
- `None` → `""` (TCF operates on strings)

Implementation: [`src/tcf/multi/`](../../src/tcf/multi/). ADR: [0004](../adr/0004-multi-column-header-compacto.md), [0013](../adr/0013-multi-column-canonical-api.md), [0014](../adr/0014-unified-api-side-outputs.md).

## Minimal API

```python
from tcf import encode, decode, SideOutputs

# Single-column
text = encode(["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"])
values = decode(text)  # list[str]

# Multi-column
table = {
    "timestamp": ["2026-01-01", "2026-01-02"],
    "email": ["a@x.com", "b@x.com"],
}
text = encode(table)
result = decode(text)  # dict[str, list[str]]

# Optional side outputs (debug, stats, future schema)
side = SideOutputs()
text = encode(table, side_outputs=side)
print(side.hcc_trace)                        # detector iterations
print(side.per_col["email"].column_features) # pre-pass features
print(side.multi_info)                        # header_bytes, body_bytes
```

### SideOutputs (ADR-0014)

Optional container that captures information produced internally
by the pipeline but that would normally be discarded. Useful for:

- Debug (inspecting HCC detector decisions, OBAT cover
  choices)
- Compression analysis (which column did not benefit, why)
- Future schema builder (consumes features + heuristics to produce
  a rich schema)

Fields:
- Pre-pass: `column_features`, `cadence_detected`, `cadence_info`, `min_len`
- OBAT: `obat_log`, `obat_used_hint`
- HCC: `hcc_trace`, `hcc_rede`, `seq_rle_runs`
- Bytes: `body_bytes` (per column)
- Multi-col: `multi_info`, `per_col` (SideOutputs nested per column)

Without `side_outputs=`: zero overhead (logs continue being generated and
discarded as before). Doc: [SideOutputs](../../src/tcf/side_outputs.py).

## Future layers (registered, not implemented)

```
┌──────────────────────────────────────────────────────────────────┐
│  PRESENT (welded canonical)                                      │
│  ────────                                                        │
│  encode(list|dict) → str                                         │
│  decode(str) → list|dict                                         │
│  SideOutputs (optional)                                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (next directions)
┌──────────────────────────────────────────────────────────────────┐
│  FUTURE Layer A — Encoder Manager (D13 v0.4, T-CODE-*)           │
│  ────────                                                        │
│  encode(data, parallel=True, output=Sink, plan=Plan(...))        │
│                                                                  │
│  • `_encode_column` in parallel workers (ProcessPoolExecutor)    │
│  • Pluggable output sinks: FileSink, MultiFileSink, HTTPSink,    │
│    TCPSink, MemorySink                                           │
│  • Plan dataclass: group_by/order/batch_size/batch_unit          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  FUTURE Layer B — Distributed transport (O-FMT-08/13)           │
│  ────────                                                        │
│  Per-channel headers (re-assembly without central coordination): │
│    #TCF.7 C name=timestamp chunk=1/3 of=table_X                  │
│  Chunked streaming: self-contained chunks, decode chunk-by-chunk,│
│    memory O(chunk_size), constant TTFB                           │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  FUTURE Layer C — Schema builder (T-CODE-SCHEMA-BUILDER)         │
│  ────────                                                        │
│  build_schema(data) → TableSchema (consumes SideOutputs)         │
│                                                                  │
│  Integrated detectors (META-TYPE-ENCODERS T02-T07):              │
│  • detect_templated (date, email, uuid, CPF, IP, phone)          │
│  • detect_enumerated (low-card categorical)                      │
│  • detect_checked (check digit)                                  │
│  • detect_composite (datetime split, money split)                │
│  • detect_hierarchical (paths, URLs)                             │
│                                                                  │
│  Outputs: TableSchema → JSON (compat metadata.json), Markdown,   │
│    diff (drift detection)                                        │
└──────────────────────────────────────────────────────────────────┘
```

Plan tickets:
- [T-CODE-ENCODER-MANAGER](../../tickets/T-CODE-ENCODER-MANAGER.md) (P2) — Revives D13 v0.4
- [T-CODE-OUTPUT-SINKS](../../tickets/T-CODE-OUTPUT-SINKS.md) (P2) — Pluggable `Sink` contract
- [T-CODE-PLAN-CONTRACT](../../tickets/T-CODE-PLAN-CONTRACT.md) (P3) — Plan dataclass
- [T-CODE-SCHEMA-BUILDER](../../tickets/T-CODE-SCHEMA-BUILDER.md) (P3) — Consumes SideOutputs

## Positioning in the compression literature

TCF sits at the intersection of three classic families:

### 1. Structural compression of string dictionaries

**Family**: front-coding and variants (Witten et al., HTFC and RPDac by
Brisaboa et al. 2011, etc.)

**Comparison**:
- TCF, via OBAT, generalizes front-coding with **bidirectionality**
  (LCP + LCS), captures "email-like" patterns where the suffix
  (`@gmail.com`) is stable and the prefix varies.
- TCF, via HCC, adds **hierarchical compositions** — there is no
  direct analog in classic front-coding.

### 2. Grammar-based compression

**Family**: Re-Pair (Larsson & Moffat 1999), Sequitur
(Nevill-Manning & Witten 1997).

**Comparison**:
- HCC is greedy iterative, in the spirit of Re-Pair but on OBAT tokens
  (not bytes).
- HCC has **distinct semantic operators** (`~` vs `,`) — there is no
  analog in Re-Pair (every substitution creates a rule).
- HCC is **offline** (analyzes the complete body) but simpler than
  Sequitur (which maintains complex online invariants).

### 3. Compaction for LLM consumption (accessory to the core)

**Family**: TabLLM (2023), TOON, JSON-tabular, compact formats
for LLMs to read tables (Sui 2024 review).

**Comparison**:
- Phase 1 (v0.5 cycle) cataloged Q01-Q38 about LLM-readability of the
  old TCF (columnar/RLE). That work is **accessory** to the focus
  of the core (compression algorithm, 0.7).
- LLM-readability becomes relevant again when Phase 2 is revived
  OR becomes a separate project.

## Aggregated differentiators

| Feature | TCF | LZ77/gzip | Re-Pair | Front-coding |
|---|---|---|---|---|
| Output | textual | binary | binary | binary/textual |
| Visually inspectable | yes | no | no | partial |
| Online (streaming-friendly) | partial | yes | no (offline) | yes |
| Bidirectional (prefix + suffix) | yes | n/a | n/a | prefix only |
| Hierarchy of compositions | yes | implicit | yes (grammar) | no |
| Auto-naming without explicit dict | yes | n/a | no (needs dict) | yes |
| Native multi-column | yes | no | no | no |
| Suited to columnar | yes (designed for it) | generic | generic | yes |

## When to use TCF

**Good use**:
- Columns of strings with textual patterns (URLs, emails, IDs, dates,
  paths)
- Medium volume (hundreds to thousands of rows; validated up to 60k in
  TPC-H lineitem)
- Text output is a requirement (inspection, line-oriented pipelines,
  consumption by LLMs)
- Multi-column tables where each column benefits from its own
  pipeline

**When to prefer alternatives**:
- **CSV/JSON** — very simple format, no need for
  compression (but TCF preserves readability)
- **gzip/brotli/zstd** — VERY large datasets, critical compression,
  binary OK
- **Re-Pair/Sequitur/HTFC** — huge dictionaries, binary output OK,
  random search matters

## State 0.7 (snapshot 2026-05-27; live state in [STATUS.md](../../STATUS.md))

> The numbers below are a **dated snapshot** (§5: the test measures, the prose points).
> For the current state — package version, test count, welded ADRs —
> see [STATUS.md](../../STATUS.md) and the guardians in `tests/`.

### Canonical implementation

`src/tcf/` — **pre-1.0** public API ([ADR-0024](../adr/0024-pre-1.0-versioning-git-as-compat.md)
supersedes the "frozen" of ADR-0017): additive, without rigid compat between dev minors
(git reproduces old versions). See the "Versioning" section above.

### Validation

**Single-column (M10 baseline, ADR-0011)**:
- D1-D9 synthetic: **1523 bytes** in 2865 raw = 53.2% ratio (RT 9/9)
- Byte-canonical chain of checkpoints: M9 → M10 → M11 → M12 → M13 → M14
  → M14+Pacote1+Multi+API+Natures+MultiDelta+v1
- Adult Census + TPC-H 57 columns: **-11.73% weighted** vs pure M9

**Multi-column (ADR-0013/0014 + V2 ADR-0022/0023/0025/0026)**:
- D17a synthetic (13×4): **303 bytes** (0.7 default, V2-B); 322B = `#TCF.6` legacy
- 9 real-world tables (Adult Census + TPC-H tier 1+2, 136k rows,
  15.8 MB raw):
  - **-33.02% weighted vs raw**, **-31.46%** vs single-col concat
  - RT 9/9 OK; Lineitem 60k×16: -17.11% vs raw

**Extended real-world (UCI/OpenML, T-DATA-1)**:
- wine-quality 6.5k × 13: 90.9% ratio (chemical decimals, low repetition)
- beijing-pm25 43.8k × 13: 71.7% (sensors + timestamps)
- online-retail 541k × 8: **23.7%** (StockCode/Country/InvoiceDate repeated)

**Benchmark vs csv/jsonl + gzip/brotli/zstd** (9 datasets total):
**TCF won in 7/9** datasets. Lost in D17a tiny (header overhead
dominates) and wine-quality (nearly unique decimals = no structure).
Details: [experiments/lab/dirty/2026-05-24-benchmark-formats-compression/](../../experiments/lab/dirty/2026-05-24-benchmark-formats-compression/).

**Test suite** (snapshot 2026-05-27: 259 passed; current count in
[STATUS.md](../../STATUS.md)). Byte-canonical guardian:
[`test_regression_v1_baseline.py`](../../tests/test_regression_v1_baseline.py)
(snapshot D1-D9=1523B + D17a=303B default / 322B `#TCF.6` legacy).

## State v0.5 (accessory)

There is v0.5 code in `old/tcf/` (columnar format with RLE/dict/stats
for the LLM benchmark). **Not canonical in v1.0**. Kept for
historical reference and while the Phase 1 LLM findings (in
`docs/findings/`) retain research relevance.

## Connections

### Algorithms
- [OBAT](OBAT.md) — layer 1 (tokenization)
- [HCC](HCC.md) — layer 2 (compositional compaction)

### Welded ADRs
- [ADR-0004 — Multi-column compact header](../adr/0004-multi-column-header-compacto.md)
- [ADR-0007 — Comma in literals bug fix](../adr/0007-comma-in-literals-bug.md)
- [ADR-0008 — detect_cadence rule 2 (numeric+high-card)](../adr/0008-detect-cadence-numeric-rule.md)
- [ADR-0009 — OBAT trigram index O(N^1.42)](../adr/0009-obat-trigram-index-optimization.md)
- [ADR-0010 — auto-detect min_len per column](../adr/0010-auto-detect-min-len.md)
- [ADR-0011 — Package 1 weld canonical (M9 → M10)](../adr/0011-pacote1-weld-canonical.md)
- [ADR-0013 — Multi-column canonical API (welded, superseded by 0014)](../adr/0013-multi-column-canonical-api.md)
- [ADR-0014 — Unified API + SideOutputs](../adr/0014-unified-api-side-outputs.md)
- [ADR-0015 — Templated/checked natures (CPF/CNPJ/IP)](../adr/0015-natures-templated-checked-weld.md)
- [ADR-0016 — HCC seq-RLE multi-delta](../adr/0016-hcc-multi-delta-seq-rle.md)
- [ADR-0017 — Format spec v1.0 frozen + versioning policy](../adr/0017-format-spec-v1-frozen.md)

### Future plan tickets
- [T-CODE-ENCODER-MANAGER](../../tickets/T-CODE-ENCODER-MANAGER.md) — P2, parallelism + sinks
- [T-CODE-OUTPUT-SINKS](../../tickets/T-CODE-OUTPUT-SINKS.md) — P2, pluggable Sink
- [T-CODE-PLAN-CONTRACT](../../tickets/T-CODE-PLAN-CONTRACT.md) — P3, Plan dataclass
- [T-CODE-SCHEMA-BUILDER](../../tickets/T-CODE-SCHEMA-BUILDER.md) — P3, build_schema
- [META-TYPE-ENCODERS](../../tickets/META-TYPE-ENCODERS.md) — natures (T02-T07)

### Narrative
- [`historia-dirty-lab.md`](../../experiments/lab/dirty/notas/historia-dirty-lab.md) — M0-M14 development
- [`roadmap-hipoteses.md`](../../experiments/lab/dirty/notas/roadmap-hipoteses.md) — active/closed hypotheses
- [`naturezas-numericas-2026-05-23.md`](../../experiments/lab/dirty/notas/naturezas-numericas-2026-05-23.md) — cataloging 12 natures
- [`futuras-otimizacoes-formato.md`](../../experiments/lab/dirty/notas/futuras-otimizacoes-formato.md) — O-FMT-* registry

### v0.4 design plan (architectural reference)
- [`2026-05-05-v04-design-recap.md`](../workbench/research-notes/_archive/2026-05-05-v04-design-recap.md) — D1-D18, EncodeManager (D13), Plan, 3 layers
