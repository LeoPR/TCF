---
title: CAMADA 1 — OBAT (Online Bidirectional Affix Tokenizer)
type: reference
parent: strategies-map
subsystem: obat
---

# CAMADA 1 — OBAT (Online Bidirectional Affix Tokenizer)

**Como decide caminhos**:

1. CAMADA 0 (Pre-pass, toggleable via cfg.pre_pass):
   - analyze_column(values) -> ColumnFeatures (always, even if pre_pass off)
   - IF cfg.pre_pass:
     * detect_cadence_from_features(features, unicas) -> (cadence_detected, info)
     * detect_min_len_from_features(features) -> min_len ∈ {3,4,5,6}
   - ELSE:
     * cadence_detected = False
     * min_len = 3 (default M9)

2. CAMADA 1 (OBAT tokenization):
   - IF cadence_detected AND cfg.obat_shape_preserve:
     * processar_with_hint(unicas, min_len, prefer_shape_consistency=True)
   - ELSE:
     * processar(unicas, min_len) [canonical]
   - Output: tokens (list[list[Token]]), obat_log (str)

3. CAMADA 2 (HCC compaction, not in this subsystem analysis):
   - IF cfg.hcc_seq_rle: HCCSeqRLE().encode(...)
   - ELSE: M8AVirtualRefsSyntax().encode(...)

For each string in OBAT processar():
   a. idx=0: emit [TokLit(s)], add to prefix/suffix index
   b. idx>=1:
      i. Lookup prefix bucket = prefix_index.get(s[:3]) -> candidates O(B)
      ii. Lookup suffix bucket = suffix_index.get(s[-3:]) -> candidates O(B)
      iii. _melhor_pref(...) -> (best_p_id, best_p_len) via greedy LCP search in bucket
      iv. _melhor_suf(...) -> (best_s_id, best_s_len) via greedy LCS search in bucket
      v. _escolher_par() -> choose non-overlapping (pref_id, pref_len, suf_id, suf_len):
         - IF best_p_len + best_s_len <= ls: fast path, return both
         - ELSE: generate 2 candidates (pref-dominant vs suf-dominant), max by coverage
      vi. Emit tokens: TokRefPref (if p_len>0), TokLit(middle), TokRefSuf (if s_len>0)
      vii. Add to indexes (if ls >= min_len)


### Estrategias (20)

| Nome | Kind | Local | Parametros | Triggers |
|---|---|---|---|---|
| **Token type: TokLit (literal)** | token-type | [src/tcf/core/online.py:30-35](../../../src/tcf/core/online.py) | text: str (any UTF-8) | always (fallback for uncovered spans); first string always emits [TokLit(s)] |
| **Token type: TokRefPref (prefix reference)** | token-type | [src/tcf/core/online.py:38-44](../../../src/tcf/core/online.py) | string_id: int (1-indexed into strings_unicas); length: int (>= min_len, typically 3-25) | when _melhor_pref finds a valid LCP >= min_len, and prefix chosen by _escolher_p |
| **Token type: TokRefSuf (suffix reference)** | token-type | [src/tcf/core/online.py:47-53](../../../src/tcf/core/online.py) | string_id: int (1-indexed); length: int (>= min_len) | when _melhor_suf finds a valid LCS >= min_len, and suffix chosen by _escolher_pa |
| **LCP (Longest Common Prefix) calculation** | heuristica | [src/tcf/core/online.py:59-64 (public); 75-82 (_lcp_len_capped)](../../../src/tcf/core/online.py) | a, b: str; cap (optional, _capped variant): int = upper bound on return value | always during _melhor_pref search; once per (candidate_prev_string) pair within  |
| **LCS (Longest Common Suffix) calculation** | heuristica | [src/tcf/core/online.py:67-72 (public); 85-94 (_lcs_len_capped)](../../../src/tcf/core/online.py) | a, b: str; cap (optional): int = upper bound | always during _melhor_suf search; once per candidate pair within suffix bucket |
| **Hash prefix index (trigram bucketing)** | marcador | [src/tcf/core/online.py:184, 196-197, 222-223; processar() initializes and maintains](../../../src/tcf/core/online.py) | trigram key length: k=3 (hardcoded, matches min_len default); bucket: list[int] (zero-indexed) | initialized empty at start of processar(); appended to every string where ls >=  |
| **Hash suffix index (trigram bucketing)** | marcador | [src/tcf/core/online.py:185, 197-198, 223; processar() manages](../../../src/tcf/core/online.py) | trigram key: s[-3:]; bucket: list[int] zero-indexed | initialized; appended for ls >= min_len; read in _melhor_suf |
| **_melhor_pref — find best prefix match** | filtro | [src/tcf/core/online.py:97-112](../../../src/tcf/core/online.py) | s (str), ls (len), strings (list), lens (list), prefix_index (dict), max_len (int=ls), min_len (int= | called once per new string in _escolher_par; bucket filtered by s[:3] trigram |
| **_melhor_suf — find best suffix match** | filtro | [src/tcf/core/online.py:115-126](../../../src/tcf/core/online.py) | s, ls, strings, lens, suffix_index, max_len (int=ls), min_len | called once per new string in _escolher_par; bucket filtered by s[-3:] |
| **_escolher_par — greedy cover with overlap detection** | estrategia | [src/tcf/core/online.py:129-162](../../../src/tcf/core/online.py) | s, ls, strings, lens, prefix_index, suffix_index, min_len (int) | once per new string (idx >= 1) in processar; core decision point for tokenizatio |
| **min_len threshold** | threshold | [src/tcf/core/online.py:102-103, 110, 116, 124 (filtering); default 3 set in processar()](../../../src/tcf/core/online.py) | int in range [2, 6]; empirically {3,4,5,6}; default=3 | passed as parameter to processar(); gates every valid match in _melhor_pref/_mel |
| **Auto-detect min_len (H-DA-11, ADR-0010)** | estrategia | [src/tcf/auto_min_len.py:25-68](../../../src/tcf/auto_min_len.py) | features (ColumnFeatures); n_threshold (int=100); returns int in {3,4,5,6} | pre-pass phase (CAMADA 0) in canonical M10 pipeline if cfg.pre_pass=True; always |
| **Cadence detection (H-DA-08, ADR-0008)** | estrategia | [src/tcf/auto_cadence.py:28-96](../../../src/tcf/auto_cadence.py) | features (ColumnFeatures), strings_unicas (list[str]), n_sample (int=5), threshold (float=0.7), nume | pre-pass phase (CAMADA 0) in canonical M10 if cfg.pre_pass=True; called before O |
| **processar() — canonical OBAT** | estrategia | [src/tcf/core/online.py:179-225](../../../src/tcf/core/online.py) | strings_unicas (list[str]); min_len (int=3); returns (list[list[Token]], str) | core CAMADA 1 processing; called from encoder.py unless cadence_detected and cfg |
| **processar_with_hint() — cadence-aware OBAT** | estrategia | [src/tcf/obat_shape.py:64-120](../../../src/tcf/obat_shape.py) | strings_unicas, min_len (int=3), prefer_shape_consistency (bool); returns (list[list[Token]], str) | CAMADA 1 processing when cadence detected (H-DA-08) and cfg.obat_shape_preserve= |
| **reconstroi() — roundtrip validation** | helper | [src/tcf/core/online.py:165-176](../../../src/tcf/core/online.py) | tokens (list[Token]), strings_unicas (list[str]); returns str | never called in canonical pipeline; available for unit tests + diagnostics |
| **ColumnFeatures pre-pass** | decision-point | [src/tcf/column_features.py:51-84](../../../src/tcf/column_features.py) | values (list[str]), sample_size (int=20); returns ColumnFeatures | always at start of _encode_column(); result fed to detect_cadence and detect_min |
| **Greedy cover selection criterion (maximize total coverage)** | decision-point | [src/tcf/core/online.py:155-161](../../../src/tcf/core/online.py) | cand_a, cand_b: (int, int, int, int) tuples (p_id, p_len, s_id, s_len) | when bp_len + bs_len > ls in _escolher_par; triggers 2-candidate generation and  |
| **Tie-break rule: first occurrence wins** | decision-point | [src/tcf/core/online.py:108-111 (_melhor_pref), 122-125 (_melhor_suf)](../../../src/tcf/core/online.py) | comparison operator > (not >=) | in _melhor_pref and _melhor_suf whenever length comparison ties |
| **Trigram index optimization (ADR-0009)** | estrategia | [src/tcf/core/online.py:97-112 (_melhor_pref uses prefix_index.get), 115-126 (_melhor_suf uses suffix_index.get), 184-185, 196-197, 222-223 (index maintenance)](../../../src/tcf/core/online.py) | trigram key k=3; bucket size B varies (typically 2-100, up to 1000+ for dates) | always in canonical OBAT; indexes built incrementally as strings processed |

### Detalhamento

**`Token type: TokLit (literal)`** (token-type, [src/tcf/core/online.py:30-35](../../../src/tcf/core/online.py))  
Dataclass representing a literal substring that cannot be compressed via reference to previous strings. Fields: text (str). Emitted when no LCP/LCS match >= min_len exists for a span, or when span falls between prefix and suffix references. Does NOT contribute to 'coverage' in greedy algorithm.

**`Token type: TokRefPref (prefix reference)`** (token-type, [src/tcf/core/online.py:38-44](../../../src/tcf/core/online.py))  
Dataclass representing a reference to the first N chars of a previous string. Fields: string_id (1-indexed), length (bytes). Decoder resolves via strings_unicas[string_id-1][:length]. Enables affix-based compression of leading patterns (e.g., email prefixes, URL paths). Byte-canonical: always uses 1-indexed IDs matching insertion order.

**`Token type: TokRefSuf (suffix reference)`** (token-type, [src/tcf/core/online.py:47-53](../../../src/tcf/core/online.py))  
Dataclass representing a reference to the last N chars of a previous string. Fields: string_id (1-indexed), length (bytes). Decoder resolves via strings_unicas[string_id-1][-length:]. Complements TokRefPref for stable trailing patterns (e.g., domain suffixes, file extensions, unit suffixes). Byte-canonical: preserves insertion order.

**`LCP (Longest Common Prefix) calculation`** (heuristica, [src/tcf/core/online.py:59-64 (public); 75-82 (_lcp_len_capped)](../../../src/tcf/core/online.py))  
Computes max k such that a[0:k] == b[0:k]. Linear scan O(min(len(a), len(b))). _lcp_len_capped() variant accepts cap parameter to limit search (used in _melhor_pref with max_len=ls to avoid overflow). No memoization; called O(N*B) times per column (N=strings, B=avg bucket size). Critical performance path optimized via trigram index (ADR-0009).

**`LCS (Longest Common Suffix) calculation`** (heuristica, [src/tcf/core/online.py:67-72 (public); 85-94 (_lcs_len_capped)](../../../src/tcf/core/online.py))  
Computes max k such that a[-k:] == b[-k:]. Linear scan from both string ends O(min(len(a), len(b))). _lcs_len_capped() variant accepts cap. Called O(N*B) times (same as LCP). Implements backward indexing a[len(a)-1-i] and b[len(b)-1-i].

**`Hash prefix index (trigram bucketing)`** (marcador, [src/tcf/core/online.py:184, 196-197, 222-223; processar() initializes and maintains](../../../src/tcf/core/online.py))  
dict[str, list[int]] mapping first 3 chars (s[:3]) to zero-indexed IDs of strings with that prefix. Bucket order = insertion order = ascending ID order (preserves tie-break). Example: {'abc': [0, 3, 7], 'def': [1, 2]} for strings indexed 0-3. Size: typically 10-100 buckets per 100-5000 strings; memory O(N) where N=total string count. Trigram k=3 chosen because min_len=3 implies any valid LCP match requires s[:3]==prev[:3].

**`Hash suffix index (trigram bucketing)`** (marcador, [src/tcf/core/online.py:185, 197-198, 223; processar() manages](../../../src/tcf/core/online.py))  
dict[str, list[int]] mapping last 3 chars (s[-3:]) to candidate IDs. Enables O(B) lookup in _melhor_suf instead of O(N) linear scan. Bucket insertion order preserved. For date-like strings (prefixes 199/200/202), buckets can grow large (2x slowdown vs partkey), but overall 5.4x speedup (ADR-0009).

**`_melhor_pref — find best prefix match`** (filtro, [src/tcf/core/online.py:97-112](../../../src/tcf/core/online.py))  
For string s, find best prefix LCP match against all strings in prefix bucket. Returns (best_id, best_len) where best_id is 1-indexed. Algorithm: iterate bucket (ascending ID order, preserves insertion order), compute _lcp_len_capped(s, prev, max_len=ls) for each, keep max by length (strict > comparison). Tie-break: first occurrence wins (due to > not >=). Filters by L >= min_len. Returns (0, 0) if bucket empty or no match >= min_len. O(B) where B=bucket size (vs O(N) naive). Empirically B=2-10 for most columns, up to 100+ for date prefixes.

**`_melhor_suf — find best suffix match`** (filtro, [src/tcf/core/online.py:115-126](../../../src/tcf/core/online.py))  
Mirror of _melhor_pref for suffix. Finds best LCS match in suffix bucket. Same logic: iterate bucket ascending, _lcs_len_capped(..., max_len=ls), keep max by length, filter >= min_len, tie-break first-wins. Returns (0, 0) if empty/no match. O(B) complexity.

**`_escolher_par — greedy cover with overlap detection`** (estrategia, [src/tcf/core/online.py:129-162](../../../src/tcf/core/online.py))  
Greedy algorithm choosing (pref_id, pref_len, suf_id, suf_len) to maximize coverage of string s without overlap. Fast path: if bp_len + bs_len <= ls (no overlap), return immediately. Otherwise: generate 2 candidates: (A) best_pref + suf_constrained_by(ls-bp_len), (B) best_suf + pref_constrained_by(ls-bs_len). Tie-break: max total coverage > max prefix length. Ensures middle section s[bp_len:ls-bs_len] is literal (non-empty). Preserves byte-canonical order from v0.

**`min_len threshold`** (threshold, [src/tcf/core/online.py:102-103, 110, 116, 124 (filtering); default 3 set in processar()](../../../src/tcf/core/online.py))  
Minimum length (in bytes) for any LCP/LCS match to be considered valid. Default value 3 reflects: (a) trigram index k=3, (b) cost-benefit (2-char match overhead not worth it), (c) M9 baseline default. Filtering occurs in _melhor_pref/suf: 'if L >= min_len'. Auto-detection via H-DA-11 (ADR-0010) chooses {3,4,5,6} per column based on avg_len + cardinality + is_numeric heuristics, captures 99.5% oracle gain.

**`Auto-detect min_len (H-DA-11, ADR-0010)`** (estrategia, [src/tcf/auto_min_len.py:25-68](../../../src/tcf/auto_min_len.py))  
Decision tree heuristic choosing optimal min_len per column. Computes from ColumnFeatures (n_rows, avg_len, cardinality, is_numeric). Gating: n < 100 -> default 3 (preserves M9 baseline in small datasets). Decision tree: card < 0.2 -> 3; avg_len >= 25 -> 6; avg >= 8 and card >= 0.4 -> 6; avg >= 5 and is_numeric and card >= 0.8 -> 6; avg >= 12 and card >= 0.7 -> 5; avg >= 3 and card >= 0.2 -> 4; else 3. Validated on 58 real-world columns (Adult Census, TPC-H): 9.87% weighted compression gain, 99.5% oracle capture. Called in encoder.py _encode_column() before OBAT.

**`Cadence detection (H-DA-08, ADR-0008)`** (estrategia, [src/tcf/auto_cadence.py:28-96](../../../src/tcf/auto_cadence.py))  
2-rule heuristic determining if column has structural 'cadence' (repeating patterns in shape/LCP-LCS). Rule 1 (wrapper+counter): uniform lengths in first N strings + LCP+LCS ratio >= threshold per consecutive pair -> dispara prefer_shape_consistency hint. Rule 2 (numeric high-card): all sampled strings numeric + card > 0.5 -> dispara hint. When detected, encoder switches from processar() to processar_with_hint(..., prefer_shape_consistency=True). Sub-exp validation: Real TPC-H detected ~25% of columns; marginal gain in multi-layer pipeline (hinted by presence of seq-RLE baseline).

**`processar() — canonical OBAT`** (estrategia, [src/tcf/core/online.py:179-225](../../../src/tcf/core/online.py))  
Main entry point. Tokenizes list of unique strings via LCP+LCS greedy cover. For each string idx=0: emit [TokLit(s)]. For idx>=1: call _escolher_par, emit tokens (TokRefPref + TokLit(middle) + TokRefSuf), maintain prefix/suffix indexes. Returns (tokens_por_string: list[list[Token]], log: str). Log contains per-string coverage %, matched IDs, etc. Byte-canonical: iterates bucket ascending ID order; tie-breaks via > strict. Complexity: O(N*B) where N=strings, B=avg bucket size; trigram index reduces from O(N^2) to O(N*B).

**`processar_with_hint() — cadence-aware OBAT`** (estrategia, [src/tcf/obat_shape.py:64-120](../../../src/tcf/obat_shape.py))  
Variant of processar() with optional shape-consistency hint. When prefer_shape_consistency=True and cadence detected, tries to replicate token structure (p_src, p_len, s_src, s_len) from previous string. Tries 3 fallbacks: (1) exact shape match (LCP/LCS exactly match), (2) wider match (reduce lengths to max available), (3) greedy fallback (use canonical _escolher_par). Returns same token structure as processar(). Motivation: columnar data often has repeating formats (fixed-width prefix, varying middle, fixed suffix like domain); hint speeds convergence. When prefer_shape_consistency=False, behaves identically to processar().

**`reconstroi() — roundtrip validation`** (helper, [src/tcf/core/online.py:165-176](../../../src/tcf/core/online.py))  
Reconstructs original string from token list. For TokLit: append text. For TokRefPref/Suf: resolve from strings_unicas and extract slice. Used internally for testing only; not part of encode/decode pipeline (HCC layer handles serialization). Termination guaranteed: DAG of references (j < i always).

**`ColumnFeatures pre-pass`** (decision-point, [src/tcf/column_features.py:51-84](../../../src/tcf/column_features.py))  
Unified feature extraction O(N). Computes n_rows, n_unicas, avg_len, cardinality, is_numeric (sample-based check), sample (first 20 strings). Immutable dataclass (frozen=True). Used by detect_min_len_from_features, detect_cadence_from_features. Introduced ADR-0010 / H-DA-11c (May 22) to avoid recomputing basic stats in multiple heuristics. Called unconditionally in _encode_column() even if pre_pass disabled (barato, utile for side_outputs).

**`Greedy cover selection criterion (maximize total coverage)`** (decision-point, [src/tcf/core/online.py:155-161](../../../src/tcf/core/online.py))  
In _escolher_par: when prefix+suffix overlap, choose candidate (pref, suf pair) maximizing pref_len + suf_len (total coverage). Tie-break: prefer candidate with max pref_len (preserves v0 behavior). Ensures middle literal always non-empty (prevents TokLit + TokRef collapse).

**`Tie-break rule: first occurrence wins`** (decision-point, [src/tcf/core/online.py:108-111 (_melhor_pref), 122-125 (_melhor_suf)](../../../src/tcf/core/online.py))  
When two strings have identical LCP/LCS length to current string, prefer the one with earlier insertion order (lower ID). Implemented via 'if L > best_len' (strict >, not >=). Preserves byte-canonical determinism: order of strings_unicas -> consistent token selection -> identical bytes across runs.

**`Trigram index optimization (ADR-0009)`** (estrategia, [src/tcf/core/online.py:97-112 (_melhor_pref uses prefix_index.get), 115-126 (_melhor_suf uses suffix_index.get), 184-185, 196-197, 222-223 (index maintenance)](../../../src/tcf/core/online.py))  
Hash-indexed prefix/suffix bucketing reduces search from O(N) to O(B) where B=bucket size. k=3 (trigram) matches min_len=3: any valid LCP/LCS match implies matching first/last 3 chars. Bucket order = insertion order (ascending ID) preserves tie-break. Empiric speedup: 5.4x on lineitem 5k (ADR-0009 sub-exp), 1.77x in full pipeline. Byte-canonical preserved: bucket iteration ascending, comparison > strict. Memory: ~2-4MB for lineitem 5k.

### Notas


CONTROL FLOW SUMMARY:
The OBAT subsystem is a 3-stage decision pipeline: (1) ColumnFeatures pre-pass (always), (2) Cadence + min_len detection (if cfg.pre_pass), (3) OBAT tokenization (canonical processar vs. shape-hint variant). Tokenization per-string: lookup prefix/suffix buckets via trigram hash, find best LCP/LCS match, greedily choose non-overlapping (prefix, suffix) pair, emit tokens. Byte-canonical via strict > tie-break + bucket insertion order.

PERFORMANCE CHARACTERISTICS:
- Time: O(N*B) where N=unique strings, B=avg bucket size (2-100, max ~1000 for dates). Without index: O(N^2). ADR-0009 empiric: 5.4x speedup (lineitem 5k), 1.77x in full pipeline.
- Space: O(N) for strings + O(N*k) for two hash dicts (k=3 per string), typically ~2-4MB per 5k-row column.
- Compression: Canonical M9 (no hint): 1615B D1-D9 baseline. M10 (auto-cadence + seq-RLE): 1523B. Real-world (Adult+TPC-H): ~9.87% gain via auto-min_len.

KEY INSIGHTS:
1. Trigram index k=3 is hard-wired but works because min_len=3 is default. If min_len increases, k should increase too.
2. Greedy cover is fast but suboptimal (2-candidate fallback when overlap); optimal would be DP (exponential). Acceptable tradeoff.
3. Cadence hint (H-DA-08) is ~25% of real columns but marginal gain in multi-layer context; mainly useful for fixed-format data.
4. Auto-min_len (H-DA-11, ADR-0010) captures 99.5% oracle; 4 decision-tree rules + 1 gating condition.
5. Byte-canonical determinism: insertion order in bucket + strict > comparison. Critical for reproducibility.

ROADMAP TOUCHES (v2.0):
- H-PERF-04: middle-trigram indexing for dates; Patricia trie as alternative
- H-PERF-05: HCC optimization (not OBAT scope)
- H-PERF-06: Cython/Rust port of lcp_len/lcs_len
- H-DA-11b/c: tuning cardinality thresholds, extracting unified detect_features()
- Lossy/dictionary modes: new Token types, processar_lossy variant
- ML-based shape prediction: extend cadence heuristic

TESTING NOTES:
- M10 baseline = 1523B D1-D9 (test_regression_v1_baseline.py validates)
- Round-trip tested in test_core_rt.py (processar -> tokens -> reconstroi -> original)
- ADR-0009 sub-exp: byte-identical D1-D9 + lineitem 1k/5k
- Side outputs (SideOutputs class) capture column_features, cadence_detected, min_len, obat_log for debugging

REFERENCES:
- docs/algorithms/OBAT.md — formal spec
- docs/adr/0009-obat-trigram-index-optimization.md — trigram index decision + empirics
- docs/adr/0010-auto-detect-min-len.md — H-DA-11 heuristic + oracle comparison
- docs/adr/0008-detect-cadence-numeric-rule.md — cadence rules 1 & 2
- src/tcf/core/online.py:1-25 — design narrative in docstring


---
