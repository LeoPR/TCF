<!-- l10n: doc_id=obat · lang=en · canonical -->
**English** · [Português](OBAT.pt-BR.md)

# OBAT — Online Bidirectional Affix Tokenizer

**Original codename**: `alg16` (16th experiment of phase M0 of the dirty
lab v0.6).

**Layer**: TCF layer 1 (tokenization core).

## What it is

OBAT is the tokenization core of TCF. It receives an ordered sequence
of unique strings (typically a column of textual tabular data)
and produces, for each string, a list of **tokens** describing how
it can be reconstructed using fragments of the previously
seen strings.

It does not produce compressed bytes; it produces **discrete
structure** that the upper layer (HCC) uses to generate the final
textual output.

## Structure

For each new string `s_i` in the sequence:

1. For each previous string `s_j` (with `j < i`):
   - Compute the longest **common prefix** between `s_i` and `s_j` (LCP)
   - Compute the longest **common suffix** between `s_i` and `s_j` (LCS)
2. Filter matches with `length < min_len` (default 3).
3. **Greedily choose** the matches that maximize coverage of
   `s_i` without overlap.
4. Uncovered fragments become `TokLit` (pure literal).

### Root tokens

| Token | Meaning |
|---|---|
| `TokLit(text)` | Literal fragment |
| `TokRefPref(string_id, length)` | Prefix of `s_{string_id}` of length `length` |
| `TokRefSuf(string_id, length)` | Suffix of `s_{string_id}` of length `length` |

Being token-level guarantees **orthogonality**: the syntax layer (HCC) can
serialize these tokens in any way, without OBAT needing to know.

## How it works (mathematical sub-language)

Sequence of unique strings: `S = (s_1, s_2, ..., s_n)`.

Definitions:
- `LCP(a, b) = max{ k | a[0:k] == b[0:k] }`
- `LCS(a, b) = max{ k | a[-k:] == b[-k:] }`

For each `s_i` with `i ≥ 2`:

```
P_i = { (j, LCP(s_i, s_j)) | j < i, LCP(s_i, s_j) ≥ min_len }
Q_i = { (j, LCS(s_i, s_j)) | j < i, LCS(s_i, s_j) ≥ min_len }
```

Greedy coverage algorithm:
1. `C := P_i ∪ Q_i` sorted by `length` descending
2. `coverage := ∅`
3. For each `(j, k, type) ∈ C`:
   - If the range covered by this match **does not overlap** with `coverage`:
     - Add to the token list (`TokRefPref` or `TokRefSuf`)
     - `coverage := coverage ∪ range`
4. Fragments of `s_i` not in `coverage` become `TokLit`.

For `i = 1` (first string), all tokens are `TokLit` (there is no
previous reference).

**Reconstruction** (decoder):
- `TokLit(t)` → emits `t`
- `TokRefPref(j, l)` → emits `s_j[0:l]` (resolved recursively if
  `s_j` is described by tokens)
- `TokRefSuf(j, l)` → emits `s_j[-l:]`

**Guaranteed termination**: since `j < i` always, the dependency
graph is acyclic. Base case: `s_1` is entirely literal.

## Why the name

| Component | Meaning |
|---|---|
| **Online** | Processes strings in order of appearance, without re-reading. Each new string only sees the previous ones. |
| **Bidirectional** | Uses prefix (LCP) **and** suffix (LCS) simultaneously. Not just "front-coding" (LCP-only). |
| **Affix** | A linguistic term unifying prefix, suffix (and infix in some contexts). Captures "a fragment at an edge". |
| **Tokenizer** | Produces tokens (not compressed bytes). Lets upper layers work with discrete structure. |

## Distinction vs the literature

### vs LZ77 (Lempel-Ziv 1977)

LZ77 uses a sliding window of previous bytes and searches for a match of
**any substring** (at any position). OBAT restricts to
**affixes** (prefix/suffix). Computationally simpler, more
suited to tabular domains where structures have stable heads/tails
(URLs with a common path, emails with `@dominio.com`, IDs with a
fixed format).

### vs Front-coding (Witten et al., dictionaries)

Traditional front-coding encodes string `s_i` by the **LCP** only
with the IMMEDIATELY preceding string `s_{i-1}`. OBAT extends it in two
dimensions:
- Also uses **LCS** (not only LCP)
- Considers **any** `j < i`, not only `j = i-1`

### vs HTFC / RPDac (Brisaboa et al. 2011)

Front-coding variants with bucketing (grouping into blocks for
search support). OBAT is fully online, without bucketing. It has no
direct support for random search (all references are
resolved sequentially).

### vs Suffix tree / Suffix automaton (Weiner 1973, etc.)

String **search** structures. OBAT is an **affix
encoding** strategy, not an index. It can be combined with an index
if needed (not the current case).

### vs Re-Pair (Larsson & Moffat 1999)

Re-Pair is **offline** (it analyzes the whole corpus before encoding) and
replaces the most frequent pairs recursively. OBAT is **online**
(one string at a time) and works at the affix level.

## OBAT's own innovations

1. **Simultaneous combination of LCP + LCS**: distinguishes OBAT from classical
   front-coding. Captures "email-type" patterns where the prefix (`joao@`) varies
   but the suffix (`@gmail.com`) is stable.
2. **Min-len threshold**: cost-benefit filter. Very short matches
   do not offset the overhead of markers in upper layers.
3. **Discrete output (tokens)**: separates "finding redundancy" from
   "serializing redundancy". HCC can evolve without affecting OBAT.
4. **Suited to columnar**: each column is a sequence of strings with
   typically high similarity. OBAT exploits this similarity
   locally, without needing a global model.

## Where it fits

OBAT is **layer 1** of TCF. Pipeline:

```
List of strings (a data column)
       ↓
   OBAT
       ↓ root tokens (TokLit / TokRefPref / TokRefSuf)
   HCC (layer 2)
       ↓ TCF text
   TCF file
```

The canonical implementation is in
[`src/tcf/core/online.py`](../../src/tcf/core/online.py). Experimental
origin: `experiments/lab/dirty/old/M0-fase-exploratoria-inicial/2026-05-11-16-online-cleanup/online.py`
(untouched since 2026-05-11).

## Connections

- [HCC](HCC.md) — the layer that consumes OBAT's tokens
- [TCF-format](TCF-format.md) — positioning of the format
- `experiments/lab/dirty/notas/historia-dirty-lab.md` — development narrative
