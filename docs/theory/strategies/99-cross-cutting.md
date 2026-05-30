---
title: Tabelas cruzadas (knobs, extension points)
type: reference
parent: strategies-map
---

## Tabelas cruzadas (cross-cutting)

### Todos os knobs/parametros tunaveis

| Subsistema | Knob |
|---|---|
| CAMADA 0 | detect_cadence_from_features.n_sample = 5 (tamanho amostra regra 1) |
| CAMADA 0 | detect_cadence_from_features.threshold = 0.7 (limiar LCP+LCS/L regra 1) |
| CAMADA 0 | detect_cadence_from_features.numeric_card_threshold = 0.5 (limiar card regra 2, ADR-0008) |
| CAMADA 0 | analyze_column.sample_size = 20 (amostra pra check is_numeric) |
| CAMADA 0 | detect_min_len_from_features.n_threshold = 100 (gating por n_rows) |
| CAMADA 0 | detect_min_len decision tree implicit thresholds: card<0.2, card>=0.2, card>=0.4, card>=0.7, card>=0.8, avg_len∈{3,5,8,12,25} |
| CAMADA 0 | PipelineConfig.pre_pass = True (default, ativa/desativa CAMADA 0) |
| CAMADA 0 | PipelineConfig.obat_shape_preserve = True (default, ativa hint em OBAT se cadence) |
| CAMADA 0 | PipelineConfig.hcc_seq_rle = True (default, M10 vs M9 variant) |
| CAMADA 0 | _lcp_len / _lcs_len implementacao: scan caractere-por-caractere fixo (nao parametrizado) |
| CAMADA 0 | _try_preserve_shape fallback hierarchy: exato → wider → greedy (deterministica, nao parametrizada) |
| CAMADA 1 | min_len: {2, 3, 4, 5, 6}; default=3 (M9), auto-detect via H-DA-11 (ADR-0010) yields 3-6 per column |
| CAMADA 1 | trigram key length k: hardcoded=3 (matches min_len default, ADR-0009) |
| CAMADA 1 | n_threshold for auto-min_len gating: default=100 (ADR-0010); datasets n<100 use min_len=3 |
| CAMADA 1 | cardinality threshold (low): default=0.2 (ADR-0010, H-DA-11 decision tree); card < 0.2 -> min_len=3 |
| CAMADA 1 | avg_len buckets (H-DA-11): {25, 8, 5, 12, 3} with card thresholds (ADR-0010 line 58-67) |
| CAMADA 1 | cadence threshold (H-DA-08): default=0.7 for LCP+LCS ratio (auto_cadence.py:32) |
| CAMADA 1 | cadence n_sample: default=5 (first 5 strings checked for uniform length + LCP-LCS) |
| CAMADA 1 | numeric_card_threshold (cadence rule 2): default=0.5 (auto_cadence.py:33) |
| CAMADA 1 | cfg.pre_pass: bool, default=True (PipelineConfig:54); False disables detect_cadence + detect_min_len |
| CAMADA 1 | cfg.obat_shape_preserve: bool, default=True; False skips processar_with_hint hint even if cadence detected |
| CAMADA 1 | cfg.hcc_seq_rle: bool, default=True; False reverts to M9 (no seq-RLE) |
| CAMADA 1 | Pipeline toggles all boolean (Fase 1), no numeric tuning exposed |
| HCC (Hierarchical Compositiona | atom_count = proximo_idx - 1 (final atom count pós-Fase A) |
| HCC (Hierarchical Compositiona | comp_acc_k (composição IDs acumulados, incrementa len(sub)-1 per alias) |
| HCC (Hierarchical Compositiona | next_alias (temp ID sequencial, inicia 1) |
| HCC (Hierarchical Compositiona | max_iterations = 99 (detector Fase B limit) |
| HCC (Hierarchical Compositiona | min_R = 2 (mínimo ocorrências) |
| HCC (Hierarchical Compositiona | min_K_range = 3 (range threshold) |
| HCC (Hierarchical Compositiona | virtual_count <= 1 (máximo 1 por sub) |
| HCC (Hierarchical Compositiona | n_est = len(str(atom_count+comp_acc_k+1)) (num width estimator) |
| HCC (Hierarchical Compositiona | virtual_estimate = '9'*n_est (pessimista baseline) |
| HCC (Hierarchical Compositiona | escape_chars = {*, \, ~, 0-9} |
| HCC (Hierarchical Compositiona | separator_char = * |
| HCC (Hierarchical Compositiona | range_separator = .. |
| HCC (Hierarchical Compositiona | ref_concat_ephemeral = , |
| HCC (Hierarchical Compositiona | ref_concat_compositional = ~ |
| HCC (Hierarchical Compositiona | rle_marker_syntax = *N|resto |
| HCC (Hierarchical Compositiona | seq_rle_syntax = *N+delta|template (ADR-0016) |
| HCC (Hierarchical Compositiona | max_seq_rle_nonzero = 1 (Fase 1 limit) |
| HCC (Hierarchical Compositiona | utf8_encoding = true |
| HCC (Hierarchical Compositiona | lf_only_canonical = true |
| CAMADA 2b | Fase 1 single non-zero restriction: compare_for_seq linha 110 hard-rejects multiple different non-zero. Futuro: Fase 2 removeria essa linha, permitindo [1,2,3] etc. |
| CAMADA 2b | Overflow width handling: shift_escape_digits linha 142 zfill(width) — se new_val > width, não trunca. Config futuro: truncate_overflow flag (atualmente sempre preserve). |
| CAMADA 2b | Run equality check (structural): compare_for_seq linha 90 requer runs_a == runs_b exatamente. Futuro: relaxar pra 'estruturalmente compatível' (ex: runs adicionales com zero offset). |
| CAMADA 2b | M10 marker format decision: _is_uniform_delta linha 181 threshold 'all(d == deltas[0] and d != 0)'. Knob: se mudar pra all(d == deltas[0]) (aceitar uniform-zero), quebraria backward compat. |
| CAMADA 2b | Escape sequence detector: find_escape_digit_runs detecta '\ seguido de isdigit(). Hardcoded: não detecta hex (\\xFF) ou octal (\\123). Futuro: extensivel pra outros bases. |
| CAMADA 2b | Marker savings estimate: compact_body linha 219 = sum(original line lengths) - len(marker). Não inclui header/footer overhead de markers. Config: tunable multiplier pra prefer/avoid compaction (atualmente 1x). |
| CAMADA 0-pre (Naturezas | MARKER_LITERAL = '_' (prefixo escape fallback) — linha 38 templated_checked.py |
| CAMADA 0-pre (Naturezas | BASE94 alfabeto size = 80 chars (94-14-1, assert>=50) — linhas 32-36 templated_checked.py |
| CAMADA 0-pre (Naturezas | SPEC_CPF.body_length = 9 (CPF body dígitos) — linha 157 |
| CAMADA 0-pre (Naturezas | SPEC_CPF.check_length = 2 (CPF check digits) — linha 158 |
| CAMADA 0-pre (Naturezas | SPEC_CPF.encoded_length = 5 (80^5 > 10^9, capacity check) — linha 161 |
| CAMADA 0-pre (Naturezas | SPEC_CNPJ.body_length = 12 (CNPJ body dígitos) — linha 194 |
| CAMADA 0-pre (Naturezas | SPEC_CNPJ.check_length = 2 — linha 195 |
| CAMADA 0-pre (Naturezas | SPEC_CNPJ.encoded_length = 7 (80^7 > 10^12) — linha 198 |
| CAMADA 0-pre (Naturezas | SPEC_IP.slot_widths = (3,3,3,3) (IPv4 octetos zero-padded a 3) — linha 123 |
| CAMADA 0-pre (Naturezas | _W1_CNPJ pesos mod-11 = [5,4,3,2,9,8,7,6,5,4,3,2] — linha 171 |
| CAMADA 0-pre (Naturezas | _W2_CNPJ pesos mod-11 = [6,5,4,3,2,9,8,7,6,5,4,3,2] — linha 172 |
| CAMADA 0-pre (Naturezas | CPF check_fn mod-11 threshold = 10 (se resto==10 então 0) — linhas 139, 143 |
| CAMADA 0-pre (Naturezas | CNPJ check_fn mod-11 threshold = 2 (se rem<2 então 0, else 11-rem) — linhas 179, 182 |
| CAMADA 0-pre (Naturezas | detect_cadence n_sample = 5 (primeiras N strings pra Regra 1) — linha 31 auto_cadence.py |
| CAMADA 0-pre (Naturezas | detect_cadence threshold = 0.7 (LCP+LCS / length ratio mínimo) — linha 32 |
| CAMADA 0-pre (Naturezas | detect_cadence numeric_card_threshold = 0.5 (Regra 2 cardinality) — linha 33 |
| CAMADA 0-pre (Naturezas | detect_min_len n_threshold = 100 (rows mínimo pra aplicar heurística) — linha 49 auto_min_len.py |
| CAMADA 0-pre (Naturezas | detect_min_len gating decision: n < 100 -> return 3 (preserva M9 baseline) — linha 50 |
| CAMADA 0-pre (Naturezas | analyze_column sample_size = 20 (amostra pra is_numeric check) — linha 51 column_features.py |
| CAMADA 0-pre (Naturezas | CPF regex pattern = r'^(\d{3})\.(\d{3})\.(\d{3})-(\d{2})$' — linha 133 |
| CAMADA 0-pre (Naturezas | CNPJ regex pattern = r'^(\d{2})\.(\d{3})\.(\d{3})/(\d{4})-(\d{2})$' — linha 169 |
| CAMADA 0-pre (Naturezas | IPv4 regex pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$' — linha 118 |
| Dispatch, Multi-Column, Pipeli | cfg.pre_pass (bool, default True) — enable pre-pass heuristics or use defaults (cadence=False, min_len=3) |
| Dispatch, Multi-Column, Pipeli | cfg.obat_shape_preserve (bool, default True) — enable shape-consistency hint in OBAT if cadence detected |
| Dispatch, Multi-Column, Pipeli | cfg.hcc_seq_rle (bool, default True) — enable seq-RLE near-identical compaction (M10) or use M9 pure |
| Dispatch, Multi-Column, Pipeli | parallel (bool|int, default False) — False=serial, True=os.cpu_count(), int N=N workers; ignored if len(table)<2 |
| Dispatch, Multi-Column, Pipeli | nature (TemplatedCheckedSpec | None, default None) — apply pre-tx filter per value (list input only) |
| Dispatch, Multi-Column, Pipeli | nature_per_col (dict[str, TemplatedCheckedSpec] | None, default None) — apply pre-tx filter per column (dict input only) |
| Dispatch, Multi-Column, Pipeli | detect_cadence: n_sample=5 (tunable in detect_cadence_from_features) — size of prefix sample for rule 1 |
| Dispatch, Multi-Column, Pipeli | detect_cadence: threshold=0.7 (tunable) — min (LCP+LCS)/length ratio for rule 1 |
| Dispatch, Multi-Column, Pipeli | detect_cadence: numeric_card_threshold=0.5 (tunable) — cardinality threshold for rule 2 |
| Dispatch, Multi-Column, Pipeli | detect_min_len: n_threshold=100 (tunable) — gating: n_rows < 100 always 3 (M9 baseline preservation) |
| Dispatch, Multi-Column, Pipeli | obat_shape_preserve: min_len parameter (from pre-pass) — minimum lengths for pref/suf in shape preservation |
| Dispatch, Multi-Column, Pipeli | seq_rle: delta format (int vs list[int]) — M10-compat single delta or ADR-0016 per-run deltas |
| Dispatch, Multi-Column, Pipeli | multi-col: col name validation — no ',' or '=' allowed in column names (hard constraint) |
| Dispatch, Multi-Column, Pipeli | multi-col: workload heuristic — sum(len(v) for v in col) used to order columns for parallel dispatch |

### Todos os extension points (hooks pra v2.0/futuro)

| Subsistema | Hook |
|---|---|
| CAMADA 0 | New detector heuristica (ex: detector_entropy_per_col, detector_low_cardinality_dict_candidate): plugar em _encode_column:141-145, chamar com ColumnFeatures pre-computada, retornar (bool_signal, info_dict). Adicionar ao cadence_info se necessario. |
| CAMADA 0 | Decision tree refinement para detect_min_len_from_features: novo modulo auto_min_len_v4 com machine learning classifier em lugar de thresholds hard-coded. Input ColumnFeatures, output min_len—mantém interface identica. Requer validacao em 58+ colunas reais. |
| CAMADA 0 | Lossy pre-filter (CAMADA 0 alternativa, ADR-0015 menciona): natureza-based pre-transform (TemplatedCheckedSpec, TemplatedPaddedSpec) aplica encode_value() ANTES de analyze_column. Novo entry point: IF nature param, pipeline: values → encode_value(nature, v) → transformed_values → analyze_column(transformed_values) → rest de CAMADA 0. Ja' tem infra em src/tcf/natures/; extensivel. |
| CAMADA 0 | Feature cache/memoization: analyze_column O(N) eh barato mas repetido em multi-col. Pooled executor (Fase 2) pode pre-compute features em paralelo antes encoder loop. |
| CAMADA 0 | Cadence regra 3 (futura, H-DA-09c/09d): detector de patterns estruturais adicionais (ex: regex-based, run-length encoding patterns). Adicionar regra ao detect_cadence_from_features com novo threshold set. Nao requer mudanca interface. |
| CAMADA 0 | Parametrizado adaptive thresholds: tuning dinamico baseado em column profile (ex: if is_numeric AND card>0.7 → threshold=0.6 em vez de 0.7). Requer oracle feedback loop (Fase 3 T-CODE-SCHEMA-BUILDER). |
| CAMADA 0 | Multi-column correlation detector: futura heuristica que analisa dependencias entre colunas (ex: ID columns sempre high-card, phone sempre fixed-format). Input: dict[col_name → ColumnFeatures], output: per-col hints. Extensao natural em multi_encoder.py. |
| CAMADA 0 | Shaper customizado para obat_shape.py: _try_preserve_shape eh hardcoded (exato→wider→greedy). Permitir plugging de estrategia customizada via prefer_shape_strategy=Callable. Ex: prefer_shape_strategy=my_aggressive_shaper retorna (p,pl,s,sl) ou None baseado em heuristica customizada. |
| CAMADA 0 | Dictionary v2.0 (futuro, roadmap): detector_low_cardinality_dict_candidate integra em CAMADA 0 pra marcar colunas dict-comprimidas (ex: card<0.1, frequencias Zipf-like). Saida: coluna especial 'dict_id' flag; processamento diferente em CAMADA 1. Requer novo ColumnFeatures field (freq_distribution, top_k_values). |
| CAMADA 0 | Patricia Trie (futura, teoria): alternativa OBAT para strings muito longas (avg_len>30). Novo detector em detect_min_len_from_features.py que retorna enum {obat, patricia_trie} em lugar de int min_len. Encoder route baseado em resultado. |
| CAMADA 1 | Alternative prefix/suffix index structure: current trigram k=3 is hardcoded. H-PERF-04 proposes middle-trigram s[len//2-1:len//2+2] for date strings to reduce bucket bloat. Could plug via parameterized _build_prefix_index(strings, k, middle_offset) returning same dict[str, list[int]] interface. |
| CAMADA 1 | Longer trigram variants (k=4, k=5) for higher selectivity: would require updating min_len defaults and tie-break semantics. API preserved: processar(strings, k=3, min_len=None) where min_len auto-inferred from k. |
| CAMADA 1 | Alternative LCP/LCS algorithms: current naive O(min(len_a, len_b)) via char-by-char scan. v2.0 could use: (1) SIMD vectorization (H-PERF-06), (2) Karp-Rabin rolling hash + verification (sub-O(L) expected), (3) Z-algorithm for batch prefix matching. API: swap lcp_len/lcs_len implementations, processar() unchanged. |
| CAMADA 1 | Greedy cover variants: current _escolher_par does 2-candidate selection when overlap. v2.0 could try: (1) 3+ candidates (tri-way split pref/mid/suf), (2) dynamic-programming optimal cover (exponential cutoff), (3) constraint solver. Decision point in line 129: wrap _escolher_par in strategy pattern. |
| CAMADA 1 | Shape-preserve hint extensions: current processar_with_hint memorizes (p_src, p_len, has_L, s_src, s_len). v2.0 could: (1) memorize longer history (last 3 shapes), (2) cluster similar shapes per prefix, (3) use ML classifier to predict shape. Interface: extend last_shape from 5-tuple to dict. |
| CAMADA 1 | Per-column custom min_len via schema metadata: ADR-0010 auto-detect is global heuristic. v2.0 could accept user-provided min_len hints via encode(..., min_len_hints={'col_name': 6}). Preprocessor in _encode_column overrides detect_min_len. |
| CAMADA 1 | Comparative affixes: instead of absolute LCP/LCS length, compare against +N reference strings (not just best). E.g., _melhor_pref_relative(s, strings, k_top=3) returns top-3 matches by relative gain. Would change _escolher_par signature. |
| CAMADA 1 | Patricia trie index (H-PERF-04): currently hash buckets. v2.0 could replace prefix_index with trie for O(L + log B) prefix search. Requires _build_prefix_trie() returning compatible interface. |
| CAMADA 1 | Lossy/dictionary modes (v2.0 roadmap): current OBAT byte-canonical, lossless. v2.0 could add (1) dictionary compression (extract common substrings), (2) lossy quantization (round numeric affixes), (3) hybrid mode. Would add new Token types; processar() signature unchanged but new variants processar_lossy(). |
| CAMADA 1 | Online re-indexing / dynamic bucketing: current indexes built once, buckets grow without cap. v2.0 could rehash buckets at N_THRESHOLD (e.g., 10K strings) to keep B bounded. Internal optimization; API unchanged. |
| HCC (Hierarchical Compositiona | **Novos marcadores léxicos** (v2.0): adicionar em _emit_body + decoder _parse_decl |
| HCC (Hierarchical Compositiona | **Dicionário pré-computado**: substitui detector greedy por lookup hash (opt-in) |
| HCC (Hierarchical Compositiona | **Lossy compactação**: novo operador (~L) ou flag em alias_to_sub |
| HCC (Hierarchical Compositiona | **Ordenação alternativa**: knob order_strategy (net|freq|hybrid) em linha ~300 |
| HCC (Hierarchical Compositiona | **Patricia trie**: substituir Counter+scan por trie (sem sintaxe mudança) |
| HCC (Hierarchical Compositiona | **Header carry spec_id**: adiciona spec_id em header (coordena natures) |
| HCC (Hierarchical Compositiona | **Fallback mechanism**: *FALLBACK|literal pra valores incompressíveis |
| HCC (Hierarchical Compositiona | **K-way restrição**: knob max_K_per_candidate (default unlimited) |
| CAMADA 2b | Fase 2 multi-delta support: remover linha 110-111 reject em compare_for_seq. Permitiria [1,2] ou [1,2,3]. Impacto: marker formato ainda CSV `*N+d1,d2,d3|`, parser identico. Decoder não muda. Test suite: atualizar test_hcc_multi_delta.py:49-53 (atualmente xfail 'multiple_non_zero'). |
| CAMADA 2b | Parametrico run-matching: generalizar find_escape_digit_runs pra aceitar outros patterns (hex \xFF, octal \123, ou custom regex). Extensão: adicionar 'run_detector' callback em HCCSeqRLE.__init__, used em place of hardcoded find_escape_digit_runs. |
| CAMADA 2b | Overflow handling strategies: adicionar knob 'overflow_mode' em HCCSeqRLE: 'preserve' (atual), 'truncate' (modulo width), ou 'reject' (skip run se overflow). Afeta shift_escape_digits linha 138-147. |
| CAMADA 2b | Per-run compaction cost threshold: atualmente todos runs compactados se detectados. Futura: threshold 'min_savings' em compact_body pra rejeitar runs que economizam < K bytes. Usado em 'near-identical mas não suficientemente repetido'. |
| CAMADA 2b | Multi-delta variant strategies: ADR-0016 Fase 1 usa CSV `d1,d2,d3` simples. Futuro Fase 2: (a) bitmask format `*N+*00*1|` (markers pra runs que variam), (b) delta-of-delta `*N+0,+1,-1,+2|` (compacta patterns tipo alternating), (c) base+perturb `*N+base=1,deltas=[0,0,1,2]|` (separado offset global). |
| CAMADA 2b | Marker syntax evolution: atualmente `*N+deltas|template`. Futuro: optional repeat-hint `*N:3+deltas|` (já know run repeats 3x, hint pra decoder), ou compressed template se muito grande. |
| CAMADA 2b | Integration com pré-processamento: HCCSeqRLE atualmente post-process puro (sem info de OBAT tokens). Futuro: token-aware seq-RLE — se sabemos que 2 tokens diferem apenas em 1 run, priorize essa compactação. |
| CAMADA 2b | Partial run detection: atualmente rejeita runs diferentes. Futuro: 'suffix-only' mode — compacta se last N runs matching, ignore prefix differences (ex: timestamp prefix + counter suffix). |
| CAMADA 2b | Streaming variant: HCCSeqRLE atualmente batcher (full body_lines in memory). Futuro: stream mode pra large datasets — detecta runs incrementally, emits markers on-the-fly. |
| CAMADA 0-pre (Naturezas | **Adicionar nova spec Checked (ex: Luhn para cartão crédito)**: criar novo TemplatedCheckedSpec com regex próprio, body_length, check_fn(body)->list[int], formatter, encoded_length; nenhuma mudança em core — polimorfismo via spec param garante compatibilidade. |
| CAMADA 0-pre (Naturezas | **Adicionar nova spec Padded (ex: MAC address, CEP brasileiro)**: implementar TemplatedPaddedSpec com regex, slot_widths tuple, separator; mesma filosofia sans check — HCC seq-RLE pode explorar estrutura se houver cadência. |
| CAMADA 0-pre (Naturezas | **v2.0 lossy-recoverable (H-LR-*)**: criar `TemplatedLossySpec(name, regex, body_length, rounding_fn, error_fn, encoded_length)` — encode retorna (rounded, error_term) packed; decode soma. Não afeta rt mas reduz bytes em floats/coords com tolerância. Plugar via pipeline nature param idêntico. |
| CAMADA 0-pre (Naturezas | **v2.0 strip-sufixo (V2-D)**: criar `TemplatedSuffixSpec(name, regex, suffix_dict, body_spec)` — detecta sufixo enumerated (ex: '.com' em email), enumera, encode retorna (body_encoded, suffix_idx). Composição com Templated+Enumerated. |
| CAMADA 0-pre (Naturezas | **v2.0 auto-detect naturezas (Schema_builder Fase 3)**: em build_schema, para cada coluna adicionar `detect_nature_via_apply_rate(column_name, values, threshold=0.8)` — retorna SPEC_CPF se 80%+ valores são 'compressible' CPF. Popula `ColumnSchema.natures` list. Requer header carry spec id pra decoder auto-detectar (ADR-0015 futuro sec 159-161). |
| CAMADA 0-pre (Naturezas | **v2.0 header carry spec id**: modificar TCF format #TCF.6 M multi-col meta line pra incluir nature spec identifier per coluna (ex: `col1=cpf col2=ip`). Decoder lê header, auto-detecta spec sem out-of-band. Single-col: adicionar marker no body inicial. |
| CAMADA 0-pre (Naturezas | **Threshold tunning pra CAMADA 0**: `encode(..., layers=PipelineConfig(nature_apply_threshold=0.8))` — aplica nature só se apply_rate >= threshold. Futuro T-CODE-LAYERED-PIPELINE Fase 2. |
| CAMADA 0-pre (Naturezas | **Fallback adaptativo**: atualmente '_' marker é binário (usa ou não). v2 pode ter graduated fallback: 'partial_compress' (encode parte) vs 'literal' vs 'hybrid' (mix chars base94 + literal). Requer extend Protocol NatureSpec com encode_partial method. |
| Dispatch, Multi-Column, Pipeli | V2-A (Fallback Identity Per-Column): Inject at _encode_column return, emit marker if HCC ratio below threshold, decoder skips HCC on fallback. Meta: '=name' vs 'size=name'. Touch: multi.py header/decode, encoder dispatch. |
| Dispatch, Multi-Column, Pipeli | V2-B (Dictionary Layer): Pre-HCC dict for high-repetition. CAMADA 2.5 dispatch: if n_unicas < threshold*n_rows, build value->id dict, emit dict meta (size/dict_id=name). Touch: multi.py meta builder, decoder dict marker. |
| Dispatch, Multi-Column, Pipeli | V2-C (Patricia Trie Ref Index): Replace trigram hash in OBAT with prefix trie. Same tokens, backward-compat. Touch: core/online.py, obat_shape.py. |
| Dispatch, Multi-Column, Pipeli | V2-D (Lossy Compression): New nature category (NatureLosy) with encode_value/decode_value. Marker prefix distinct from Templated. Example: float rounding. Touch: encoder.py nature dispatch, natures/. |
| Dispatch, Multi-Column, Pipeli | V2-E (Adaptive Layer Selection): Per-column cfg markers in meta ('size:cfg=name', cfg='p0_h0_s1'). Heterogeneous pipelines. Touch: multi.py meta encode/decode. |
| Dispatch, Multi-Column, Pipeli | V2-F (Streaming Encoder): _encode_column as generator (yield chunks). Out-of-core support. HCCSeqRLE buffering strategy. Touch: encoder.py, multi.py workers. |
| Dispatch, Multi-Column, Pipeli | V2-G (Cross-Column Atom Sharing): Global alias namespace, sub-tuplas span cols. Multi-col body merger. Complex meta. Touch: multi.py merger, HCC detector. |
| Dispatch, Multi-Column, Pipeli | V2-H (Custom Tokenizer Plugin): Token protocol extensible (TokCustom variant). cfg.tokenizer_plugin dispatch. Touch: encoder.py line 150/155, plugin registry. |
| Dispatch, Multi-Column, Pipeli | V2-I (Per-Layer Decision Markers): Embed comments in body ('# CADENCE=1', '# MIN_LEN=4') for auto decoder intelligence. Touch: side_outputs, decoder comment strip. |

---

## Como usar este doc

- **Pra estudar uma camada**: va na secao numerada (1-6), leia control_flow + estrategias.
- **Pra encontrar onde plugar algo novo**: tabela 'Extension points' no fim.
- **Pra entender uma decisao do encoder**: cruze a tabela de estrategias pelo file:line.
- **Pra ver thresholds existentes**: tabela 'knobs' no fim.

Para o roteiro v2.0 fundamentado: ver [ADR-0018](../adr/0018-v2-format-roadmap.md).
Para o formato em si: ver [TCF-format.md](../algorithms/TCF-format.md).
