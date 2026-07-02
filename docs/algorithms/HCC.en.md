<!-- l10n: doc_id=hcc · lang=en · canonical -->
**English** · [Português](HCC.pt-BR.md)

# HCC — Hierarchical Compositional Coding

**Original codename**: `M8.A` (variant A of the M8 macro from the dirty lab v0.6).

**Layer**: TCF layer 2 (compositional compaction).

## What it is

HCC is the **compositional compaction** layer of TCF. It receives the
root tokens produced by [OBAT](OBAT.md) and produces the final TCF
text, compressing recurring compositions into auto-named refs
organized hierarchically.

The central innovation of HCC is the semantic distinction between two
concatenation operators in text:

- `,` (comma) — **ephemeral** concat: joins two refs on emission, but
  does NOT create a new named ref.
- `~` (tilde) — **compositional** concat: joins two refs AND creates a
  new auto-named ref for future reuse.

Range `a..b` is a particular case of composition by consecutive sequence.

## Structure

The output of HCC is text. Each line represents an original string
(or repetition via RLE).

### Syntax

| Construct | Meaning |
|---|---|
| `1,2,3` | Refs 1, 2, 3 concatenated (without creating a new ref) |
| `1~2~3` | Refs 1, 2, 3 concatenated AND creating new refs (pairwise) |
| `1..5` | Range: refs 1, 2, 3, 4, 5 (particular case of composition) |
| `abc` | Literal `abc` |
| `\X` | Escape of a reserved char (`*`, `\`, `~`, digit, etc.) |
| `*N\|line` | RLE: line repeats N times |
| `*` | Separator at a lit-lit or lit-ref boundary |
| `^N` | Repetition of an already-decoded string (anti-RLE of a single string) |

### Internal pipeline

1. **Phase A (tokenize)**: alg16 tokens + provisional atoms → `pieces`
   per line (`lit` or `refs`)
2. **Phase B (detect)**: iterative greedy — replaces reusable
   sub-tuples with `alias_marker`
3. **Phase C (emit)**: single pass — assigns decoder-style IDs
   (interleaved atoms + compositions), emits text

## How it works (mathematical sub-language)

### Internal state

Let `body = (T_1, ..., T_n)` be the body, where `T_i` is the TCF line of
the i-th unique string.

Let `R` be the set of refs (atomic + virtual) and `M ⊂ R × R × ... × R`
the set of detected sub-tuples.

### Greedy detector

For each iteration `k = 1, 2, ...`:

```
count[sub] = | { position in pieces[*]['refs'] where sub appears consecutively } |

for each sub ∈ pieces with count[sub] ≥ 2:
    Lr_inline = chars of _emit_refs_range(sub)
    len_N = chars of str(atom_count + accumulated_compositions + K - 1)
    net = (R - 1) * (Lr_inline - len_N)
    if net > 0:
        candidate

best = argmax(net) among candidates
if best exists:
    replace all occurrences of best.sub with a new alias_marker
    aliases.append(best.sub)
else:
    stop
```

### Constraint for correct inline expansion (body-order check)

When a candidate `sub` contains a virtual `-Y` at a position `> 0`,
require:

```
alias_first_line[Y] < sub_first_line[sub]
```

That is, `Y` must have appeared alone on a line **prior** to the first
appearance of `sub`. Guarantee: when emitting the def of `sub`,
`Y` is already resolved — inline expansion via pairwise left-assoc
preserves the correct value of `Y`.

### Emit (pairwise left-assoc)

For a chain `a~b~c~...~z` of K refs, the decoder allocates `K - 1` IDs
following the rule:

```
ID_1 = a + b
ID_2 = ID_1 + c
ID_3 = ID_2 + d
...
ID_{K-1} = ID_{K-2} + z
```

Where `+` is string concatenation. The final ID (`ID_{K-1}`) is the
"exported" value of the chain — it can be referenced by other lines.

Intermediate IDs are also allocated (and can be referenced if
an alias is defined for that sub-composition at some point).

### Body-order of IDs

IDs are assigned by order of appearance in the body — interleaved between
atoms (`'lit'` pieces) and compositions (`'composition_def'`). This
allows a single-pass decoder without a separate preamble.

## Why the name

| Component | Meaning |
|---|---|
| **Hierarchical** | Compositions can contain refs that are themselves compositions. Natural tree structure of levels. |
| **Compositional** | The central operation is COMPOSITION (concat with naming). Distinguishes it from mere concat. |
| **Coding** | Encodes into **text** (not binary bytes). Readable and inspectable output. |

## Differentiator vs the literature

### vs Re-Pair (Larsson & Moffat 1999)

Re-Pair recursively replaces the most frequent pairs of
**bytes/symbols** until there is no pair with freq ≥ 2. It builds a
context-free grammar.

HCC shares the spirit of "replace what repeats" but:
- Works on OBAT **tokens** (not bytes).
- Distinguishes `,` (ephemeral) vs `~` (creates a ref) — **explicit
  semantics** in the output. Re-Pair has no such distinction (every
  substitution creates a grammar rule).
- **Implicit auto-naming** (sequential IDs by order). Re-Pair
  needs an explicit dictionary of rules.
- **Textual output** (not binary). Re-Pair typically outputs binary.

### vs Sequitur (Nevill-Manning & Witten 1997)

Sequitur infers a grammar online by uniting digrams (pairs of adjacent
symbols) that repeat, keeping the grammar minimal.

HCC is **offline** (it sees the complete body before deciding, then
iterates greedily). Simpler to implement. Sequitur maintains strong
invariants; HCC only requires net > 0.

### vs LZW (Lempel-Ziv-Welch 1984)

LZW grows the dictionary progressively as it reads the stream. HCC
also grows a dictionary (compositions) but via **global greedy** with
a net heuristic, not progressively.

### vs Templates / Macros in programming

The `~` operator resembles a macro/template — it defines a named group
for reuse. HCC formalizes it with an explicit cost algebra (net) and
constraints to guarantee correctness (body-order).

## HCC's own innovations

1. **Dual semantic marker** (`~` vs `,`): unique in the literature —
   compressed text distinguishes "create a ref" from "concat just this
   once".
2. **Implicit auto-naming**: IDs by order of appearance, without a
   preamble. Enables a single-pass decoder.
3. **Unified ref space**: the detector sees atomic + virtual in the same
   queue → captures pairs like `(atom_X, previous composition)` that
   traditional detectors miss.
4. **Body-order constraint**: algebraic guarantee of correctness for
   inline expansion with pairwise left-assoc.
5. **Range as a particular case**: `a..b` is sugar for
   `a~a+1~...~b`. Clean syntax for common consecutive sequences.
6. **Textual output without brackets**: the file is a pure sequence of
   lines, LF only. Inspectable, processable by line-oriented tools
   (grep, sed, etc.).

## Where it fits

HCC is **layer 2** of TCF. Pipeline:

```
List of strings (a data column)
       ↓
   OBAT (layer 1)
       ↓ root tokens
   HCC (layer 2)
       ↓ TCF text (with `~`/`,`, numeric refs, escapes)
   TCF file
```

The canonical implementation is in
[`src/tcf/composicional/syntax.py`](../../src/tcf/composicional/syntax.py).
Experimental origin:
`experiments/lab/dirty/old/2026-05-16-M8-virtual-refs-clean-output/M8-A-detector-unificado/syntax.py`
(untouched since 2026-05-16).

## Connections

- [OBAT](OBAT.md) — the layer that produces the root tokens consumed by HCC
- [TCF-format](TCF-format.md) — positioning of the format
- `experiments/lab/dirty/notas/historia-dirty-lab.md` — narrative of the
  development (codename M8.A)
- `experiments/lab/dirty/notas/no-funcional-marca-e-troca.md` —
  future direction: extension of HCC with a variable slot
