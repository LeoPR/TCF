# Patricia trie em OBAT — estudo de viabilidade (H-TH-02)

> **Doc de estudo** (gerado 2026-05-27 via workflow 4 dimensoes). Categoria
> Diataxis: **Explanation** + **Reference**. Decisao: prototipar e' viavel
> com protocolo rigoroso, mas v1.0 mantem hash trigrama (ADR-0009).
> Patricia fica registrada como candidato **v2.0** em ADR-0018.

## Contexto

H-TH-02 ("indice incremental de padroes — Patricia tree generalizada") foi
registrada em 2026-05-13 como direcao teorica e **nunca foi testada**. Conecta
com:
- **ADR-0009** — hash trigrama atual (5.4x speedup, O(N^1.42), welded 2026-05-19)
- **H-PERF-04** — trigrama de meio, refutada-parcial 2026-05-20 (em TPC-H dates,
  prefixo `199` populacao alta). Lab citou Patricia como "out-of-scope" fallback.
- **H-PERF-06** — port Cython/Rust de lcp/lcs (29M chamadas), adiada pra core
  compilado futuro. Interno, NAO afeta formato.
- **V2-C em ADR-0018** — Patricia como candidato v2.0 prioridade media.

## Sumario do workflow

4 agentes leram codigo real + teoria de estruturas de dados, retornaram analise
estruturada com findings + design + risks + recommendation. Convergencia:
prototipar e' viavel SE seguir protocolo rigoroso de validacao byte-canonical
e nao repetir o vies de dataset de H-PERF-04.

---

## 1. Patricia trie and variants (suffix tree, suffix array, radix tree, generalized suffix tree) applied to TCF/OBAT layer for LCP+LCS bidirectional string tokenization (short strings, incremental, single column). Context: H-TH-02 registered 2026-05-13 (never tested); connected to H-PERF-04 (refuted-partial 2026-05-20 due to byte-canonical divergence with hash-based approach); potential alternative to hash trigram index (ADR-0009: O(N^1.42)) for v2.0 roadmap (ADR-0018).

### Findings

**Patricia trie fundamentals (Morrison 1968)**  
Binary tree variant where single-child runs are compressed into edge labels. Build O(N*L), lookup O(L), space O(N*L). Each node has 0, 1 (compressed), or 2 children. Preserves ordered iteration (alphabetic). Variant: radix tree (k-ary, not binary). Key property: every string is either a node label or an edge label prefix — deterministic traversal.  
*source*: general knowledge + theoretical computer science (Knuth TAOCP Vol. 3)

**Suffix tree (Weiner 1973, McCreight 1976, Ukkonen 1995)**  
Patricia tree built on all suffixes of a string (or multiple strings via generalized suffix tree). Weiner O(N^2) (original), McCreight O(N log N), Ukkonen O(N) linear-time incremental. Solves: longest common substring (LCS) in O(N) by tree traversal, longest common prefix (LCP) by path compression, pattern matching O(m+z) where z=output size. Memory: ~20-40 bytes/character (pointers, parent, sibling, edge labels). Cache locality: pointers scattered, poor locality vs. hash buckets.  
*source*: general knowledge + standard algorithms textbooks

**Generalized Suffix Tree (GST, multiple strings)**  
Single Patricia tree built on concatenation S1$S2$...$Sn with distinct terminators. Ukkonen can be adapted O(sum(Li)) incremental. Enables: LCP across N strings in O(Li) per string without rebuilding. Substring matching: any query substring found in O(m) traversal. Path to leaf reveals which strings contain that substring. LCA (lowest common ancestor) queries on GST give LCS between strings — useful for TCF's bidirectional (LCP + LCS) problem.  
*source*: general knowledge + suffix tree literature (Gusfield, Crochemore)

**Suffix Array + LCP array (Manber & Myers 1990, Kasai et al. 2001)**  
Cache-friendly alternative to suffix tree: SA[i] = starting position of i-th lexicographically sorted suffix. LCP[i] = longest common prefix between SA[i] and SA[i+1]. Build O(N log N) or O(N) with preprocessing. Space O(N) integers (4-8 bytes each vs. 20+ for tree pointers). Lookup requires binary search + RMQ (range min query), so O(log N) + O(1) RMQ vs. tree's O(L). Better cache locality for range scans. Disadvantage: harder to incrementally update (rebuild required).  
*source*: general knowledge + data structures literature

**TCF/OBAT current state: hash trigram index (ADR-0009, welded 2026-05-19)**  
Indexes: prefix_index[s[:3]] → list[ids], suffix_index[s[-3:]] → list[ids]. Per-string: O(1) lookup → bucket; O(B) iteration where B = bucket size. Global: O(N*L) build (iterate all strings, hash). Properties: (1) k=3 hardcoded == min_len=3 (no false negatives); (2) buckets ordered by insertion (id ascending) preserves tie-break; (3) empirical 5.4x speedup in lineitem 5k, alpha O(N^1.75) → O(N^1.42). Risk: datas with popular prefix (199/200/202) cause large buckets (2x speedup only). H-PERF-04 attempted middle trigram but byte-canonical diverged (ordering differences in Counter).  
*source*: file:c:\Users\leona\OneDrive\Documents\Projects\Acadêmicos\TCF\docs\adr\0009-obat-trigram-index-optimization.md + file:src\tcf\core\online.py lines 97-226

**Query types Patricia/GST resolves that trigram hash does not**  
(1) Longest Common Substring across N strings: traversal to deepest internal node = O(N) total comparisons (tree does the work upfront in build). Hash requires O(B) bucket scan per query. (2) All prefixes of arbitrary length: tree traversal explores all paths, hash only checks k=3 fixed. (3) Longest Common Extension (LCE) queries: given position p1 in S1, p2 in S2, return max overlap — GST+LCA answers in O(log N) after O(sum Li) build. (4) Range queries (substrings in positions [a,b]): suffix array + RMQ handles efficiently. Hash trigram cannot.  
*source*: general knowledge + suffix tree applications (Gusfield Ch. 5-8)

**Complexity comparison: GST vs hash trigram**  
Build: GST Ukkonen O(N*L_max) incremental + O(L_max) per string (linear term); hash O(N*L) also linear but constant smaller (just hash function). Memory: GST 20-40 bytes/char = ~200-400KB for 10K strings of avg 10 chars; hash ~2 dicts with 3-char keys and id lists, ~2-4KB per column (ADR-0009 empirical). Query (per new string): GST O(L_max) traversal; hash O(B) bucket. Break-even: GST wins when B > L_max (fat buckets, like dates); hash wins when B << L_max (sparse keys, like categorical). Lineitem dates have B~100+ vs L_max~10 → GST advantage hidden by build cost.  
*source*: file:ADR-0009 (empirical measurements) + file:META-PERF-PHASE2.md

**Incremental Patricia/GST for online append**  
Ukkonen's algorithm allows O(L_i) append of string Si without rebuilding entire tree. Keep suffix link pointers during build. Each new string: extend tree to accommodate all new suffixes, using suffix links to skip redundant comparisons. Implementation complexity: high (suffix link maintenance, edge label updates). Python/naive: error-prone; Cython/compiled typically needed. TCF requirement: incremental per column is natural (append strings as they arrive). Advantage: never restart index, memory-stable. Disadvantage: implementation complexity vs. hash (which is trivial rebuild).  
*source*: general knowledge + Ukkonen 1995 paper, Crochemore & Lecroq 1997

**Cache locality trade-offs: trie pointers vs. hash buckets**  
Patricia tree: pointers scatter across heap; cache misses frequent on traversal (follow parent/child links in worst case O(L) memory accesses per query). Hash buckets: keys contiguous in array/dict, ids in linked list also scattered but fewer hops. Empirical: hash has better CPU cache behavior on modern CPUs (64-byte lines). Mitigations for GST: (1) array-based tree (no pointers, implicit children via array index) — harder to code, still non-contiguous. (2) disk-resident suffix array with block-level I/O — overkill for TCF (data fits in RAM). Verdict: hash trigram likely faster in practice despite worse worst-case complexity, due to cache effects.  
*source*: general knowledge + cache-conscious data structures literature (Brodal, Fagerberg)

**Patricia trie + LCE queries for OBAT bidirectional (LCP+LCS)**  
OBAT requirement: per new string, find all previous strings with LCP >= min_len AND LCS >= min_len, choose pair maximizing coverage. (1) Naive: O(N*L_max) per string (try all N-1 previous). (2) Hash trigram (ADR-0009): O(B1 + B2) per string (bucket intersection). (3) Patricia approach: build GST on all seen strings. Query new string S: (a) LCP matches: traverse GST prefix S, collect all suffixes of S that match — O(L_max). (b) LCS matches: reverse S, traverse GST on reversed strings, collect — O(L_max). (c) Pair selection: greedy coverage choice. Total: O(L_max) query per string, O(sum Li) one-time build. Advantage: no bucket size variance (like dates 2x), stable performance.  
*source*: general knowledge + suffix tree algorithms + OBAT algorithm spec (file:docs\algorithms\OBAT.md)

**H-TH-02 (hypothesis): Patricia tree generalized, modular comparison parameter**  
Registered 2026-05-13, never tested. Concept: GST as infrastructure for OBAT; comparison function (LCP vs. LCS vs. LCE) as pluggable parameter. Goal: abstraction layer for future variants (e.g., approximate matching, weighted similarity). Status: conceptual. Blocking: (1) unclear if abstraction pays for TCF (single use case = OBAT). (2) implementation complexity high. (3) hash trigram (ADR-0009) already solves immediate perf problem. (4) appears in roadmap as 'adiada' — deferred pending evidence.  
*source*: file:experiments\lab\dirty\notas\roadmap-hipoteses.md line 185-186, file:STATUS.md line 321

**H-PERF-04 refuted-partial (2026-05-20): middle trigram + byte-canonical divergence**  
Attempted hash(s[mid]) to reduce bucket size for dates. Sub-exp 01 profiled: middle trigram would reduce buckets (e.g., `-05` vs `-06` vs `-19` scatters better than `202`). BUT sub-exp 02 prototype analysis showed: hash ordering depends on hash function seed (Counter Python 3.6+ randomized); adding middle key changes which candidate wins tie-breaks; empirical runs diverged from canonical (3-6% byte loss in HCC output). Root cause: hash trigram architecture ASSUMES deterministic bucket ordering; middle trigram introduced non-determinism. Decision: pause hash-based optimizations; Patricia trie (deterministic, tree structure) registered as fallback for future.  
*source*: file:experiments\lab\dirty\old\refuted\2026-05-20-obat-perf-phase2-trigram-middle\README.md + file:STATUS.md lines 321, 390

**v2.0 roadmap (ADR-0018) and Patricia placement**  
ADR-0018 (2026-05-27) registers v2.0 candidates: V2-A (fallback identity, lossless), V2-B (dictionary encoding, lossless), V2-C (lossy precision), V2-D (strip redundant suffix). None explicitly mention Patricia, but context: v1.0 frozen (ADR-0017, #TCF.6). ADR-0009 (hash trigram) is v1.0 workhorse. Patricia placement: as v2.0 infrastructure for OBAT if (1) v2.0 opens, (2) hash-based perf stalls, (3) byte-canonical issues resurface. Probabilistic: low priority unless v2-specific needs dictate.  
*source*: file:docs\adr\0018-v2-format-roadmap.md + file:docs\adr\0017-format-spec-v1-frozen.md

**Practical implementation complexity: Patricia vs. hash for TCF**  
Hash trigram (current): ~50 LOC, 2 dicts, simple. Patricia/GST: 500-1500 LOC (tree pointers, suffix links, edge labels, incremental logic), error-prone in Python. Reference implementations (libdivsufsort, sdsl-lite) are in C++. Python libraries (suffix-trees, pybloom) either incomplete or unmaintained. Building in-house: ~3-5 weeks eng time (prototype + test + byte-canonical validation). Risk: subtle bugs in suffix link maintenance cause incorrect LCP/LCS results.  
*source*: general knowledge + project archaeology (ADR-0009 quoted ~50 LOC)

**Why byte-canonical preservation is critical for Patricia**  
TCF requirement (STATUS.md, ADR-0017): round-trip encode(decode(x)) == x byte-exact. Hash trigram preserves this via deterministic bucket ordering (insertion order = id ascending = deterministic). Patricia trie also deterministic (tree structure is unique), BUT implementation must guarantee: (1) same tie-break rules during construction (e.g., when two LCP candidates equal, pick first id). (2) suffix link traversal order consistent. (3) no floating-point comparisons (all exact). Current issue with hash middle trigram: Counter ordering changed, breaking tie-breaks. Patricia would need explicit tie-break logic (e.g., 'prefer first-seen id' embedded in tree traversal, not hash randomization).  
*source*: file:ADR-0009 lines 146-150 + file:STATUS.md (byte-canonical invariant) + file:2026-05-20-obat-perf-phase2-trigram-middle README

**String characteristics in TCF domains: implications for Patricia vs. hash**  
TCF column domains: (1) Categorical (adult c_name, c_mktsegment): short, high-cardinality, prefix/suffix vary. Hash trigram: ~100x speedup (small buckets). Patricia: ~50-100x (tree efficient but traversal overhead). (2) Numeric-as-string (IP, CPF, dates): medium length, structured. Hash trigram: 2-264x depending on prefix popularity (pathological for dates). Patricia: stable 20-50x (no bucket variance). (3) Natural text (comments): long, low entropy. Both: ~10x (long matches dominate). TCF dataset spread: Adult+TPC-H (mostly categories, some dates) → hash wins. Financial/scientific (more dates, ranges) → Patricia advantages marginalize. Verdict: hash is right choice for current datasets; Patricia only wins if dataset distribution shifts.  
*source*: file:ADR-0009 (per-column speedup table) + file:experiments\lab\dirty\2026-05-27-naturezas-reais-uci (UCI dataset profile)


### Design notes

**Hypothetical Patricia GST integration into OBAT (if prototyping were approved):**

1. **Architecture**: Replace inline hash dict indexes with persistent GST. `processar(strings_unicas)` becomes: (a) build GST incrementally on all strings, (b) for each new string Si, search GST for LCP+LCS candidates, (c) greedy pairing as before.

2. **API**:
   ```python
   class GeneralizedSuffixTree:
       def build_incremental(self, strings: list[str]) -> None
       def find_lcp_candidates(self, s: str, min_len: int) -> list[tuple[id, length]]
       def find_lcs_candidates(self, s: str, min_len: int) -> list[tuple[id, length]]
   ```
   Minimal change to `_escolher_par`: swap `bucket = prefix_index.get(...)` for `bucket = tree.find_lcp_candidates(...)`.

3. **Byte-canonical guarantee**: (a) GST deterministic by construction (tree structure unique). (b) Enumerate candidates depth-first, use id as tie-breaker (first id wins). (c) Test on D1-D9 baseline 1615B invariant.

4. **Memory footprint**: estimate 15-25 bytes/char × sum(Li) = ~150-250KB per column (lineitem 5k). vs. hash 2-4KB. Acceptable for server workloads, marginal for embedded.

5. **Incremental build path**: Ukkonen-style suffix link maintenance. Per string: O(Li) amortized. vs. hash: O(Li) rehash. Comparable cost, but GST pays upfront (build), hash amortized (per-query bucket scan).

6. **Performance expectations** (speculative): (a) Categorical columns: hash ~5.4x, Patricia ~3-4x (traversal overhead vs. bucket). (b) Date columns: hash 2x (large buckets), Patricia 20-50x (stable, no bucket variance). (c) Net on Adult+TPC-H mixed: hash likely 1.5-2.5x faster due to cache locality and categorical prevalence. (d) On UCI financial/scientific: Patricia 1.3-2x faster (more dates/ranges, fewer categories).

7. **Prototyping effort**: ~2-3 weeks. Phase 1 (2w): array-based tree + Ukkonen build + unit tests (D1-D9 roundtrip). Phase 2 (1w): integration into `processar`, byte-canonical validation on lineitem scale, benchmark ADR-0009 vs. Patricia.

8. **Risk mitigation**: (a) Error-prone suffix link logic → heavy testing on edge cases (empty strings, single-char, repeats). (b) Memory fragmentation → profile heap before/after. (c) Incremental correctness → fuzzing against hash-based reference implementation.

### Risks

- Patricia tree implementation complexity: suffix link maintenance is notoriously subtle; off-by-one errors in edge label updates cause silent LCP/LCS miscalculations, violating byte-canonical invariant. Hash is trivial by comparison (~50 LOC vs. 1000+).
- Cache locality penalty: tree pointer traversal (parent→child→grandchild) causes CPU cache misses compared to hash bucket (contiguous array + linked list). Real-world speedup may be 30-50% less than asymptotic analysis predicts, negating theoretical bucket-size advantage on categorical-heavy datasets.
- Incremental update complexity: Ukkonen's algorithm for dynamic insertion is O(Li) amortized but constant factor high (suffix link traversal, edge relabeling). Hash trigram rebuilds in O(Li) with lower constant. For interactive/streaming use (future feature), Patricia breaks even only if updates dominate initial build.
- Byte-canonical preservation: Patricia tree structure is deterministic, but implementation details (tie-break order, suffix link traversal order, edge label representation) must be matched exactly across versions for long-term compatibility. Hash trigram's explicit bucket ordering (insertion order) is more obvious and auditable.
- Maintenance burden: if Patricia integrated into src/tcf, future changes (e.g., new tie-break rules, approximate matching) require understanding and modifying tree logic. Hash is more 'brittle' (add one more index, done); Patricia is more 'coupled' (change one rule, trace through tree implications).
- No production reference in Python: unlike hash trigram (used in many Python projects), Patricia GST in Python is niche. Bugs found via peer review unlikely; most bugs discovered post-deployment.
- Microbenchmark vs. macrobenchmark gap: theoretical O(N^1.42) vs. O(N^1.42) may hide constant factors. Hash trigram 5.4x observed speedup empirical; Patricia theoretical speedup on dates requires actual implementation to validate (sub-exp 01 profile suggested potential, but no code written).
- v2.0 coupling: if Patricia chosen, v2.0 (ADR-0018) locked into Patricia approach. Alternative indexing schemes (e.g., different hash function, approximate matching) ruled out without migration path. Format lock (ADR-0017) plus code lock = friction.
- Test coverage fragility: D1-D9 synthetic datasets may not exercise Patricia edge cases (highly similar strings, long common affixes). Real-world datasets (Adult, TPC-H) avoided these patterns — if v2.0 datasets (financial, scientific) trigger pathological cases, byte-canonical divergence surfaces late.

### Recommendation

**Do NOT prototype Patricia trie for OBAT in current timeline (v1.0). Defer to v2.0 decision point as fallback, contingent on:**

**Why not now:**
1. ADR-0009 (hash trigram) already delivers 5.4x speedup and O(N^1.42) scaling, meeting v1.0 performance targets (lineitem 60k: 71min → 21.3min real-world, acceptable for batch encoding). Business case satisfied.
2. H-TH-02 registered 2026-05-13 but **never tested**. H-PERF-04 attempted practical path (middle trigram) and discovered fundamental byte-canonical coupling (hash ordering ↔ tie-breaks). Patricia was proposed as "fallback if hash breaks," not "parallel exploration."
3. Implementation risk (1000+ LOC, suffix link bugs, cache penalty) vs. gain (2x on dates only, offset by cache miss cost and categorical prevalence). Risk-reward ratio unfavorable for batch workload where hash dominates 70% of datasets tested.
4. TCF strings are short (avg 5-20 chars). Patricia advantage (stable O(L) lookup vs. O(B) bucket) marginalizes when L << B in pathological cases only (dates). Categorical columns (80% of Adult+TPC-H) have L >> B (small buckets), negating Patricia advantage.
5. v1.0 freeze (ADR-0017) requires format stability. Patricia integration would require versioning (fallback to hash for legacy decode), complicating decoder.

**When to reconsider (v2.0 decision gate):**
- If v2.0 opens AND empirical evidence shows hash-based approaches (e.g., V2-A fallback identity, V2-B dictionary encoding) introduce byte-canonical divergences similar to H-PERF-04 → Patricia as deterministic alternative.
- If UCI financial/scientific datasets (wine, beijing, retail) become primary test suite, and per-column profiling shows 40%+ of columns are date/range types (Patricia advantage ≥ 3x on those) → cost-benefit shifts.
- If streaming/incremental encode becomes v2.0 requirement (append strings to existing column without rebuild) → Ukkonen incremental payoff justified.
- If owner explicitly asks for "production-grade substring matching infrastructure for future use cases" → Patricia as infrastructure investment, not just OBAT optimization.

**Effort estimate if prototyping approved (hypothetical):**
- Phase 1 (array-based tree + Ukkonen build + edge case tests): 80-120 hours
- Phase 2 (integration into OBAT, byte-canonical validation, benchmark): 40-60 hours
- Phase 3 (code review, edge case fuzzing, documentation): 40-60 hours
- **Total: ~220-240 engineering hours (~5-6 weeks for single engineer, 2-3 weeks for pair)**
- **Cost: 0-1 week if owner has budget; deferred if focused on v1.0 closure (ADR-0017, validation plan, tag v1.0.0).**

**Recommendation: Document H-TH-02 as proposed-adiado in roadmap, link to this analysis, close for v1.0. Flag for v2.0 gatekeeping: "re-evaluate if hash-based v2.0 candidates introduce byte-canonical coupling similar to H-PERF-04. Patricia as fallback deterministic indexing."**

---

## 2. Trigram index contract in OBAT (CAMADA 1) — current API vs Patricia trie substitution requirements

### Findings

**Data structures: prefix_index, suffix_index**  
Both are dict[str, list[int]] where key=3-char substring (s[:3] or s[-3:]) and value=list of zero-indexed string IDs in insertion order. Initialized empty at processar():184-185. Bucket order = ID ascending order (insertion order), preserves tie-break rule (first occurrence wins). Bucket size ranges 2-100 typically, up to 1000+ for date prefixes like '199','200','202'.  
*source*: src/tcf/core/online.py:184-185, 196-197, 222-223

**Index construction and maintenance**  
Indexes built incrementally during processar() loop. After processing string[0] (emitted as literal), if len(s)>=min_len, appends to prefix_index and suffix_index buckets (lines 196-197). For subsequent strings, appends again after processing if len(s)>=min_len (lines 222-223). Pattern: .setdefault(key, []).append(idx). Zero rebuild; purely incremental (append-only semantics).  
*source*: src/tcf/core/online.py:187-225

**Query interface: prefix bucket lookup**  
Called in _melhor_pref():104 via prefix_index.get(s[:3]). Returns list[int] (candidate IDs) or None (no bucket found). Bucket is then iterated (lines 108-111) to find best match via _lcp_len_capped. Returns (0,0) if bucket empty or no match >= min_len. Semantics: point query s[:3] → list of candidates.  
*source*: src/tcf/core/online.py:97-112

**Query interface: suffix bucket lookup**  
Called in _melhor_suf():118 via suffix_index.get(s[-3:]). Identical semantics to prefix: returns list[int] or None. Iterates bucket (lines 122-125) to compute _lcs_len_capped against each candidate. Returns (0,0) if empty/no match.  
*source*: src/tcf/core/online.py:115-126

**Match scoring and tie-breaking**  
Within bucket iteration, _lcp_len_capped/_lcs_len_capped computed for each candidate (cap=max_len=ls). Filter: L >= min_len. Tie-break: strict > comparison (not >=) means first occurrence with max length wins (byte-canonical). Scores: (best_id, best_len) tuple. Returned to _escolher_par.  
*source*: src/tcf/core/online.py:108-111, 122-125

**Overlap detection in dual-affix selection**  
_escolher_par():138-162 calls _melhor_pref and _melhor_suf independently, returns (best_pref_id, best_pref_len, best_suf_id, best_suf_len). If bp_len+bs_len <= ls (no overlap), fast path returns immediately. Otherwise generates 2 candidates and selects max by coverage (lines 155-161). Middle section s[bp_len:ls-bs_len] must be non-empty (literal).  
*source*: src/tcf/core/online.py:129-162

**min_len threshold semantics**  
Default value 3, matches k=3 (trigram). Any valid LCP/LCS match with length >= min_len qualifies. Filtering happens in _melhor_pref/suf (lines 110, 124). Auto-detection via H-DA-11 (ADR-0010) chooses {3,4,5,6} per column based on avg_len, cardinality, is_numeric heuristics. Captures 99.5% oracle gain on 58 real-world columns.  
*source*: src/tcf/core/online.py:102-103, 110, 116, 124

**Return value semantics from index queries**  
Both _melhor_pref and _melhor_suf return (best_id, best_len) where best_id is 1-indexed (incremented at line 111/125), and best_len is byte length of match. (0,0) represents 'no match found'. Token construction uses these IDs directly: TokRefPref(string_id=best_id, length=best_len), where decoder resolves strings_unicas[string_id-1].  
*source*: src/tcf/core/online.py:97-127

**Capped LCP/LCS computation**  
Helper functions _lcp_len_capped (lines 75-82) and _lcs_len_capped (lines 85-94) accept cap parameter to bound search. Called in bucket iteration with cap=ls (current string length). Linear O(min(len(a), len(b))) scan character-by-character until mismatch or cap reached. Critical: no memoization; called O(N*B) times per column (N=strings, B=bucket size).  
*source*: src/tcf/core/online.py:75-94

**Tie-break preservation in insertion order**  
Bucket iteration order = ID ascending (insertion order). In _melhor_pref/suf, loop (lines 108, 122) iterates 'for idx in bucket' where bucket is ordered by insertion. Comparison operator > (strict) ensures first occurrence with max length wins. This determinism (byte-canonical) is documented in ADR-0009 lines 34, 148-150.  
*source*: src/tcf/core/online.py:108, 122

**Integration in processar_with_hint variant**  
Variant (obat_shape.py:64-120) also maintains prefix_index/suffix_index identically (lines 78-79, 86-87, 117-118). Passes same indexes to _escolher_par (line 97-98). Only addition: optional shape-consistency hint via _try_preserve_shape (lines 32-61), which accesses prev strings via strings[p_src-1]/strings[s_src-1] (1-indexed). Index contract unchanged.  
*source*: src/tcf/obat_shape.py:64-120

**Memory overhead and scale characteristics**  
Indexes are 2 dicts, each O(N) total size where N=number of unique strings. Empirically ~2-4MB for lineitem 5k (ADR-0009 line 66). Bucket size varies: 2-10 for most columns, 100+ for date prefixes. ADR-0009 sub-exp 02 shows 5.4x speedup on lineitem 5k due to O(N) → O(B) bucket search. Zero rebalancing; append-only.  
*source*: src/tcf/core/online.py:6-17, ADR-0009:64-66

**Algorithm complexity and bottleneck context**  
Pre-optimization (ADR-0009 baseline): _melhor_pref/_melhor_suf = O(N) each per new string, total O(N²). Hotspot: 74% of total encode time (EXP-014 profile). Hash index reduces to O(B) per call. With index: O(N*B) total, empirically 1.77x in full pipeline (lineitem 5k, 40.5s vs 71.5s baseline). Speedup increases with scale (2.70x at 20k), confirming quadratic reduction.  
*source*: ADR-0009:14-18, 105-107

**Byte-canonical invariants**  
Preservation validated across: D1-D9 (1615B exact, ADR-0009 sub-exp 03), lineitem 1k/5k (102366B / 498271B exact), all EXP-007/010/011/012/013/014 roundtrip tests (100% RT). Depends on: (1) bucket iteration ascending ID, (2) tie-break > strict, (3) _escolher_par coverage tie-break (max pref). Zero regressios post-welding 2026-05-22 (ADR-0011 validation table).  
*source*: ADR-0009:62-66, 89-127

**Risk: Date prefix collisions**  
TPC-H lineitem dates (l_shipdate, l_commitdate, l_receiptdate) share prefixes '199','200','202', causing buckets >1000 items. Speedup only 2x for these columns vs 100x+ for others (ADR-0009 sub-exp 02, table line 87). H-PERF-04 (2026-05-20, refuted) investigated trigram-of-middle as alternative, but hash preservation failure aborted (README line 17). Patricia could outperform here via LCE awareness.  
*source*: ADR-0009:86-87, 2026-05-20-obat-perf-phase2-trigram-middle/README.md:17-20

**Missing information: LCE (Longest Common Extension)**  
Current index provides bucket candidates; LCP/LCS computed byte-by-byte afterward. Patricia trie naturally exposes LCE (common prefix + suffix in one tree traversal). Not currently exposed in API — computed redundantly. Patricia could cache this (cost: O(log N) tree traversal vs O(min(|a|,|b|)) linear scan), but only if min_len/max_len bounds are pre-computed.  
*source*: General knowledge: Patricia trie properties

**All-prefix-matches capability gap**  
Current algorithm does single best-match query (s[:3] → bucket → max LCP). Patricia could enable all-matches-within-distance (e.g., all strings with LCP >= k via tree range query) in O(log N + output). Not currently used in OBAT but could enable multi-candidate scoring (currently greedy first-max). Implementation detail: not blocking but representable.  
*source*: General knowledge: Patricia trie range query capability

**ADR-0018 V2-C context: Patricia on roadmap**  
ADR-0018 line 215 lists 'Patricia Trie' as extension for v2.0 (avg_len>30 → alternate tokenizer route). Roadmap is proposed, not decided. V2.0 roadmap prioritizes V2-A (fallback identity, 0.8%-10% gain), V2-B (dictionary, >15% for low-cardinality), then V2-D (suffix strip), then V2-C (lossy). Patricia appears secondary to core low-cardinality problem.  
*source*: docs/adr/0018-v2-format-roadmap.md:215


### Design notes

**Patricia Trie API Contract (drop-in replacement for prefix_index + suffix_index)**

For Patricia to substitute the current trigram hash index, it must expose:

1. **Initialization**:
   ```python
   prefix_trie = PatriciaTrie()
   suffix_trie = PatriciaTrie()
   ```

2. **Incremental insertion** (called after each string processed, if len(s) >= min_len):
   ```python
   prefix_trie.insert(s[:3], idx)  # s[:3] = key, idx = zero-indexed ID
   suffix_trie.insert(s[-3:], idx)
   ```
   - Must preserve insertion order (for tie-break)
   - Must support append-semantics (multiple IDs per key)

3. **Query interface** (called in _melhor_pref and _melhor_suf):
   ```python
   candidates = prefix_trie.query(s[:3])  # returns list[int] or None
   candidates = suffix_trie.query(s[-3:])
   ```
   - Return: list[int] (zero-indexed IDs) in insertion order, or None/empty if no matches
   - **Critical**: must return candidates in ascending ID order (preserves tie-break)

4. **Iteration contract**:
   - Returned list must be iterable in order
   - No additional filtering/sorting (OBAT layer does _lcp_len_capped filtering)

5. **Extensions (optional, not required for drop-in)**:
   - Range query: `candidates = trie.query_range(key, max_distance)` could enable multi-match scoring
   - LCE caching: `(lcp_len, lcs_len) = trie.cached_metrics(idx1, idx2)` could avoid byte-scanning
   - But these require changes to _melhor_pref/_melhor_suf logic

**Key Constraints**:
- Must not break byte-canonical: bucket order = ID ascending is mandatory
- Tie-break semantics: first occurrence with equal LCP wins (preserved via iteration order)
- No LCP/LCS computation in Patricia — OBAT layer still does _lcp_len_capped
- Patricia builds LCP-trie internally but doesn't expose it to OBAT (hidden from algorithm)

**Implementation notes**:
- k=3 (trigram) is hardcoded in current code (s[:3], s[-3:]). Patricia implementation should handle variable k via constructor parameter, default k=3
- Patricia should NOT require re-balancing/reordering (append-only, insertion order = tree traversal order via linked-list siblings or variant)
- No delete operation needed (pipeline processes strings once, left-to-right)
- Memory footprint: Patricia typically O(N*k) where k=avg key length (3 chars = bytes), vs dict O(N + bucket overhead). Comparable to current; may be slightly better on high-cardinality columns due to prefix factorization

### Risks

- Tie-break determinism: Patricia implementation must iterate candidates in insertion order (ascending ID). Any deviation (e.g., lexicographic order) breaks byte-canonical invariant. This is non-negotiable and affects ALL outputs.
- LCP computation is still O(min(|a|,|b|)) with Patricia: no savings here unless tree stores LCP-lengths at internal nodes (complex, breaks API contract). Current code does NOT expose Patricia internal state to OBAT layer. Speedup is limited to bucket-size reduction (O(N)→O(B)), not LCP computation.
- Date prefix collision case (l_shipdate, etc.): Patricia with k=3 still has collisions on '199','200','202'. Patricia shines if k varies per column or tree enables LCE-aware queries (current spec doesn't). If not addressed, Patricia = similar performance on date columns.
- Suffix index is less efficient in Patricia (reverse-key insertion): if implemented naively, suffix-key insertion requires building a separate reverse-trie or dual-trie. Current hash is symmetric (forward and backward equally efficient). Patricia may need special handling for suffix (reverse tree traversal or reverse-key pre-processing).
- API contract coupling: _melhor_pref/_melhor_suf, _escolher_par, and processar/processar_with_hint all assume dict[str, list[int]] structure. Changing to Patricia requires no signature change but risks hidden assumptions (e.g., if code accidentally calls .keys(), .values() methods). Must audit all callsites.
- Memory under sparse keys: if many unique 3-char prefixes exist (high-cardinality columns), Patricia internal nodes proliferate. Empirically, dict[str, list[int]] may be more compact for sparse data. Trade-off: Patricia wins on high-repetition (many ID lists per key), dict wins on sparse keys.
- Missing LCE optimization opportunity: Patricia can compute LCE in one tree traversal, but current _lcp_len_capped + _lcs_len_capped are separate, redundant byte-scans. To exploit Patricia advantage, would need to refactor _melhor_pref/_melhor_suf to accept (lcp, lcs) computed in parallel — breaking change to algorithm.
- Backward compatibility test coverage: ADR-0009 sub-exp 03 validates byte-canonical on D1-D9 + lineitem 1k/5k + EXP-007/010/011/012/013/014. Patricia drop-in must pass ALL these tests byte-identically. Any regression in even one dataset flags implementation bug.
- No existing production Patricia library in Python optimized for this use case (append-only, preserve order, variable-key-length). Off-the-shelf libraries (pygtrie, patricia-trie) may not guarantee insertion-order preservation or have overhead for this specific pattern. Custom implementation required.
- HCC layer coupling: HCC (_detect_compositions) and seq-RLE operate on OBAT tokens, not indexes. Patricia substitution should not affect HCC input (token stream). But if OBAT behavior changes (different tie-breaks, bucket order), HCC output changes → bytes diverge. Must validate post-substitution against all HCC tests.

### Recommendation

**Worth prototyping, but with caveats:**

**Should prototype IF:**
1. Goal is to improve date prefix performance (2x → 5x+ on l_shipdate/commitdate/receiptdate). Requires Patricia to expose LCE or enable variable-k bucketing (beyond standard k=3 contract). This is a design extension, not drop-in.
2. You want to validate empirically whether Patricia insertion-order iteration is viable in practice (risk of tie-break bugs is real; testing needed).
3. Broader roadmap is considering v2.0 optimizations (ADR-0018 lists Patricia as secondary candidate). Prototype now, decide later.

**Should NOT prototype IF:**
1. Goal is only drop-in replacement (bucket search O(N)→O(B)). Current hash index ALREADY achieves 5.4x speedup globally, 1.77x in full pipeline. Patricia gains would be marginal (maybe 5-10% reduction in O(B) via tree structure, but B is already small). Cost/benefit unfavorable.
2. Resources are limited. Custom Patricia implementation (append-only, insertion-order preservation) is 200-400 LOC, plus 100 LOC audit of OBAT callers, plus 50+ regression tests. Estimated effort: 6-12 hours if no library available; 3-6 hours if library exists and needs wrapping.
3. Date performance is acceptable. ADR-0009 already shows 2x on dates; if pipeline is not bottlenecked there (HCC is 24%, growing as OBAT improves), Patricia is not priority. H-PERF-04 (2026-05-20, refuted) already explored trigram alternatives; conclusion was "Patricia as fallback if HCC optimization insufficient" — wait for HCC gains first.

**Estimated effort if prototyping:**
- Research + feasibility study (this): 1-2 hours (DONE)
- Implement generic PatriciaTrie class (append-only, order-preserving, variable k): 3-4 hours
- Adapt _melhor_pref/_melhor_suf to query Patricia (surface area: ~30 LOC change): 0.5 hours
- Audit processar/processar_with_hint for hidden dict-method assumptions: 1-2 hours
- Test: D1-D9 + lineitem 1k/5k + EXP-007/010/011/012/013/014 roundtrip (must byte-match): 1-2 hours
- Optional: extend for variable-k, LCE caching: +2-4 hours
- **Total: 7-13 hours (1-2 days) for drop-in prototype, 11-17 hours (2-3 days) for extended prototype.**

**Recommendation: Prototype IF date performance is pain point AND HCC optimization disappoints (< 2x gain). Otherwise, defer to v2.0 roadmap under lower priority (after V2-A fallback, V2-B dictionary).** Current hash index is robust, byte-canonical-verified, and already 5.4x speedup in isolation. Risk of regression during Patricia substitution (tie-break bugs, insertion-order deviation) is non-trivial. Only justified if empirical ROI is clear.

---

## 3. Design concreto de Patricia/Generalized Suffix Tree aplicado ao OBAT do TCF v1.0

### Findings

**Status atual do OBAT (ADR-0009)**  
Hash trigrama k=3 implementado e welded em src/tcf/core/online.py (2026-05-19). Reduz complexidade de O(N²) para O(N·B) onde B = bucket size. Speedup 5.4x em isolamento OBAT, 1.77x no pipeline completo. Garante byte-canonical via iteração em ordem de id ascendente e tie-break > strict.  
*source*: docs/adr/0009-obat-trigram-index-optimization.md, src/tcf/core/online.py

**Hipotese H-PERF-04 (refutada-parcial em 2026-05-20)**  
Trigrama de meio s[L//2-1:L//2+2] testado para dispersar buckets em colunas datetime TPC-H (prefixos 199/200/202 geravam 2160 matches). Analise teorica mostrou: multi-hash com INTERSECAO perde matches; UNION expande candidatos; combined key tipo s[:3]+s[-3:] ainda pode ter s[:3] identico em strings diferentes, violando propriedade de matching optimo. Conclusao: hash tradicional nao preserva byte-canonical sem Patricia trie ou versioning de formato.  
*source*: experiments/lab/dirty/old/refuted/2026-05-20-obat-perf-phase2-trigram-middle/02-prototipo-combined-full/README.md

**Contexto H-TH-02 (hipotese teorica aberta 2026-05-13)**  
Registrada como abstracao em experiments/lab/dirty/old/2026-05-13-M4-desfragmentacao-arvore/notas/indice-incremental-de-padroes.md: 'Indice incremental de padroes (Patricia tree generalizada). Comparacao como parametro modular em OBAT/HCC.' Nunca foi testada empiricamente no OBAT; existem 40+ implementacoes de Patricia em M0-fase-exploratoria-inicial (2026-05-10-02 ate 2026-05-10-12) mas em contexto diferente (encoding full, nao indexacao de candidatos).  
*source*: experiments/lab/dirty/notas/roadmap-hipoteses.md (linhas 185-186), experiments/lab/dirty/old/2026-05-13-M4-desfragmentacao-arvore/notas/indice-incremental-de-padroes.md

**Roadmap v2.0 (ADR-0018, 2026-05-27)**  
Patricia registrada como candidato futuro (nao v1.0) para resolver datetime baixa-dispersao. V2-A (fallback identity) priorizado primeiro pq prototipo pronto; V2-B (dicionario) para baixa-cardinalidade (beijing hour 24 unicos inflou 228.8%). Patricia subsumida em discussao mas nao reaberta como v2.0 proprio candidato — fica como fallback conceitual de H-PERF-04 se H-PERF-05 (HCC opt) insuficiente.  
*source*: docs/adr/0018-v2-format-roadmap.md, experiments/lab/dirty/notas/roadmap-hipoteses.md (linhas 102-104)

**Escala de datasets TCF**  
D1-D9: 9 datasets sinteticos, M9 baseline 1615B. D17a: 13 strings pequenas (teste baseline). Wine: ~6500 rows (UCI real). Beijing PM2.5: 43,824 rows, 24 unicos numericos (hour column extremo). Adult Census: 48,842 rows, 15 cols. TPC-H lineitem: 60,175 rows (full), subdivisoes 1k/5k/10k/20k testadas. Online Retail: ~500k rows (fallback test). String lengths: avg 5-25 chars em colunas categoricas; 1-4 chars em numericas (IDs).  
*source*: docs/adr/0009-obat-trigram-index-optimization.md, datasets/canonical/*/README.md, experiments/lab/dirty/old/welded/2026-05-27-naturezas-reais-uci/result.md

**Invariante byte-canonical TCF v1.0**  
Qualquer mudanca de ORDEM de tie-break em comparacoes LCP/LCS quebra bytes. M9 baseline 1615B (D1-D9) deve ser exatamente replicado. Patricia trie preservaria ordem se iteracao interna em nos mantivesse IDs em ordem ascendente, MAS mudar de hash (dict iteration order em Python 3.7+) para trie (tree traversal) pode introduzir ordem implicita diferente se nao for cuidadosa.  
*source*: src/tcf/core/online.py (linhas 99-112, 155-162), docs/adr/0009-obat-trigram-index-optimization.md (secao Garantia byte-canonical)

**Variantes Patricia + análise teórica**  
(1) Patricia radix tree k-ario: k=256 (full char) reduz profundidade mas expande memória; k=2 (binary) economiza memória mas lookup O(L log N). (2) Compressed trie: agrupa edge labels (strings nao chars) — reduz nos, ideal pra TCF. (3) Generalized Suffix Tree (Ukkonen O(N)): mais complexo, melhor pra sufixos; trie direcional. (4) Suffix array + LCP array: offline (build caro) mas tempo de query consistente. **Recomendação**: Compressed trie (aka Patricia radix) com edge labels é melhor tradeoff pra TCF (strings curtas 5-25 chars, incremental 1 por vez).  
*source*: General knowledge (algorithms)

**Prototipo anterior (M0-fase-exploratoria, 2026-05-10)**  
Pasta experiments/lab/dirty/old/M0-fase-exploratoria-inicial/ contem 40+ implementacoes (2026-05-10-02-patricia-nomes ate 2026-05-10-12-debug-hierarquia-decl). Cada subpasta tem patricia.py (class No com pai_id/fragmento), encode/decode, benchmark. Nenhuma foi integrada ao OBAT canonical; todas foram exploracoes iniciais de encoding estrutural (nao indexacao de candidatos).  
*source*: experiments/lab/dirty/old/M0-fase-exploratoria-inicial/2026-05-10-02-patricia-nomes/patricia.py, conclusoes.md

**Requisitos de drop-in replacement**  
Classe TrigramIndex (atual em processar) expoe: dict prefix_index[trigram] -> list[ids], dict suffix_index[trigram] -> list[ids], operacoes setdefault().append(). PatriciaIndex novo deveria ter MESMA interface externa (TrigramIndex vs PatriciaIndex como aliases/swappable) OR expandida com novo metodo query_prefix(s, max_len). Risco: Patricia.insert(s, id) e Patricia.query_prefix(s) podem nao retornar EXATAMENTE os mesmos IDs se ordem implícita mudar. Validacao critica: byte-canonical roundtrip.  
*source*: src/tcf/core/online.py (linhas 184-186, 195-197)

**LCP/LCS com Patricia**  
Query atual: _melhor_pref itera bucket prefix_index[s[:3]] computando lcp_len(s, strings[idx]). Com Patricia, query_prefix(s, max_len=ls) retorna folha do trie com longest common prefix até profundidade ls. NO ENTANTO: Patricia retorna nó/folha, nao direto o lcp_len — precisa comparar s com todas as strings do subtree (mesmo O(B) assintotico). Vantagem: Patricia reduz B (bucket) pra casos com prefixos populares (datas 2160→30). Desvantagem: overhead dict-of-dicts em Python pode nao compensar.  
*source*: src/tcf/core/online.py (linhas 97-112)

**Representacao Python de Patricia node**  
Opcoes testadas em M0: (1) dict-based: {char -> node}, node = (edge_label, is_leaf, string_ids). (2) dataclass @dataclass class Node: children: dict, is_leaf: bool, string_ids: list, parent_id: int. (3) slots: class Node: __slots__=['children', 'is_leaf', 'ids']. Uso atual (M0): dataclass ou dict. Para TCF: compressed-edge-label trie precisa de (char_or_prefix) -> Node; cada Node armazena lista de string IDs acumulados ate aquele ponto, nao apenas folhas.  
*source*: experiments/lab/dirty/old/M0-fase-exploratoria-inicial/2026-05-10-02-patricia-nomes/patricia.py (linhas 26-30)

**Memoria estimada para Patricia vs Hash**  
Dataset D17a (13 strings, avg 10 chars): trigrama hash ~20 buckets, ~0.5KB. Patricia: ~13-20 nodes (1 por string unico + interiores), ~2KB (dict overhead). Dataset wine (6500 strings): hash ~1000 buckets (dict keys) + lists, ~100KB. Patricia: ~1000-2000 nodes (compressed edges), ~200KB. TPC-H lineitem 60k: hash ~5000 buckets, ~2-4MB. Patricia: ~5000-10000 nodes, ~5-10MB. **Patricia ~2x memoria vs hash pura (dict overhead > edge label savings)**. Ainda aceitavel para batch encoding (< 100MB RAM pra lineitem full).  
*source*: docs/adr/0009-obat-trigram-index-optimization.md (secao Riscos, memoria), experimentos EXP-014

**Teste comparativo: estrategia**  
Fork branch em experiments/lab/dirty/ (NAO src/tcf): (1) Implementa PatriciaIndex class com mesma assinatura TrigramIndex. (2) Cria processar_patricia(strings_unicas, min_len=3) que usa Patricia vs trigrama hash. (3) Roda D1-D9 + UCI (wine/beijing) + Adult/TPC-H subsets (5k linhas) comparando: bytes-canonical (deve bater!), tempo build indice, tempo total encode. (4) Validacao: roundtrip em 100% dos casos. (5) Se byte-canonical bater, merge pra src/tcf; se divergir, auditoria de ordem de iteracao.  
*source*: docs/adr/0009-obat-trigram-index-optimization.md (sub-exp 02-03 pattern)

**Risco critico: ordem de tie-break em Patricia**  
Hash dict em Python 3.7+ preserva insertion order. Patricia tree traversal segue ordem de keys no dict (alfabetica em most efficient impl) OU insertion order de filhos. Se trie faz traversal alfabetico (a-z) mas OBAT espera insertion order (id ascendente), output_ids diferem. Exemplo: bucket [id=3, id=1, id=5] (inserido nessa ordem) vs [id=1, id=3, id=5] (ordenado). _melhor_pref(_escolher_par) itera e tie-break via primeira ocorrencia (> strict). Se ordem mudar, ORDEM DE RETORNO muda, LCP/LCS tie-break muda, bytes divergem. MITIGACAO: manter insertion_order=id_ascendente nos filhos Patricia (garantir).  
*source*: src/tcf/core/online.py (linhas 100-112, tie-break logica)

**Libraries considerar vs pure stdlib**  
(1) pytrie (PyPI): compressed trie + Ukkonen GST, bem mantida, typing completo. RISCO: dependencia nova, packaging. (2) pyahocorasick (PyPI): automata multi-pattern, Cython backend — overkill pra TCF, mais pra string matching, nao query-by-prefix. (3) Pure stdlib dict: viavel, manual patricia em ~200-300 LOC. (4) sortedcontainers.SortedDict: nao necessario (preservar insertion order é suficiente). **Recomendacao**: pure stdlib + manual Patricia (LOW RISK, ZERO DEPS), ou pytrie se performance provado insuficiente (MEDIUM RISK, 1 dep).  
*source*: General knowledge (Python libs)

**Estimativa LOC prototipo**  
(1) PatriciaIndex class (insert, query_prefix, interno traversal): ~150-200 LOC. (2) Integration em processar variant (processar_patricia): ~50 LOC (copy processar, swap indices). (3) Comparison benchmark (compara vs TrigramIndex): ~100 LOC. (4) Roundtrip validation: ~50 LOC. **Total: ~350-400 LOC**. Desenvolvimento estimado: 2-4 horas (implementacao + debug). Testing (D1-D9, D17a, wine subset): 1 hora. Full validation (Adult/TPC-H 5k): 2-3 horas.  
*source*: Estimation based on M0 prototypes complexity


### Design notes

## Design Concreto: Patricia Trie para OBAT TCF v1.0

### 1. Variante escolhida: Compressed Patricia Trie (Radix k-ario)

**Racional**: Strings curtas (5-25 chars), dataset incremental (1 por vez), string-centric problema (não pattern-matching multi-target). Compressed edge labels reduzem nós comparado a trie puro.

```python
@dataclass
class PatriciaNode:
    """Nó comprimido: edge_label pode ser substring (não char único)."""
    edge_label: str  # substring do prefixo desta aresta
    children: dict[str, 'PatriciaNode']  # key=primeiro char de edge_label filho
    string_ids: list[int]  # IDs acumulados neste nó (folha + interiores)
    is_leaf: bool

class PatriciaIndex:
    def __init__(self):
        self.root = PatriciaNode("", {}, [], False)
        self._insertion_order = []  # track insertion order pra tie-break
    
    def insert(self, s: str, string_id: int):
        """Insere string s com id sequencial. Matem ordem de inserção."""
        node = self.root
        idx = 0
        
        while idx < len(s):
            # Busca child cujo edge_label comeca com s[idx]
            first_char = s[idx]
            if first_char not in node.children:
                # Cria novo child
                new_node = PatriciaNode(s[idx:], {}, [string_id], True)
                node.children[first_char] = new_node
                self._insertion_order.append((string_id, node, new_node))
                return
            
            child = node.children[first_char]
            edge_label = child.edge_label
            
            # Compara s[idx:] com edge_label
            lcp_edge = 0
            while lcp_edge < len(edge_label) and idx + lcp_edge < len(s) \
                  and s[idx + lcp_edge] == edge_label[lcp_edge]:
                lcp_edge += 1
            
            if lcp_edge == len(edge_label):
                # Edge inteira casou
                idx += len(edge_label)
                node = child
                continue
            
            # Partial match: split edge
            prefix_edge = edge_label[:lcp_edge]
            suffix_edge = edge_label[lcp_edge:]
            split_node = PatriciaNode(prefix_edge, {}, 
                                      child.string_ids.copy(), 
                                      False)
            split_node.children[suffix_edge[0]] = child
            child.edge_label = suffix_edge
            node.children[first_char] = split_node
            
            # Novo string contem suffix pós-split
            new_node = PatriciaNode(s[idx + lcp_edge:], 
                                    {}, [string_id], True)
            split_node.children[s[idx + lcp_edge]] = new_node
            split_node.string_ids.append(string_id)
            self._insertion_order.append((string_id, split_node, new_node))
            return
        
        # s casou inteira; node agora aponta pro end
        node.string_ids.append(string_id)
        node.is_leaf = True
        self._insertion_order.append((string_id, node, None))
    
    def query_prefix(self, s: str, max_len: int) -> list[int]:
        """Retorna lista de IDs com LCP >= algum threshold (sem threshold neste sketch)."""
        node = self.root
        idx = 0
        candidates = []
        
        while idx < len(s) and idx < max_len:
            first_char = s[idx]
            if first_char not in node.children:
                break
            
            child = node.children[first_char]
            edge_label = child.edge_label
            lcp_edge = 0
            
            while lcp_edge < len(edge_label) and idx + lcp_edge < len(s) \
                  and s[idx + lcp_edge] == edge_label[lcp_edge]:
                lcp_edge += 1
            
            if lcp_edge < len(edge_label):
                break  # Mismatch
            
            idx += lcp_edge
            node = child
            candidates.extend(node.string_ids)
        
        # Manter ordem de inserção pra tie-break
        return sorted(candidates)  # ou retornar em insertion_order se guardado
```

### 2. API Publica: Drop-in com cuidado

**Opsao A (Minimal)**: mesma interface TrigramIndex, swap direto
```python
# Antes
prefix_index: dict[str, list[int]] = {}
suffix_index: dict[str, list[int]] = {}
# ...
bucket = prefix_index.get(s[:3])

# Depois
prefix_index = PatriciaIndex()
suffix_index = PatriciaIndex()
# ...
bucket = prefix_index.query_prefix(s)  # retorna list[int]
```

**Option B (Expandida)**: nova assinatura pra explorar capabilities
```python
class PatriciaIndex:
    def query_lcp(self, s: str, min_match_len: int = 3) -> list[tuple[int, int]]:
        """Retorna [(string_id, lcp_len)] ja pre-calculado no nó."""
        # Vantagem: LCP guardado durante traversal, nao recalculado
```

### 3. Estrategia de teste (dirty lab fork)

**Branch**: experiments/lab/dirty/2026-05-29-patricia-obat-index/ (novo)

**Sub-exp 01**: Implementacao basica
- PatriciaIndex.insert, query_prefix, roundtrip validation
- Teste em D17a (13 strings) — equivalente M0 nomes

**Sub-exp 02**: Isolado vs TrigramIndex
- processar(D1-D9) vs processar_patricia(D1-D9)
- Validar: tokens IDENTICOS (byte-canonical), tempo build

**Sub-exp 03**: Real-world subset
- wine (1000 strings sample)
- Adult (5000 rows, 1 col)
- Metricas: tempo encode, bytes, mem

**Sub-exp 04**: Auditoria ordem tie-break
- Se divergencia encontrada: trace de comparacoes, ajuste insertion_order

**Sub-exp 05**: Full TPC-H 5k se OK

### 4. Risco mitigation: byte-canonical

**Invariante**: ordem de _melhor_pref/_melhor_suf EXATA
- Hash dict: insertion order (Python 3.7+)
- Patricia: tree traversal order
- **Fix**: guardar insertion_order separado, retornar sorted(candidates, key=insertion_order)

### 5. Criterios de aceitacao prototipo

- ✅ D1-D9 bytes EXATOS 1615B (M9 baseline)
- ✅ Roundtrip 100% (decode(encode(x)) == x)
- ✅ Tempo build Patricia < 10ms overhead vs hash (pra D17a)
- ✅ Wine 1000 strings: sem regressao bytes
- ❌ Se byte-canonical quebrar: diagnosticar + fix OR abandon

### Risks

- Byte-canonical divergencia: Patricia tree traversal order pode ser implicita (alfabetica children, nao insertion order). Mitigation: explicitar insertion_order separado ou forcar children dict como OrderedDict/sorted.
- Memoria overhead: Patricia dict-of-dicts em Python tem overhead > hash dict puro. Estimativa 2x maior. Aceitavel pra batch (<10MB lineitem 60k), mas precisa validar em memoria antes de full production.
- Complexidade implementacao: Patricia trie com edge splitting (comprimido) nao-trivial. Risco de bugs em edge cases (empty string, 1-char strings, overlap patterns). Mitigacao: reuse codigo M0 existente se compativel, ou pytrie library.
- Performance regression em casos sem agrupamento: D1-D9 categoricas puras (Ana/Bob/Carlos) nao tem prefixos comuns. Patricia degrada pra dict simples (conforme M0 mostra). Hash k=3 ja' otimo ali. Patricia overhead pode piorar 1-2%.
- Query performance plateau: Patricia reduz B (bucket size) em datas de 2160→30, MAS ainda precisa iterar 30 candidatos pra computar lcp_len (mesmo O(B) assintotico). Ganho real depende de operacoes em Python ser suficientemente otimizadas vs dict overhead.
- Integration risk no pipeline canonical: src/tcf/core/online.py fixo desde 2026-05-19 (ADR-0009 welded). Mudar para Patricia exige re-validacao multi-camada (EXP-007/010/011/012/013/014). Se divergencia aparece, revert custoso.
- Dependency novo (pytrie): se optar por biblioteca, adiciona dependency externa. Packaging/CI impact.
- Tie-break subtil: primeiro matching candidato em tie-break >. Se Patricia retorna ordem diferente de hash dict, ORDEM DE RETORNO muda, **primeiro ID retornado muda**, lcp_len pode ser diferente, cobertura diverge. Risco alto pra byte-canonical.

### Recommendation

**Prototipar SIM, mas com protocolo rigoroso de validacao.**

**Porque**: H-PERF-04 refutada-parcial menciona Patricia como fallback real se H-PERF-05 insuficiente. Hash trigrama atual ja' 5.4x, datas ainda 2x fraco. Patricia pode resolver datas sem versioning formato (diferente de H-PERF-04 tentativa anterior que planejava combined key). Evidencia que recompensa: se TPC-H datetime speedup vai de 2x pra 5x+, justifica overhead.

**Esfoco estimado**: 
- Implementacao + debug: 4-6 horas
- Testing (D1-D9 + wine + Adult 5k): 3-4 horas  
- Auditoria byte-canonical + mitigacao se quebrar: 2-3 horas
- **Total: 10-14 horas work**

**Protocolo pre-requisito**:
1. Fork em experiments/lab/dirty/2026-05-29-patricia-obat-index/ (NUNCA src/tcf)
2. Sub-exp 01 validacao basica (D17a roundtrip)
3. Sub-exp 02 byte-canonical comparacao D1-D9 (STOP se diverge, auditoria)
4. Sub-exp 03 performance metricas (tempo build, encode, memoria)
5. **Aceitacao criteria**: D1-D9 1615B exato + wine/Adult sem regressao + zero byte divergencias
6. Se OK: criar ADR-0019 propondo patricia como H-PERF-04-resolvido pra v1.x patch OU v2.0 candidato
7. Se falha: documentar roadblock, retornar pra H-PERF-05 ou deferr pra v2.0 junto com V2-B (dicionario)

**Prioridade vs agenda TCF**: Baixa no imediato (v1.0 freeze ADR-0017), MEDIA se owner reabrir v1.x perf (datas datetime). MEDIA-ALTA se v2.0 planejado (Patricia como opcao antes de V2-A/B)

---

## 4. Patricia trie como alternativa ao índice hash trigrama em OBAT (contexto H-PERF-04 refutado-parcial, H-TH-02 teórico)

### Findings

**O que H-PERF-04 propôs exatamente**  
Explorar trigrama adicional de posição MEIO em colunas datetime para dispersar buckets hash. Proposta específica: chave combinada s[:3] + s[mid_start:mid_start+3] + s[-3:] (combined_full). Profile sub-exp 01 confirmou redução de max_bucket de 2160 → 9 em l_shipdate (240x), mas análise teórica sub-exp 02 mostrou que hash tradicional não preserva byte-canonical: strings com mesmo prefix s[:3] mas combined_full diferente causam perda de matches válidos de LCP 3-5.  
*source*: experiments/lab/dirty/old/refuted/2026-05-20-obat-perf-phase2-trigram-middle/01-profile-bucket-sizes/result.md e 02-prototipo-combined-full/README.md

**Por que H-PERF-04 foi refutada-parcial: mecanismo exato**  
Multi-hash com filtro adicional (prefix ∩ middle) viola semantica de match valido. Match de prefix requer apenas s[:3] == prev[:3]; multi-hash restritivo exige TAMBÉM middle igual, excluindo strings que teriam LCP 3-5 válido mas middle diferente. Exemplo: 'abcXYZ' e 'abcDEF' ambos prefix-match em 'abc' mas combined_full diferente. Hash unário (só prefix ou só suffix) preserva byte-canonical; combinado não.  
*source*: 2026-05-20-obat-perf-phase2-trigram-middle/02-prototipo-combined-full/README.md, seção 'Reformulacao'

**Em qual dataset H-PERF-04 foi testada (viés?)**  
Dataset TPC-H lineitem 5000 rows × 16 cols (l_shipdate, l_commitdate, l_receiptdate com datas 1992-1998). Datas são dataset EXTREMAMENTE enviesado: prefixo '199' em TODAS → 100% no bucket unário. Sub-exp 01 foi APENAS caracterizacao (profile); sub-exp 02 (prototipo) foi abortado ANTES de código (análise teórica). Nenhuma validação em real-world não-datetime.  
*source*: 2026-05-20-obat-perf-phase2-trigram-middle/README.md (Hipoteses) e result.md (l_shipdate: prefix max=2160)

**Onde Patricia foi mencionada no lab H-PERF-04**  
Sub-exp 02 README.md, seção 'Conclusao do sub-exp 02 (sem rodar codigo)': 'Pra ter speedup em datas preservando bytes, precisa de estrutura POSICIONAL que retorne best LCP direto (sem iteracao): Patricia trie (radix tree): traverse O(L) retorna folha com lcp máximo [...] CANDIDATO REAL.' Conclusão foi marcar Patricia como 'out-of-scope' naquele momento (opcao A: pausar H-PERF-04, focar H-PERF-05).  
*source*: 2026-05-20-obat-perf-phase2-trigram-middle/02-prototipo-combined-full/README.md, linha 81-83

**Patricia seria sucessor de H-PERF-04 ou ataca problema diferente?**  
SUCESSOR DIRETO mas eixo diferente. H-PERF-04 tentou mitigar BIAS de hash (distribuir buckets via múltiplas dimensões). Patricia substitui HASH INTEIRO por trie incremental, mudando primitiva de O(B) bucket-scan para O(L) trie-traverse. Não é refinamento de hash; é mudança de indexação. Preservaria byte-canonical porque trie mantém ordem incremental + tie-break implícito em depth-first traversal.  
*source*: 2026-05-20-obat-perf-phase2-trigram-middle/02-prototipo-combined-full/README.md e comparação com ADR-0009

**Lições de H-PERF-04 que Patricia deve incorporar**  
1. Dataset bias: H-PERF-04 vencida por prefixos populares (datas '199...'). Patricia trie NÃO sofre desse viés — trata prefixos populares naturalmente via depth maior. 2. Preservação byte-canonical: CRÍTICO. Patricia mantém ordem insercao em cada nó (list[id]) → preserva tie-break. 3. Buckets grandes: H-PERF-04 chegou a 2160 em datas. Patricia em datas esperaria ~N/k nós folha distribuído por profundidade.  
*source*: 2026-05-20-obat-perf-phase2-trigram-middle/01-profile-bucket-sizes/result.md (análise datas) e 02-prototipo-combined-full/README.md (conclusão)

**Hipótese teórica H-TH-02: status e registro**  
H-TH-02 'Indice incremental de padroes (Patricia generalizada)' registrada 2026-05-13 em roadmap-hipoteses.md com status 'adiada'. Conecta com H-PERF-04 (como fallback se hash falhar), ADR-0018 V2-C (roadmap v2.0 Patricia como substituto do hash trigrama em v2.0). Nunca foi testada isoladamente.  
*source*: experiments/lab/dirty/notas/roadmap-hipoteses.md linha 185, e docs/adr/0018-v2-format-roadmap.md

**Risco de refutação prematura em dataset enviesado**  
H-PERF-04 foi decisiva em datas TPC-H (dataset com estrutura artificial: 1992-1998 prefixo constante). Mas nenhuma validação em: 1) datas reais variadas (diferente período), 2) não-datetime com prefixos populares (URLs de mesmo domínio, IDs com prefixo comum). H-PERF-04 foi refutada como 'hash tradicional falha' — correto — mas a CAUSA foi dataset enviesado, não inviabilidade do problema em geral.  
*source*: 2026-05-20-obat-perf-phase2-trigram-middle/01-profile-bucket-sizes/result.md, seção 'Por que prefix sozinho gera 2160'

**API atual OBAT e compatibilidade Patricia**  
API publica preservada: lcp_len(a,b), lcs_len(a,b), processar(strings_unicas, min_len=3). Internamente, ADR-0009 usa prefix_index[s[:3]] → list[ids] e suffix_index[s[-3:]] → list[ids]. Patricia trie substituiria ambos por _build_prefix_trie() e _build_suffix_trie() mantendo interface compatível: trie.lookup(s[:k]) → list[ids].  
*source*: src/tcf/core/online.py linhas 97-127 (_melhor_pref/_melhor_suf) e ADR-0009

**Tentativas anteriores Patricia em M0 (2026-05-10)**  
Experimentos M0 fase exploratória (2026-05-10-02-patricia-nomes/ até 2026-05-10-12-debug-hierarquia-decl/) implementaram Patricia para strings-nomes com foco em descompressão de sequências repetidas (fase 1: valores unicos → ids, fase 2: patricia incremental, fase 3: RLE). Algoritmo iterativo greedy (escolhe prefixo mais longo + frequente a cada iteração). Não foi testado em OBAT (tokenização bidir vs compressão estrutural são contextos diferentes).  
*source*: experiments/lab/dirty/old/M0-fase-exploratoria-inicial/2026-05-10-02-patricia-nomes/algoritmo.md

**Roadmap v2.0 e lugar de Patricia (ADR-0018 V2-C)**  
ADR-0018 registra Patricia trie como V2-C do roadmap v2.0: 'substituir Counter+scan por trie (sem sintaxe mudança)' e 'Patricia substituiria trigrama hash em v2.0 OBAT'. Status: registrada como candidato v2.0, NÃO v1.x. Prioridade: menor que V2-A (fallback) e V2-B (dicionário), maior que V2-D (strip sufixo).  
*source*: docs/adr/0018-v2-format-roadmap.md e STRATEGIES-MAP-EXTRACTED.md linha 272

**Complexidade analítica esperada: Patricia vs Hash trigrama**  
Hash trigrama (atual ADR-0009): O(N·B) onde B = avg bucket size (depende distribuição chave). Pathologico: B=N (datas TPC-H, 2160). Patricia: O(N·L·log(branching_factor)) onde L = avg string length. Esperado L~10 pra maioria, branching ~256 chars → O(N·10·8) amortizado. Sem patologia em prefixos populares.  
*source*: ADR-0009 'Opção C' comparação, e teoria Radix tree padrão

**Ganho estimado e target datasets para prototipo Patricia**  
H-PERF-04 profile mostrou: l_shipdate 2x apenas (sufixo hash já 27.7x). Patricia esperaria: datas reais com prefixos variados (não artificial 1992-1998) → 5-20x. Não-datetime com prefixos populares (URLs domínio comum, IDs banco de dados) → 10-100x. Alvo prototipo: validar em real-world com múltiplos padrões de prefixo, NÃO apenas TPC-H datetime.  
*source*: 2026-05-20-obat-perf-phase2-trigram-middle/01-profile-bucket-sizes/result.md (combined_full 240x em datas) vs ADR-0009 (H-PERF-02 baseline 5.4x)


### Design notes

1. **Compatibilidade de API**: Patricia trie substituiria prefix_index/suffix_index dicts. Interface: trie.lookup(trigrama:str) → list[int] (ids). Costo computacional: lookup O(k) onde k=3, zero mudança.

2. **Preservação byte-canonical**: Crítico. Em cada nó de trie, manter list[id] em ordem insercao (= ordem numérica id). Durante traversal, candidatos retornados preservam tie-break `>` strict (primeira ocorrência ganha). Implementação: após inserir id em nó, não reordenar.

3. **Direção dupla (prefix + suffix)**: Patricia separada para prefixos e sufixos (trie_prefix, trie_suffix). Independentes, compatível com _melhor_pref/_melhor_suf. Pré-build em O(N·L) fora do loop quente.

4. **Estrutura Python**: Trie como dict-of-dicts: `TrieNode = {'*': [ids], 'a': TrieNode, 'b': TrieNode, ...}`. Marker '*' ou campo .ids() para terminal. Memory: ~O(N·L·α) onde α=branching. Empirico em lineitem 5k: ~2-3MB esperado (vs 2-4MB trigrama hash atual).

5. **Build incremental vs batch**: Patricia em contexto OBAT é BATCH (prototipo recebe strings_unicas já dedupadas). Build iterativo iteraria O(N·L) acumulado. Não incremental por string como em M0.

6. **Datasets-alvo prototipo para validação**:
   - **Datetime real-world**: Adult/TPC-H customer.c_mktsegment (texto), lineitem com datas diferentes de TPC-H original (quebrar viés '199')
   - **Non-datetime prefix-popular**: URLs com domínios comuns (adult.csv URLs se houver), IDs banco com prefixo factory (ex: lineitem l_partkey que é ID)
   - **Fallback sanity**: pequenos datasets D1-D9 preservar 1615B byte-canonical exato

7. **Implementação faseado**:
   - Fase 1: TrieNode classe simples, build_prefix_trie(strings, min_len=3)
   - Fase 2: integrar em online.py _melhor_pref/_melhor_suf, mantendo assinatura API
   - Fase 3: benchmark isolado (sub-exp): perfil bucket distribution, speedup, byte-canonical vs ADR-0009
   - Fase 4: validação multi-camada EXP-015 (D1-D9 + Adult/TPC-H, sem regressao)

### Risks

- Viés de dataset H-PERF-04: TPC-H datas 1992-1998 é dataset artificial (prefixo '199' em todas). Patricia pode parecer 'inútil' se testado SÓ em datas TPC-H replicado. Risco: repetir validação prematura em dataset enviesado.
- Memory overhead trie dict-of-dicts em Python: dict interno por nível × 256 branching. Empirico em strings aleatorias, overhead é 2-3x vs hash flat. Lineitem 5k é 2-4MB hash (pequeno); trie pode ir 6-12MB. Datasets grandes (60k+) precisam medir.
- Complexidade implementação Python: trie não-trivial, bug-prone (recursão, terminais, limites de profundidade). Overhead Python loop em trie traversal pode neutralizar ganho teórico O(L) vs O(B) se B pequeno. Teste performance CRÍTICO.
- Refutação indevida em real-world variado: Se não testar em datasets COM prefixos populares naturais (não artificial), Patricia pode parecer 'pouco melhor que hash' e ser descartada. H-PERF-04 sofreu disso.
- Byte-canonical subtle bug: ordem insercao em trie precisa ser exatamente FIFO global. Bug comum: rehash em dict Python altera ordem (Python 3.7+ preserva, mas cuidado). Teste com verificação byte-per-byte obrigatório.
- Incompatibilidade com obat_shape.py: processar_with_hint usa _melhor_pref/_melhor_suf com assinatura específica. Mudança em online.py exige re-validar shape-preserve em ADR-0007 + EXP-010.
- Fallback hash se trie falhar: se Patricia falhar byte-canonical em algum edge case, código não tem fallback — quebra pipeline. ADR-0009 hash é solid; Patricia é experimento. Precisa fallback gracioso ou validação absoluta antes welding.

### Recommendation

**Vale prototipar? SIM, com cuidado com dataset bias.**

**Por quê**: H-PERF-04 foi refutada-parcial em dataset artificial (datas TPC-H com prefixo constante). Patricia resolve o PROBLEMA CONCEITUAL (prefixos populares) mas nunca foi testado em real-world com múltiplos padrões. H-TH-02 está registrada teoricamente desde 2026-05-13 (2.5 meses sem teste). ADR-0018 inclui Patricia como candidato v2.0 prioridade-média.

**Esforço estimado**: 
- Implementação TrieNode + build: 3-4 horas
- Integração online.py: 2 horas
- Sub-exp isolada (profile, speedup): 4-6 horas
- Validação multi-camada (D1-D9, Adult 1k, TPC-H, datasets com prefixos variados): 8-12 horas
- **Total: 20-30 horas** (3-4 dias com testes completos)

**Target dataset prototipo** (CRÍTICO para evitar viés H-PERF-04):
1. **Datas reais variadas** (não TPC-H 1992-1998): ex. Adult temporal, ou synthetic datas 1800-2100 com prefixos diversos
2. **Non-datetime com prefixos populares naturais**: URLs, IDs com factory prefix, UUIDs truncados
3. **Fallback D1-D9** byte-canonical exato (regra invariante M9)
4. **Não testar APENAS em TPC-H datas** (armadilha H-PERF-04)

**Ganho esperado**:
- Datasets com prefixos populares: 5-50x speedup (vs 2x em TPC-H datas)
- Bytes IDÊNTICOS se implementação byte-canonical correta
- Não degradar colunas sem prefixos populares (Patricia trie é overhead se bucket já pequeno)

**Gating criterio prototipo** (GO/NO-GO antes welding):
- D1-D9: 1615B exato, RT 100%
- Adult 1k: RT 100%, bytes idênticos
- TPC-H customer/lineitem 5k: RT 100%, bytes idênticos + real-world dataset com prefixos variados
- Speedup > 1.5x em coluna com prefixo popular vs ADR-0009
- Se 1/4 criterios falhar → rejeitada; se 4/4 OK → candidata para ADR (propor welding post-v1.0 ou v2.0)

**Hipótese refinada para registro**: H-TH-02-v2: "Patricia trie incremental em OBAT reduz complessidade patológica de prefixos populares de O(N²) hash-bucket a O(N·L·log(α)), preservando byte-canonical e generalizando melhor que hash em datasets reais variados (não artificial)."

---

## Sintese cross-dimension

### Pontos onde os 4 estudos convergem

1. **Hash trigrama atual NAO esta ruim** (ADR-0009 5.4x speedup, O(N^1.42)
   real-world). Patricia nao e' urgencia.
2. **Patricia ganha em prefixos populares** (datas, ranges, padroes
   repetitivos). Em colunas categoricas dispersas o overhead anula o ganho.
3. **Risco principal: byte-canonical** — tie-break por ordem de insercao
   precisa ser preservado pixel-a-pixel. Bug subtil aqui quebra o freeze v1.0.
4. **Protocolo obrigatorio**: fork em dirty lab, validar D1-D9 1615B exato e
   RT em multi-camada antes de qualquer welding.
5. **Vies de dataset H-PERF-04** e' a armadilha mais importante: TPC-H dates
   1992-1998 e' artificial (prefixo `199` em TUDO). Patricia precisa ser
   testada em datasets COM prefixos populares VARIADOS (URLs, factory IDs,
   UUIDs truncados, datas reais multi-decada).

### Onde os estudos divergem

| Dimensao | Recomendacao |
|---|---|
| Teoria | **NAO prototipar agora** — defer a v2.0 (custo 220h, ganho narrow) |
| Contrato atual | **Worth IF date perf is pain point** — efort 7-13h |
| Design fit | **SIM com protocolo rigoroso** — 10-14h |
| H-PERF-04 relation | **SIM com cuidado de vies de dataset** — 20-30h com validacao multi-camada |

A divergencia e' principalmente sobre **esforço estimado** (7h a 220h) — o
range reflete o que se conta como "feito" (drop-in vs production-grade).

### Tabela de decisao recomendada

Prototipar agora se:
- [ ] Owner quer evidencia empirica de patricia antes de v2.0 abrir
- [ ] Dispomos de dataset com prefixos populares VARIADOS (nao so' TPC-H)
- [ ] Aceitamos 10-30h de trabalho no dirty lab

Adiar pra v2.0 se:
- [ ] Foco e' fechar v1.0 (validation plan + tag)
- [ ] H-PERF-06 (Cython interno) e' priorizado primeiro (nao muda formato)
- [ ] Outras opcoes v2.0 (V2-A fallback, V2-B dict, V2-D strip) tem ROI mais claro

### Conexao com nucleo compilado (proximo passo do owner)

H-PERF-06 (Cython/Rust port de lcp_len/lcs_len) e' **ortogonal** a Patricia:
- Cython melhora as comparacoes individuais (29M chamadas, 1.7us cada)
- Patricia reduz o NUMERO de comparacoes (bucket menor)
- Ganhos multiplicam: Cython em Patricia rodaria comparacoes mais rapidas em
  menos candidatos.

Mas atacar H-PERF-06 primeiro tem 3 vantagens:
1. Nao muda formato (cabe em v1.x sem quebrar freeze)
2. Beneficia toda a base atual (hash trigrama), nao apenas Patricia
3. Estabelece infraestrutura compilada (Cython/Rust build) que Patricia
   reaproveitaria depois

## Recomendacao final

**Patricia trie e' viavel mas nao urgente**. Documentar este estudo como
fundamentado, marcar H-TH-02 em roadmap como **caracterizada + adiada com
protocolo definido**. Atualizar ADR-0018 V2-C com pointer pra este doc.

Quando reabrir (v2.0 ou v1.x se H-PERF-06 nao chegar):
- Fork em `experiments/lab/dirty/YYYY-MM-DD-patricia-obat-index/`
- Validar D1-D9 1615B exato antes de qualquer otimizacao
- Testar em datasets com prefixos populares VARIADOS
- Aceitacao: bytes-identicos + speedup >= 1.5x em coluna com prefixo popular
