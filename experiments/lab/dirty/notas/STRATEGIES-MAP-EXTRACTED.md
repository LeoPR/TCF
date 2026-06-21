# STRATEGIES MAP — extrato bruto (control-flow por camada)

> **CONSOLIDAR / extrato histórico (faxina 2026-06-21)**: este é o dump bruto que foi
> curado e segmentado no hub oficial **[`docs/theory/strategies/INDEX.md`](../../../../docs/theory/strategies/INDEX.md)**
> (mapa de estratégias por subsistema) + `docs/theory/strategies-map.md`. Use o hub como
> a versão navegável; este arquivo fica como material-fonte cru. Refs de linha de código
> podem estar defasadas vs `src/tcf` atual.

================================================================================
## CAMADA 0 — Pre-pass: Column Feature Analysis, Cadence Detection, Min-Len Auto-detection
================================================================================

**CONTROL FLOW**: PIPELINE CANONICO M10 em encoder.py _encode_column(encoder.py:117-178):

1. **Dedup** (encoder.py:133-136): Ordena values em dict para obter unicas, preserva ordem insercao.

2. **CAMADA 0 — Pre-pass** (encoder.py:138-146):
   a. `analyze_column(values)` [SEMPRE executada, barato O(N)] → ColumnFeatures
   b. IF cfg.pre_pass=True [default=True]:
      - `detect_cadence_from_features(features, unicas)` → (cadence_detected, cadence_info)
      - `detect_min_len_from_features(features)` → min_len ∈ {3,4,5,6}
   c. ELSE:
      - cadence_detected = False, min_len = 3 (defaults), cadence_info["rule_hit"] = None

3. **CAMADA 1 — OBAT tokenizer** (encoder.py:148-156):
   a. IF cadence_detected AND cfg.obat_shape_preserve:
      - `processar_with_hint(unicas, min_len=min_len, prefer_shape_consistency=True)`
   b. ELSE:
      - `processar(unicas, min_len=min_len)` [canonical sem hint]

4. **CAMADA 2 — HCC compactacao** (encoder.py:158-163):
   a. IF cfg.hcc_seq_rle=True [default]:
      - `HCCSeqRLE.encode(values, unicas, tokens, header)`
   b. ELSE:
      - `M8AVirtualRefsSyntax.encode(...)` [M9 puro, sem seq-RLE]

5. **Side outputs** (encoder.py:165-177): Popula SideOutputs dict se fornecido.

DECISOES ENCADEADAS:
- analyze_column OUTPUT (features) →  input a detect_cadence + detect_min_len (parallelizable em teoria)
- detect_cadence OUTPUT (bool) → condicao PARA obat_shape_preserve
- detect_min_len OUTPUT (min_len) → param a OBAT variant escolhido
- OBAT tokens OUTPUT → input a HCC

CONFIG TOGGLES (pipeline.py):
- cfg.pre_pass={True|False}: gating da pipeline 0 (analyze + 2-detect)
- cfg.obat_shape_preserve={True|False}: gating hint em OBAT (requer cadence_detected=True)
- cfg.hcc_seq_rle={True|False}: gating HCC variant (M10 vs M9)
- DEFAULT_PIPELINE = PipelineConfig() = (True, True, True) = M10 canonical

**KNOBS**:
  - detect_cadence_from_features.n_sample = 5 (tamanho amostra regra 1)
  - detect_cadence_from_features.threshold = 0.7 (limiar LCP+LCS/L regra 1)
  - detect_cadence_from_features.numeric_card_threshold = 0.5 (limiar card regra 2, ADR-0008)
  - analyze_column.sample_size = 20 (amostra pra check is_numeric)
  - detect_min_len_from_features.n_threshold = 100 (gating por n_rows)
  - detect_min_len decision tree implicit thresholds: card<0.2, card>=0.2, card>=0.4, card>=0.7, card>=0.8, avg_len∈{3,5,8,12,25}
  - PipelineConfig.pre_pass = True (default, ativa/desativa CAMADA 0)
  - PipelineConfig.obat_shape_preserve = True (default, ativa hint em OBAT se cadence)
  - PipelineConfig.hcc_seq_rle = True (default, M10 vs M9 variant)
  - _lcp_len / _lcs_len implementacao: scan caractere-por-caractere fixo (nao parametrizado)
  - _try_preserve_shape fallback hierarchy: exato → wider → greedy (deterministica, nao parametrizada)

**EXTENSION POINTS (v2.0 hooks)**:
  - New detector heuristica (ex: detector_entropy_per_col, detector_low_cardinality_dict_candidate): plugar em _encode_column:141-145, chamar com ColumnFeatures pre-computada, retornar (bool_signal, info_dict). Adicionar ao cadence_info se necessario.
  - Decision tree refinement para detect_min_len_from_features: novo modulo auto_min_len_v4 com machine learning classifier em lugar de thresholds hard-coded. Input ColumnFeatures, output min_len—mantém interface identica. Requer validacao em 58+ colunas reais.
  - Lossy pre-filter (CAMADA 0 alternativa, ADR-0015 menciona): natureza-based pre-transform (TemplatedCheckedSpec, TemplatedPaddedSpec) aplica encode_value() ANTES de analyze_column. Novo entry point: IF nature param, pipeline: values → encode_value(nature, v) → transformed_values → analyze_column(transformed_values) → rest de CAMADA 0. Ja' tem infra em src/tcf/natures/; extensivel.
  - Feature cache/memoization: analyze_column O(N) eh barato mas repetido em multi-col. Pooled executor (Fase 2) pode pre-compute features em paralelo antes encoder loop.
  - Cadence regra 3 (futura, H-DA-09c/09d): detector de patterns estruturais adicionais (ex: regex-based, run-length encoding patterns). Adicionar regra ao detect_cadence_from_features com novo threshold set. Nao requer mudanca interface.
  - Parametrizado adaptive thresholds: tuning dinamico baseado em column profile (ex: if is_numeric AND card>0.7 → threshold=0.6 em vez de 0.7). Requer oracle feedback loop (Fase 3 T-CODE-SCHEMA-BUILDER).
  - Multi-column correlation detector: futura heuristica que analisa dependencias entre colunas (ex: ID columns sempre high-card, phone sempre fixed-format). Input: dict[col_name → ColumnFeatures], output: per-col hints. Extensao natural em multi_encoder.py.
  - Shaper customizado para obat_shape.py: _try_preserve_shape eh hardcoded (exato→wider→greedy). Permitir plugging de estrategia customizada via prefer_shape_strategy=Callable. Ex: prefer_shape_strategy=my_aggressive_shaper retorna (p,pl,s,sl) ou None baseado em heuristica customizada.
  - Dictionary v2.0 (futuro, roadmap): detector_low_cardinality_dict_candidate integra em CAMADA 0 pra marcar colunas dict-comprimidas (ex: card<0.1, frequencias Zipf-like). Saida: coluna especial 'dict_id' flag; processamento diferente em CAMADA 1. Requer novo ColumnFeatures field (freq_distribution, top_k_values).
  - Patricia Trie (futura, teoria): alternativa OBAT para strings muito longas (avg_len>30). Novo detector em detect_min_len_from_features.py que retorna enum {obat, patricia_trie} em lugar de int min_len. Encoder route baseado em resultado.

**STRATEGIES** (14):

### [estrategia] analyze_column  (src/tcf/column_features.py:51-84)
  desc: Computa features basicas de uma coluna em 1 passada O(N) sobre values. Extrai: n_rows (total), n_unicas (distinct count), avg_len (media de comprimentos), cardinality (n_unicas/n_rows como razao), is_numeric (check amostragem), sample (tuple de primeiras N strings para analises posteriores). is_numeric eh True somente se TODAS strings do sample parsam float(). Edges: coluna vazia retorna features zerados com is_numeric=False. Sample padrao=20.
  params: sample_size=20 (tamanho amostra pra check is_numeric). Computacao O(N) on n_rows.
  triggers: Sempre computa (barato, util pra side outputs). Entrada obrigatoria em encoder.py:139 antes de qualquer decisao pre-pass.
### [estrategia] detect_cadence_from_features  (src/tcf/auto_cadence.py:28-96)
  desc: 2-regra heuristica pra detectar se coluna tem cadencia estrutural (justifica usar processar_with_hint com prefer_shape_consistency=True). Regra 1 (wrapper+counter): lengths uniformes em primeiras n_sample strings E (LCP+LCS)/L >= threshold em TODOS pares consecutivos → rule_hit='1-uniform-length-high-lcp-lcs'. Regra 2 (numeric high-card, ADR-0008): is_numeric=True AND cardinality > numeric_card_threshold → rule_hit='2-numeric-high-cardinality'. Retorna (bool, dict info) onde info contem rule_hit, reasoning, lcp_lcs_ratios se aplicavel, cardinality, is_numeric. Requer len(strings_unicas) >= 2; senao retorna False+reason='muito poucas strings'.
  params: n_sample=5 (tamanho amostra regra 1, default primeiras 5 unicas). threshold=0.7 (limiar ratio LCP+LCS/L em regra 1). numeric_card_threshold=0.5 (cardinalidade threshold regra 2, ADR-0008). Parametros tunaveis.
  triggers: Disparada em encoder.py:141 IF cfg.pre_pass=True. Entrada: ColumnFeatures pre-computada + lista strings_unicas. Output decide se obat usa hint ou nao (encoder.py:149-156).
### [estrategia] detect_min_len_from_features  (src/tcf/auto_min_len.py:25-68)
  desc: Heuristica v3 (shallow decision tree) auto-detecta min_len otimo baseado em avg_len, cardinality, is_numeric. Decision tree com gating (n < n_threshold→3) + 6 regras sequenciais (primeira match wins): card<0.2→3 (baixa-card seguro), avg_len>=25→6 (long-form), avg_len>=8 AND card>=0.4→6 (dates/mid-len high-card), avg_len>=5 AND is_numeric AND card>=0.8→6 (numeric high-card), avg_len>=12 AND card>=0.7→5 (phone-like), avg_len>=3 AND card>=0.2→4 (IDs sequenciais), else→3. Captura 99.5% do oracle (melhor min_len possivel) em 58 colunas real-world (Adult+TPC-H). Gating n<100 preserva M9 baseline EXATO (1615B D1-D9).
  params: n_threshold=100 (lower gating: n<100→return 3, datasets pequenos recebem default seguro). Thresholds internos: card<0.2, avg_len buckets {3,5,8,12,25}, ratios {0.2,0.4,0.7,0.8}. Todos empíricos em 58 colunas reais.
  triggers: Disparada em encoder.py:142 IF cfg.pre_pass=True. Entrada: ColumnFeatures pre-computada. Output min_len∈{3,4,5,6} passado a OBAT (encoder.py:150/155).
### [helper] _is_numeric_string  (src/tcf/column_features.py:26-34)
  desc: Helper que determina se uma string individual eh numerica (aceita int, float, negativos, exponencial '1e5'). Implementacao: try float(v) return True, except ValueError/TypeError return False. Empty string retorna False. Usado em analyze_column para compor is_numeric field (sample-based check).
  params: Nenhum parametro; logica fixa float() try-except.
  triggers: Disparada por analyze_column:75 para cada string em sample (sample_size=20). Resultado acumulado via all().
### [estrategia] processar_with_hint  (src/tcf/obat_shape.py:64-120)
  desc: Variante de OBAT tokenizer com dica opcional prefer_shape_consistency. Quando False, comporta-se identico ao processar() canonical. Quando True: apos cada string emitida, memoriza shape=(p_src, p_len, has_L, s_src, s_len); pra proxima string, tenta replicar exatamente via _try_preserve_shape. Fallbacks: (1) exato: lcp_avail>=p_len_old AND lcs_avail>=s_len_old, (2) wider: reduz p_len/s_len a max possivel se exato falhar (lcp_avail, lcs_avail), (3) greedy: cai pra OBAT canonical se nem wider funciona. Input: strings_unicas (deduplicated), min_len (from pre-pass), prefer_shape_consistency (from cadence detection). Output: (tokens_por_string, log_string).
  params: prefer_shape_consistency={True|False} (toggleavel via cfg.obat_shape_preserve=True default). min_len inherit de detect_min_len_from_features.
  triggers: Disparada em encoder.py:150-155 baseado em cadence_detected AND cfg.obat_shape_preserve. IF ambos true, usa processar_with_hint(prefer_shape_consistency=True). ELSE usa processar() canonical (src/tcf/core/online.py).
### [helper] _try_preserve_shape  (src/tcf/obat_shape.py:32-61)
  desc: Tenta replicar last_shape em string s. Valida: last_shape deve ter has_L=True (literal existe entre prefix e suffix), p_src/s_src devem estar em range (idx_limit). Calcula lcp_avail/lcs_avail contra s e prev strings. Tenta exato (lcp_avail>=p_len_old AND lcs_avail>=s_len_old); se falhar, tenta wider reduzindo ambos a minimo disponivel, validando new_len > 0 e ambos >= min_len. Retorna (p_src, p_len, s_src, s_len) tupla ou None.
  params: Nenhum parametro configuravel; logica deterministica.
  triggers: Disparada por processar_with_hint:92 IF prefer_shape_consistency=True AND last_shape is not None (apos primeira string emitida).
### [marcador] PipelineConfig  (src/tcf/pipeline.py:35-60)
  desc: Dataclass frozen com 3 boolean toggles controlando CAMADA 0-3 comportamento. pre_pass (default=True): ativa analyze_column+detect_cadence+detect_min_len. obat_shape_preserve (default=True): usa processar_with_hint com hint=True se cadence detected. hcc_seq_rle (default=True): aplica HCCSeqRLE vs M8AVirtualRefsSyntax. Default singleton DEFAULT_PIPELINE = PipelineConfig() equivale a M10 canonical. Motivacao: ablation + debug sem hardcode.
  params: 3 boolean flags, todos default=True → M10 canonical invariant.
  triggers: Passado via layers= param em encode() (encoder.py:60). Usado em _encode_column (encoder.py:140-156) como cfg.
### [helper] lcp_len (Longest Common Prefix)  (src/tcf/core/online.py:59-64)
  desc: Computa LCP length entre duas strings a,b via scan caractere-por-caractere ate' mismatch ou fim da menor string. Usa min(len(a), len(b)) como limite. O(min(|a|,|b|)) simples. Usado em detect_cadence para computar ratio (lcp+lcs)/L em pares consecutivos (regra 1), e em obat_shape para validar se pode replicar shape anterior.
  params: Nenhum; logica fixa.
  triggers: Disparada por detect_cadence_from_features:70 em cada par (sample[i-1], sample[i]) pra regra 1. Disparada por _try_preserve_shape:44 para validar preservacao.
### [helper] lcs_len (Longest Common Suffix)  (src/tcf/core/online.py:67-72)
  desc: Computa LCS length entre duas strings a,b via scan de tras pra frente (indices negativos) ate' mismatch. O(min(|a|,|b|)). Dual de lcp_len. Mesmos usos em detect_cadence + obat_shape.
  params: Nenhum; logica fixa.
  triggers: Disparada por detect_cadence_from_features:71 em cada par. Disparada por _try_preserve_shape:45.
### [threshold] Cardinality Threshold (0.5, 0.2, etc)  (src/tcf/auto_cadence.py:33, src/tcf/auto_min_len.py:56-66)
  desc: Multiplos thresholds de cardinalidade (razao n_unicas/n_rows) usados em decisoes: (1) numeric_card_threshold=0.5 em detect_cadence Regra 2 (valores numericos com >50% distinct → cadence estrutural, ADR-0008). (2) Implicit thresholds em detect_min_len: card<0.2→ml=3, card>=0.2→ml=4, card>=0.4→ml=6 (com avg_len), card>=0.7→ml=5. (3) card>=0.8 com is_numeric+avg_len>=5→ml=6. Empirico em 58 colunas reais; pode nao generalizar a datasets novos.
  params: 0.5 (numeric_card_threshold), 0.2/0.4/0.7/0.8 (implicit em auto_min_len). Tunaveis, nenhum exposto via API publica.
  triggers: Usados em detect_cadence_from_features:87 (Regra 2) e detect_min_len_from_features:56-66 (decision tree).
### [threshold] Average Length Buckets  (src/tcf/auto_min_len.py:58-66)
  desc: Decision tree em auto_min_len usa buckets de avg_len (media tamanho string na coluna) como gating: avg_len<3→ml=3 (default), avg_len>=3 AND card>=0.2→ml=4, avg_len>=5 (+ is_num+card>=0.8)→ml=6, avg_len>=8 (+ card>=0.4)→ml=6, avg_len>=12 (+ card>=0.7)→ml=5, avg_len>=25→ml=6. Empirico em real-world. Representa padrao: strings muito longas=higher min_len safe.
  params: Buckets fisos: {3, 5, 8, 12, 25}. Tunaveis, nenhum exposto API publica.
  triggers: Usados em detect_min_len_from_features:58-66 (decision tree sequencial).
### [threshold] LCP+LCS Ratio Threshold (0.7)  (src/tcf/auto_cadence.py:32, linha 76)
  desc: Regra 1 de detect_cadence requer que em TODOS os pares consecutivos do sample, (lcp+lcs)/L >= 0.7 (default). L = tamanho uniforme string. Threshold 0.7 significa >=70% dos caracteres em pair sao LCP ou LCS (comuns). Escolhido empiricamente para detectar wrapper+counter patterns (ex: wrapper='[' L=']', numeric counter no meio). Valor atual reflete ADR-0008 real-world validation (0.7 bom balance para HELP vs HURT).
  params: threshold=0.7 (default, parametro tunable em detect_cadence_from_features).
  triggers: Usado em detect_cadence_from_features:76 condicao ALL ratios >= threshold.
### [decision-point] n_rows Gating (n >= 100)  (src/tcf/auto_min_len.py:49-50)
  desc: Gating em detect_min_len_from_features: IF n_rows < n_threshold (100 default), return 3 (fallback seguro). Justificativa: datasets pequenos (D1-D9 sinteticos, n=12-20) com heuristica complexa pode quebrar M9 baseline invariant. Empirico: n<100 recebem default ml=3, preserva 1615B exato em D1-D9. Datasets reais (Adult/TPC-H n=1000-5000) passam gating, recebem heuristica completa.
  params: n_threshold=100 (limite gating, tunable via detect_min_len_from_features param). Default M9 ml=3 quando gateado.
  triggers: Avaliada primeira em detect_min_len_from_features:49 ANTES de decision tree.
### [threshold] Sample Size (n_sample=5)  (src/tcf/auto_cadence.py:31, linha 59)
  desc: Tamanho da amostra de strings unicas para regra 1 (wrapper+counter) em detect_cadence. Default=5 significa primeiras 5 strings unicas sao analisadas pra uniformidade de length e ratios LCP+LCS. Escolha empirica: suficiente pra detectar pattern, sem overhead grande. Tunable via parametro detect_cadence_from_features(n_sample=...).
  params: n_sample=5 (default, tunable).
  triggers: Usado em detect_cadence_from_features:59 pra limitar analise a primeiras N unicas.

**NOTES**: SUBSISTEMA CAMADA 0 EXAUSTIVO — PRE-PASS UNIFICADO:

OBJETIVO ADR-0014/11: Single-pass O(N) pre-analysis extrai features coluna, informando decisoes CAMADA 1-3 (OBAT tokenizer + HCC compactacao). Zero duplicacao feature computation; reuso via ColumnFeatures imutavel.

COMPONENTES:

1. **ColumnFeatures (dataclass frozen)**: 6 fields (n_rows, n_unicas, avg_len, cardinality, is_numeric, sample). Computado por analyze_column(values, sample_size=20) em O(N) single pass. is_numeric via sample-based check: ALL strings[:20] parse float(). Usado como input chave em detect_cadence + detect_min_len + (future detectors).

2. **detect_cadence_from_features (2-rule)**: 
   - Regra 1: len(strings_unicas) > 1 AND lengths uniformes (set(lens)==1) AND for ALL pares (s[i-1],s[i]) in sample: (lcp+lcs)/L >= 0.7 → rule_hit='1-uniform-length-high-lcp-lcs'. Padroes: wrapper+counter ('[...VALUE...]').
   - Regra 2 (ADR-0008): is_numeric=True AND cardinality > 0.5 → rule_hit='2-numeric-high-cardinality'. Padroes: numeric IDs, timestamps, decimais.
   - Empirico: 12 HELP (cadence util) + 22 HURT (cadence prejudicial) + 42 NO-OP em 76 colunas reais. Regra 2 captura todos 12 HELP; 7 NO-OPs adicionais (custo zero).
   - Output: (bool, dict info) com rule_hit, lcp_lcs_ratios[], cardinality, is_numeric, reason.
   - Condicao IF: encoder.py:149 cadence_detected AND cfg.obat_shape_preserve → usa processar_with_hint(prefer_shape_consistency=True).

3. **detect_min_len_from_features (heuristica v3, decision tree)**:
   - Gating: n < 100 → return 3 (preserva M9 baseline 1615B D1-D9 exato).
   - Decision tree (ordem importa, primeiro match wins):
     * card < 0.2 → 3 (baixa-cardinality sempre segura)
     * avg_len >= 25 → 6 (long-form text)
     * avg_len >= 8 AND card >= 0.4 → 6 (dates, mid-len high-cardinality)
     * avg_len >= 5 AND is_numeric AND card >= 0.8 → 6 (numeric high-cardinality)
     * avg_len >= 12 AND card >= 0.7 → 5 (phone-like)
     * avg_len >= 3 AND card >= 0.2 → 4 (IDs sequenciais, TPC-H partkey)
     * else → 3
   - Validacao sub-exp: 58 colunas real-world (Adult 1k/5k, TPC-H region/customer/lineitem 5k). Captura oracle 99.5% (melhor min_len possivel). Baseline M9 (1615B D1-D9) preservado byte-canonical.
   - Ganho real-world puro: 9.87% weighted (1,008,003B base → 908,502B, -99,501B). Top wins: l_comment -29KB, fnlwgt -22KB, l_extendedprice -20KB.
   - Condicao IF: encoder.py:142, input a OBAT (encoder.py:150/155).

4. **processar_with_hint** (OBAT variant com dica shape-preserve):
   - Variante de online OBAT tokenizer (src/tcf/core/online.py) com memory de shape anterior.
   - Shape = (p_src, p_len, has_L, s_src, s_len). Apos cada string processada, memoriza shape.
   - Proxima string: _try_preserve_shape tenta replicar exato. Fallbacks: (1) wider reduz p_len/s_len a max disponivel, (2) greedy cai pra OBAT canonical.
   - prefer_shape_consistency={True|False}: True ativa shape memory, False = OBAT canonical sempre.
   - Empirico: ADR-0007 sub-exp revalidacao mostra ganho em wrapper patterns. Byte-canonical invariante.
   - Condicao IF: encoder.py:150 IF cadence_detected AND cfg.obat_shape_preserve.

5. **Thresholds empiricos** (todos tunaveis mas nenhum exposto API publica):
   - numeric_card_threshold = 0.5 (cadence regra 2)
   - threshold = 0.7 (cadence regra 1, LCP+LCS ratio)
   - cardinality buckets: 0.2, 0.4, 0.7, 0.8 (auto_min_len)
   - avg_len buckets: 3, 5, 8, 12, 25 (auto_min_len)
   - n_threshold = 100 (gating auto_min_len)
   - sample_size = 20 (is_numeric check)
   - n_sample = 5 (cadence regra 1)
   Justificativa: Real-world validation 58 colunas (sub-exp 2026-05-19 + 2026-05-21). Risco: pode nao generalizar a datasets novos; revisao recomendada em datasets >100 colunas.

6. **PipelineConfig toggle infrastructure** (pipeline.py):
   - 3 boolean toggles (pre_pass, obat_shape_preserve, hcc_seq_rle) controlam CAMADA 0-3.
   - DEFAULT_PIPELINE = PipelineConfig(True,True,True) = M10 canonical invariante.
   - pre_pass=False desabilita analyze_column+detect_cadence+detect_min_len, fallback defaults (cadence=False, min_len=3). Util pra ablation/debug.
   - Fase 1 (atual): boolean simples. Fase 2 (futuro): per-layer markers em body, online adaptive.

7. **Nature pre-filter (CAMADA 0 opcional, ADR-0015)**:
   - Entrada nature= param em encode(). Aplica encode_value(nature, v) ANTES de pipeline M10.
   - Exemplos: TemplatedCheckedSpec (CPF -64%, CNPJ -61%), TemplatedPaddedSpec (IP -97% subnet).
   - Modulos: src/tcf/natures/templated_checked.py, src/tcf/natures/templated_padded.py.
   - Strategy pattern: zero if/isinstance; polimorfismo via Protocol NatureSpec (encode_value/decode_value/classify_value).
   - Fallback marker `_` distingue literal de compressed; preserve RT.

RISCOS RESIDUAIS (ADR-0008 + ADR-0010):
- Cardinalidade threshold (0.5, 0.2, etc): empiricos em 58 colunas, nao testado em datasets >100 colunas.
- avg_len buckets: similar risco generalizacao.
- n_threshold=100: arbitrario; datasets 50-100 rows podem ter perfil diferente.
- is_numeric exponential notation ("1e5"): aceito, pode ser excessivo em casos.
- 7 FPs NO-OP em cadence audit (custo zero, ignoravel).

EXTENSOES V2.0 VIAVIES:
1. Dictionary detector: card<0.1 + freq Zipf-like → flag especial, processamento diferente CAMADA 1.
2. Patricia Trie: avg_len>30 → rota tokenizer alternativa.
3. ML auto-tune: classifier treinado em oracle data, replace decision tree.
4. Correlation analyzer: multi-coluna, dependencias ID/phone/categoria.
5. Cadence regras adicionais (regex, RLE, autocorrelation).
6. Patricia Trie, Adaptive thresholds (oracle feedback loop).

VALIDACAO MULTI-CAMADA (ADR-0011, canonical src/tcf):
- D1-D9 (baseline): 1615B INVARIANTE (byte-canonical preservado)
- D17a (sint): 322B INVARIANTE (nature=None)
- Adult 1k/5k: 9.87% gain vs M9
- TPC-H region/customer/lineitem 5k: 9.87% weighted gain
- RT (roundtrip): 100% em todas 57+ colunas reais
- Zero regressoes documentadas post-welding 2026-05-22

================================================================================
## CAMADA 1 — OBAT (Online Bidirectional Affix Tokenizer)
================================================================================

**CONTROL FLOW**: 
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


**KNOBS**:
  - min_len: {2, 3, 4, 5, 6}; default=3 (M9), auto-detect via H-DA-11 (ADR-0010) yields 3-6 per column
  - trigram key length k: hardcoded=3 (matches min_len default, ADR-0009)
  - n_threshold for auto-min_len gating: default=100 (ADR-0010); datasets n<100 use min_len=3
  - cardinality threshold (low): default=0.2 (ADR-0010, H-DA-11 decision tree); card < 0.2 -> min_len=3
  - avg_len buckets (H-DA-11): {25, 8, 5, 12, 3} with card thresholds (ADR-0010 line 58-67)
  - cadence threshold (H-DA-08): default=0.7 for LCP+LCS ratio (auto_cadence.py:32)
  - cadence n_sample: default=5 (first 5 strings checked for uniform length + LCP-LCS)
  - numeric_card_threshold (cadence rule 2): default=0.5 (auto_cadence.py:33)
  - cfg.pre_pass: bool, default=True (PipelineConfig:54); False disables detect_cadence + detect_min_len
  - cfg.obat_shape_preserve: bool, default=True; False skips processar_with_hint hint even if cadence detected
  - cfg.hcc_seq_rle: bool, default=True; False reverts to M9 (no seq-RLE)
  - Pipeline toggles all boolean (Fase 1), no numeric tuning exposed

**EXTENSION POINTS (v2.0 hooks)**:
  - Alternative prefix/suffix index structure: current trigram k=3 is hardcoded. H-PERF-04 proposes middle-trigram s[len//2-1:len//2+2] for date strings to reduce bucket bloat. Could plug via parameterized _build_prefix_index(strings, k, middle_offset) returning same dict[str, list[int]] interface.
  - Longer trigram variants (k=4, k=5) for higher selectivity: would require updating min_len defaults and tie-break semantics. API preserved: processar(strings, k=3, min_len=None) where min_len auto-inferred from k.
  - Alternative LCP/LCS algorithms: current naive O(min(len_a, len_b)) via char-by-char scan. v2.0 could use: (1) SIMD vectorization (H-PERF-06), (2) Karp-Rabin rolling hash + verification (sub-O(L) expected), (3) Z-algorithm for batch prefix matching. API: swap lcp_len/lcs_len implementations, processar() unchanged.
  - Greedy cover variants: current _escolher_par does 2-candidate selection when overlap. v2.0 could try: (1) 3+ candidates (tri-way split pref/mid/suf), (2) dynamic-programming optimal cover (exponential cutoff), (3) constraint solver. Decision point in line 129: wrap _escolher_par in strategy pattern.
  - Shape-preserve hint extensions: current processar_with_hint memorizes (p_src, p_len, has_L, s_src, s_len). v2.0 could: (1) memorize longer history (last 3 shapes), (2) cluster similar shapes per prefix, (3) use ML classifier to predict shape. Interface: extend last_shape from 5-tuple to dict.
  - Per-column custom min_len via schema metadata: ADR-0010 auto-detect is global heuristic. v2.0 could accept user-provided min_len hints via encode(..., min_len_hints={'col_name': 6}). Preprocessor in _encode_column overrides detect_min_len.
  - Comparative affixes: instead of absolute LCP/LCS length, compare against +N reference strings (not just best). E.g., _melhor_pref_relative(s, strings, k_top=3) returns top-3 matches by relative gain. Would change _escolher_par signature.
  - Patricia trie index (H-PERF-04): currently hash buckets. v2.0 could replace prefix_index with trie for O(L + log B) prefix search. Requires _build_prefix_trie() returning compatible interface.
  - Lossy/dictionary modes (v2.0 roadmap): current OBAT byte-canonical, lossless. v2.0 could add (1) dictionary compression (extract common substrings), (2) lossy quantization (round numeric affixes), (3) hybrid mode. Would add new Token types; processar() signature unchanged but new variants processar_lossy().
  - Online re-indexing / dynamic bucketing: current indexes built once, buckets grow without cap. v2.0 could rehash buckets at N_THRESHOLD (e.g., 10K strings) to keep B bounded. Internal optimization; API unchanged.

**STRATEGIES** (20):

### [token-type] Token type: TokLit (literal)  (src/tcf/core/online.py:30-35)
  desc: Dataclass representing a literal substring that cannot be compressed via reference to previous strings. Fields: text (str). Emitted when no LCP/LCS match >= min_len exists for a span, or when span falls between prefix and suffix references. Does NOT contribute to 'coverage' in greedy algorithm.
  params: text: str (any UTF-8)
  triggers: always (fallback for uncovered spans); first string always emits [TokLit(s)]
### [token-type] Token type: TokRefPref (prefix reference)  (src/tcf/core/online.py:38-44)
  desc: Dataclass representing a reference to the first N chars of a previous string. Fields: string_id (1-indexed), length (bytes). Decoder resolves via strings_unicas[string_id-1][:length]. Enables affix-based compression of leading patterns (e.g., email prefixes, URL paths). Byte-canonical: always uses 1-indexed IDs matching insertion order.
  params: string_id: int (1-indexed into strings_unicas); length: int (>= min_len, typically 3-25)
  triggers: when _melhor_pref finds a valid LCP >= min_len, and prefix chosen by _escolher_par does not overlap suffix
### [token-type] Token type: TokRefSuf (suffix reference)  (src/tcf/core/online.py:47-53)
  desc: Dataclass representing a reference to the last N chars of a previous string. Fields: string_id (1-indexed), length (bytes). Decoder resolves via strings_unicas[string_id-1][-length:]. Complements TokRefPref for stable trailing patterns (e.g., domain suffixes, file extensions, unit suffixes). Byte-canonical: preserves insertion order.
  params: string_id: int (1-indexed); length: int (>= min_len)
  triggers: when _melhor_suf finds a valid LCS >= min_len, and suffix chosen by _escolher_par does not overlap prefix
### [heuristica] LCP (Longest Common Prefix) calculation  (src/tcf/core/online.py:59-64 (public); 75-82 (_lcp_len_capped))
  desc: Computes max k such that a[0:k] == b[0:k]. Linear scan O(min(len(a), len(b))). _lcp_len_capped() variant accepts cap parameter to limit search (used in _melhor_pref with max_len=ls to avoid overflow). No memoization; called O(N*B) times per column (N=strings, B=avg bucket size). Critical performance path optimized via trigram index (ADR-0009).
  params: a, b: str; cap (optional, _capped variant): int = upper bound on return value
  triggers: always during _melhor_pref search; once per (candidate_prev_string) pair within bucket
### [heuristica] LCS (Longest Common Suffix) calculation  (src/tcf/core/online.py:67-72 (public); 85-94 (_lcs_len_capped))
  desc: Computes max k such that a[-k:] == b[-k:]. Linear scan from both string ends O(min(len(a), len(b))). _lcs_len_capped() variant accepts cap. Called O(N*B) times (same as LCP). Implements backward indexing a[len(a)-1-i] and b[len(b)-1-i].
  params: a, b: str; cap (optional): int = upper bound
  triggers: always during _melhor_suf search; once per candidate pair within suffix bucket
### [marcador] Hash prefix index (trigram bucketing)  (src/tcf/core/online.py:184, 196-197, 222-223; processar() initializes and maintains)
  desc: dict[str, list[int]] mapping first 3 chars (s[:3]) to zero-indexed IDs of strings with that prefix. Bucket order = insertion order = ascending ID order (preserves tie-break). Example: {'abc': [0, 3, 7], 'def': [1, 2]} for strings indexed 0-3. Size: typically 10-100 buckets per 100-5000 strings; memory O(N) where N=total string count. Trigram k=3 chosen because min_len=3 implies any valid LCP match requires s[:3]==prev[:3].
  params: trigram key length: k=3 (hardcoded, matches min_len default); bucket: list[int] (zero-indexed)
  triggers: initialized empty at start of processar(); appended to every string where ls >= min_len (after first string); read in _melhor_pref via prefix_index.get(s[:3])
### [marcador] Hash suffix index (trigram bucketing)  (src/tcf/core/online.py:185, 197-198, 223; processar() manages)
  desc: dict[str, list[int]] mapping last 3 chars (s[-3:]) to candidate IDs. Enables O(B) lookup in _melhor_suf instead of O(N) linear scan. Bucket insertion order preserved. For date-like strings (prefixes 199/200/202), buckets can grow large (2x slowdown vs partkey), but overall 5.4x speedup (ADR-0009).
  params: trigram key: s[-3:]; bucket: list[int] zero-indexed
  triggers: initialized; appended for ls >= min_len; read in _melhor_suf
### [filtro] _melhor_pref — find best prefix match  (src/tcf/core/online.py:97-112)
  desc: For string s, find best prefix LCP match against all strings in prefix bucket. Returns (best_id, best_len) where best_id is 1-indexed. Algorithm: iterate bucket (ascending ID order, preserves insertion order), compute _lcp_len_capped(s, prev, max_len=ls) for each, keep max by length (strict > comparison). Tie-break: first occurrence wins (due to > not >=). Filters by L >= min_len. Returns (0, 0) if bucket empty or no match >= min_len. O(B) where B=bucket size (vs O(N) naive). Empirically B=2-10 for most columns, up to 100+ for date prefixes.
  params: s (str), ls (len), strings (list), lens (list), prefix_index (dict), max_len (int=ls), min_len (int=3)
  triggers: called once per new string in _escolher_par; bucket filtered by s[:3] trigram
### [filtro] _melhor_suf — find best suffix match  (src/tcf/core/online.py:115-126)
  desc: Mirror of _melhor_pref for suffix. Finds best LCS match in suffix bucket. Same logic: iterate bucket ascending, _lcs_len_capped(..., max_len=ls), keep max by length, filter >= min_len, tie-break first-wins. Returns (0, 0) if empty/no match. O(B) complexity.
  params: s, ls, strings, lens, suffix_index, max_len (int=ls), min_len
  triggers: called once per new string in _escolher_par; bucket filtered by s[-3:]
### [estrategia] _escolher_par — greedy cover with overlap detection  (src/tcf/core/online.py:129-162)
  desc: Greedy algorithm choosing (pref_id, pref_len, suf_id, suf_len) to maximize coverage of string s without overlap. Fast path: if bp_len + bs_len <= ls (no overlap), return immediately. Otherwise: generate 2 candidates: (A) best_pref + suf_constrained_by(ls-bp_len), (B) best_suf + pref_constrained_by(ls-bs_len). Tie-break: max total coverage > max prefix length. Ensures middle section s[bp_len:ls-bs_len] is literal (non-empty). Preserves byte-canonical order from v0.
  params: s, ls, strings, lens, prefix_index, suffix_index, min_len (int)
  triggers: once per new string (idx >= 1) in processar; core decision point for tokenization
### [threshold] min_len threshold  (src/tcf/core/online.py:102-103, 110, 116, 124 (filtering); default 3 set in processar())
  desc: Minimum length (in bytes) for any LCP/LCS match to be considered valid. Default value 3 reflects: (a) trigram index k=3, (b) cost-benefit (2-char match overhead not worth it), (c) M9 baseline default. Filtering occurs in _melhor_pref/suf: 'if L >= min_len'. Auto-detection via H-DA-11 (ADR-0010) chooses {3,4,5,6} per column based on avg_len + cardinality + is_numeric heuristics, captures 99.5% oracle gain.
  params: int in range [2, 6]; empirically {3,4,5,6}; default=3
  triggers: passed as parameter to processar(); gates every valid match in _melhor_pref/_melhor_suf
### [estrategia] Auto-detect min_len (H-DA-11, ADR-0010)  (src/tcf/auto_min_len.py:25-68)
  desc: Decision tree heuristic choosing optimal min_len per column. Computes from ColumnFeatures (n_rows, avg_len, cardinality, is_numeric). Gating: n < 100 -> default 3 (preserves M9 baseline in small datasets). Decision tree: card < 0.2 -> 3; avg_len >= 25 -> 6; avg >= 8 and card >= 0.4 -> 6; avg >= 5 and is_numeric and card >= 0.8 -> 6; avg >= 12 and card >= 0.7 -> 5; avg >= 3 and card >= 0.2 -> 4; else 3. Validated on 58 real-world columns (Adult Census, TPC-H): 9.87% weighted compression gain, 99.5% oracle capture. Called in encoder.py _encode_column() before OBAT.
  params: features (ColumnFeatures); n_threshold (int=100); returns int in {3,4,5,6}
  triggers: pre-pass phase (CAMADA 0) in canonical M10 pipeline if cfg.pre_pass=True; always computes ColumnFeatures
### [estrategia] Cadence detection (H-DA-08, ADR-0008)  (src/tcf/auto_cadence.py:28-96)
  desc: 2-rule heuristic determining if column has structural 'cadence' (repeating patterns in shape/LCP-LCS). Rule 1 (wrapper+counter): uniform lengths in first N strings + LCP+LCS ratio >= threshold per consecutive pair -> dispara prefer_shape_consistency hint. Rule 2 (numeric high-card): all sampled strings numeric + card > 0.5 -> dispara hint. When detected, encoder switches from processar() to processar_with_hint(..., prefer_shape_consistency=True). Sub-exp validation: Real TPC-H detected ~25% of columns; marginal gain in multi-layer pipeline (hinted by presence of seq-RLE baseline).
  params: features (ColumnFeatures), strings_unicas (list[str]), n_sample (int=5), threshold (float=0.7), numeric_card_threshold (float=0.5)
  triggers: pre-pass phase (CAMADA 0) in canonical M10 if cfg.pre_pass=True; called before OBAT selection
### [estrategia] processar() — canonical OBAT  (src/tcf/core/online.py:179-225)
  desc: Main entry point. Tokenizes list of unique strings via LCP+LCS greedy cover. For each string idx=0: emit [TokLit(s)]. For idx>=1: call _escolher_par, emit tokens (TokRefPref + TokLit(middle) + TokRefSuf), maintain prefix/suffix indexes. Returns (tokens_por_string: list[list[Token]], log: str). Log contains per-string coverage %, matched IDs, etc. Byte-canonical: iterates bucket ascending ID order; tie-breaks via > strict. Complexity: O(N*B) where N=strings, B=avg bucket size; trigram index reduces from O(N^2) to O(N*B).
  params: strings_unicas (list[str]); min_len (int=3); returns (list[list[Token]], str)
  triggers: core CAMADA 1 processing; called from encoder.py unless cadence_detected and cfg.obat_shape_preserve
### [estrategia] processar_with_hint() — cadence-aware OBAT  (src/tcf/obat_shape.py:64-120)
  desc: Variant of processar() with optional shape-consistency hint. When prefer_shape_consistency=True and cadence detected, tries to replicate token structure (p_src, p_len, s_src, s_len) from previous string. Tries 3 fallbacks: (1) exact shape match (LCP/LCS exactly match), (2) wider match (reduce lengths to max available), (3) greedy fallback (use canonical _escolher_par). Returns same token structure as processar(). Motivation: columnar data often has repeating formats (fixed-width prefix, varying middle, fixed suffix like domain); hint speeds convergence. When prefer_shape_consistency=False, behaves identically to processar().
  params: strings_unicas, min_len (int=3), prefer_shape_consistency (bool); returns (list[list[Token]], str)
  triggers: CAMADA 1 processing when cadence detected (H-DA-08) and cfg.obat_shape_preserve=True
### [helper] reconstroi() — roundtrip validation  (src/tcf/core/online.py:165-176)
  desc: Reconstructs original string from token list. For TokLit: append text. For TokRefPref/Suf: resolve from strings_unicas and extract slice. Used internally for testing only; not part of encode/decode pipeline (HCC layer handles serialization). Termination guaranteed: DAG of references (j < i always).
  params: tokens (list[Token]), strings_unicas (list[str]); returns str
  triggers: never called in canonical pipeline; available for unit tests + diagnostics
### [decision-point] ColumnFeatures pre-pass  (src/tcf/column_features.py:51-84)
  desc: Unified feature extraction O(N). Computes n_rows, n_unicas, avg_len, cardinality, is_numeric (sample-based check), sample (first 20 strings). Immutable dataclass (frozen=True). Used by detect_min_len_from_features, detect_cadence_from_features. Introduced ADR-0010 / H-DA-11c (May 22) to avoid recomputing basic stats in multiple heuristics. Called unconditionally in _encode_column() even if pre_pass disabled (barato, utile for side_outputs).
  params: values (list[str]), sample_size (int=20); returns ColumnFeatures
  triggers: always at start of _encode_column(); result fed to detect_cadence and detect_min_len heuristics
### [decision-point] Greedy cover selection criterion (maximize total coverage)  (src/tcf/core/online.py:155-161)
  desc: In _escolher_par: when prefix+suffix overlap, choose candidate (pref, suf pair) maximizing pref_len + suf_len (total coverage). Tie-break: prefer candidate with max pref_len (preserves v0 behavior). Ensures middle literal always non-empty (prevents TokLit + TokRef collapse).
  params: cand_a, cand_b: (int, int, int, int) tuples (p_id, p_len, s_id, s_len)
  triggers: when bp_len + bs_len > ls in _escolher_par; triggers 2-candidate generation and comparison
### [decision-point] Tie-break rule: first occurrence wins  (src/tcf/core/online.py:108-111 (_melhor_pref), 122-125 (_melhor_suf))
  desc: When two strings have identical LCP/LCS length to current string, prefer the one with earlier insertion order (lower ID). Implemented via 'if L > best_len' (strict >, not >=). Preserves byte-canonical determinism: order of strings_unicas -> consistent token selection -> identical bytes across runs.
  params: comparison operator > (not >=)
  triggers: in _melhor_pref and _melhor_suf whenever length comparison ties
### [estrategia] Trigram index optimization (ADR-0009)  (src/tcf/core/online.py:97-112 (_melhor_pref uses prefix_index.get), 115-126 (_melhor_suf uses suffix_index.get), 184-185, 196-197, 222-223 (index maintenance))
  desc: Hash-indexed prefix/suffix bucketing reduces search from O(N) to O(B) where B=bucket size. k=3 (trigram) matches min_len=3: any valid LCP/LCS match implies matching first/last 3 chars. Bucket order = insertion order (ascending ID) preserves tie-break. Empiric speedup: 5.4x on lineitem 5k (ADR-0009 sub-exp), 1.77x in full pipeline. Byte-canonical preserved: bucket iteration ascending, comparison > strict. Memory: ~2-4MB for lineitem 5k.
  params: trigram key k=3; bucket size B varies (typically 2-100, up to 1000+ for dates)
  triggers: always in canonical OBAT; indexes built incrementally as strings processed

**NOTES**: 
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


================================================================================
## HCC (Hierarchical Compositional Coding) M8.A — Camada 2 (Compactação Composicional)
================================================================================

**CONTROL FLOW**: **Fluxo de Decisão HCC M8.A (3 Fases Sequenciais)**:

**FASE A — Tokenize (_tokenize_pieces linhas 151-221)**:
1. Input: linhas (strings com RLE), unicas (unique strings), tokens_por_string (OBAT)
2. _rle_adjacente(linhas) -> (string, count) groups
3. For each group: eid = unica_to_eid[string]
4. IF eid in eid_emitido -> is_rep=True, skip pieces emit, append line_meta(count, eid, True)
5. ELSE -> tokenize: fragments + refs herança via _coletar_quebras + quebras tracking
6. Merge 'ref' pieces consecutivos, output pieces_per_line[li] = [('lit'|'refs', ...), ...]
7. Output: pieces_per_line, line_meta, atom_count

**FASE B — Detect (_detect_compositions linhas 225-362)**:
1. WHILE TRUE (max 99 iterações):
   a. Count all K>=2 sub-tuplas em ref sequences, track sub_first_line[sub]
   b. Track alias_first_line[alias] para virtuals já em corpo
   c. Build candidates: sub com R>=2 E (0 virtuals OR (1 virtual AND (pos=0 OR alias_first_line<sub_first_line)))
   d. Compute net = (R-1)*(baseline - n_tam) para cada candidato
   e. PICK best_net > 0 (tie: Counter order)
   f. IF best is None -> STOP
   g. ELSE -> alias_temp++, alias_to_sub[alias_temp] = list(sub), substitute all sub in pieces_per_line com -alias_temp
2. Output: alias_to_sub, iter_traces

**FASE C — Emit (_emit_body linhas 391-468)**:
1. For each line_meta (count, eid, is_rep):
   a. IF is_rep -> emit `*count|^eid` (or `^eid` if count=1)
   b. ELSE:
      i. prov_to_final mapping inicializa para atoms desta linha
      ii. For each piece ('lit'|'refs'):
         - 'lit': current_id++, prov_to_final[idx]=current_id, emit _escape_lit(text) + possibly `*` separator
         - 'refs': emit _emit_ref_run(refs) com segment recursivo via _emit_alias
      iii. Track prev_lit_term_digit pra decidir `*` separator próxima piece
2. Output: body (list de linhas texto), prov_to_final, alias_to_final, ref_seqs (traced)

**Decisões-chave Detector**:
- **net > 0**: accepta candidate iff lucro > 0 (absolute)
- **virtual constraint**: rejeita se 1 virtual em pos>0 e ordem violated
- **R >= 2**: rejeita sub com <2 ocorrências
- **max 99 iterations**: safety limit
- **Greedy tie-break**: Counter insertion order (primeiro encontrado ganha, não max-multiple)

**Decisões Emit**:
- **Prev_type + prev_lit_term_digit**: decide `*` separator
- **is_rep**: ^eid vs recompile
- **Pairwise left-assoc**: chain flattening order-determinístico
- **Inline expansion**: virtuals em pos 0 garantido resolvível

**KNOBS**:
  - atom_count = proximo_idx - 1 (final atom count pós-Fase A)
  - comp_acc_k (composição IDs acumulados, incrementa len(sub)-1 per alias)
  - next_alias (temp ID sequencial, inicia 1)
  - max_iterations = 99 (detector Fase B limit)
  - min_R = 2 (mínimo ocorrências)
  - min_K_range = 3 (range threshold)
  - virtual_count <= 1 (máximo 1 por sub)
  - n_est = len(str(atom_count+comp_acc_k+1)) (num width estimator)
  - virtual_estimate = '9'*n_est (pessimista baseline)
  - escape_chars = {*, \, ~, 0-9}
  - separator_char = *
  - range_separator = ..
  - ref_concat_ephemeral = ,
  - ref_concat_compositional = ~
  - rle_marker_syntax = *N|resto
  - seq_rle_syntax = *N+delta|template (ADR-0016)
  - max_seq_rle_nonzero = 1 (Fase 1 limit)
  - utf8_encoding = true
  - lf_only_canonical = true

**EXTENSION POINTS (v2.0 hooks)**:
  - **Novos marcadores léxicos** (v2.0): adicionar em _emit_body + decoder _parse_decl
  - **Dicionário pré-computado**: substitui detector greedy por lookup hash (opt-in)
  - **Lossy compactação**: novo operador (~L) ou flag em alias_to_sub
  - **Ordenação alternativa**: knob order_strategy (net|freq|hybrid) em linha ~300
  - **Patricia trie**: substituir Counter+scan por trie (sem sintaxe mudança)
  - **Header carry spec_id**: adiciona spec_id em header (coordena natures)
  - **Fallback mechanism**: *FALLBACK|literal pra valores incompressíveis
  - **K-way restrição**: knob max_K_per_candidate (default unlimited)

**STRATEGIES** (24):

### [marcador] Atomic refs  (src/tcf/composicional/syntax.py:3-5, 26-28)
  desc: IDs positivos (1,2,3,...) que representam strings atômicas (literais ou tokens OBAT). Allocados sequencialmente durante tokenização da Fase A. Cada átomo recebe um prov_id (provisional) durante _tokenize_pieces, depois remapeado para final_id durante _emit_body. Coexistem no mesmo espaço de refs com referências virtuais.
  params: prov_id >= 1; final_id alocado durante emit interleaved; _runs_pos() agrupa consecutivos para compressão com ranges
  triggers: sempre; alocados na Fase A para cada piece ('lit' ou fragmento ref herdado)
### [marcador] Virtual refs (aliases)  (src/tcf/composicional/syntax.py:3-5, 223-362)
  desc: IDs negativos (-1,-2,...) que representam composições detectadas. Um -alias_temp refere alias_to_sub[alias_temp], lista de elems (positivos atoms ou negativos inner aliases). Emitidos como cadeias composicionais no body. Estratégia unificada: detector vê atoms + virtuals na mesma fila, permitindo pares como (atom_X, composição_anterior).
  params: virtual_id = -alias_temp; alias_temp starts at 1, incrementa em _detect_compositions; alias_to_sub maps temp -> list de refs mixtos
  triggers: Fase B: em iterações greedy quando sub-tupla R>=2 e net>0; Fase C: emissão inline com pairwise left-assoc
### [filtro] Detector greedy (Fase B)  (src/tcf/composicional/syntax.py:225-362)
  desc: Itera até convergência (max 99 iterations linha 359). A cada iteração: (1) conta sub-tuplas K>=2 em ref sequences; (2) computa net = (R-1)*(baseline_chars - num_len) onde baseline=emit length sem composição, num_len=len(str(N)) p/ ID novo; (3) filtra candidatos net>0 + constraints (virtuais em pos 0 OU alias_first_line < sub_first_line); (4) pick argmax(net); (5) substitui todas ocorrências de best.sub por alias novo. Interrompe quando best=None.
  params: R >= 2 (mínimo 2 ocorrências); net > 0 (threshold lucro); max_iterations = 99; virtual_count <= 1 (no máximo 1 virtual per sub); body-order check se virtual em pos>0
  triggers: Sempre na Fase B após tokenização; continua enquanto houver candidato com net>0
### [threshold] Net gain criterion  (src/tcf/composicional/syntax.py:288-302)
  desc: Heurística central do detector: net = (R-1) * (baseline - n_tam), onde R=ocorrências, baseline=chars se emitido `,`-separado inline, n_tam=len(str(próx_id)). Positivo = lucro em bytes se criar novo ref. Negativo/zero = descarta. Tie-break: Counter order (primeiro encontrado ganha). Estimativa de baseline em _estimate_baseline_chars monta ranges L>=3 e estima ~2 digits por virtual.
  params: baseline > 0; n_tam = len(str(atom_count + comp_acc_k + K - 1)); lucro absoluto = (R-1) * (baseline - n_tam); min_R=2
  triggers: Em toda iteração; cada candidato avaliado, melhor fica no 'best'
### [filtro] Body-order constraint (inline expansion correctness)  (src/tcf/composicional/syntax.py:267-287, 495-541)
  desc: Quando um sub contém virtual -Y em posição >0, filtra se alias_first_line[Y] >= sub_first_line[sub]. Sem isso, inline expansion falharia: ao emitir def de sub, Y ainda não resolvido. Com constraint garantido, pairwise left-assoc de Y já tem final_id. Decisão acontece em _detect_compositions; emissão em _emit_alias com expand() recursivo.
  params: virt_pos = índice do virtual em sub (0-based); virt_alias = -sub[virt_pos]; alias_first_line[virt_alias] must exist before sub_first_line[sub]
  triggers: Na detecção, quando virtual_count==1 e virt_pos>0; rejeita candidato se violado
### [helper] Escape mechanism (_escape_lit)  (src/tcf/composicional/syntax.py:52-73)
  desc: Prefixo `\` (backslash) escapa chars reservados: `*` (RLE marker), `\` (escape self), `~` (compositor), dígitos (ref start). Lógica: iterator por char; se digit, coleta run contígua e prefixo com `\`; se `*`/`\`/`~`, single char escape. Retorna (text_escaped, prev_lit_term_digit) onde bool indica se último char é digit (usado pra decidir `*` separator próxima piece).
  params: chars escapados: {*, \, ~, 0-9}; escape_char = \; nenhuma normalização de CRLF
  triggers: Em toda literal 'lit' piece durante _emit_body (linha 445)
### [heuristica] Range compression (M1.E syntax)  (src/tcf/composicional/syntax.py:91-101, 104-114)
  desc: Runs de refs consecutivos length>=3 emitidos como `A..B` range em vez de `A~A+1~...~B`. Em _emit_refs_range: groups by _runs_pos, cada run L>=3 vira `start..end`, else individual. Joined por `,` (concat efêmero). Em _emit_composition: analoga mas joined por `~` (compositor). Decoder inverte ranges via range(int(a), int(b)+1).
  params: L >= 3 threshold pra range (linha 97, 110); consecutive check: next == prev+1; delimiter: `,` em refs, `~` em composition
  triggers: Sempre em emit, quando há >=2 consecutivos em run
### [marcador] RLE marker: *N|linha  (src/tcf/composicional/syntax.py:416, 462-463, 748-759)
  desc: Formato `*N|resto` onde N=count inteiro, resto=body linha. Representa N repetições idênticas de mesma string única. Encode: agrupado em _rle_adjacente (linhas consecutivas idênticas), eid emitido; se eid já visto, emite `*count|^eid`. Decode: split `*` e `|`, parse count, emite resto N vezes. Compatível com seq-RLE (ADR-0016).
  params: count >= 1; 'resto' = linha body ou `^eid` se repetição de ja-decodificado
  triggers: Sempre em emit quando count>1 (linha 415, 462)
### [marcador] RLE reference: ^eid  (src/tcf/composicional/syntax.py:416-418, 754-755)
  desc: Sintaxe `^N` onde N=eid (elemento id 1-based da lista decodificada anterior). Emitido quando linha repeats de string única ja decodificada previamente em diferente grupo RLE não-consecutivo. Decode: busca nos_decl[eid-1], append N vezes. Bug fix 2026-05-15: `^eid` + count agora emite `*count|^eid` pra preservar repetições em grupos separados (linha 415-418).
  params: eid >= 1; eid in [1..len(nos_decl)]
  triggers: Quando is_rep=True em line_meta (eid ja emitido antes)
### [marcador] Seq-RLE marker: *N+delta|template (ADR-0016)  (src/tcf/composicional/hcc_seqrle.py:150-228, 230-274)
  desc: Format `*N+delta|template` ou `*N+d1,d2,...|template`. Post-process em compact_body: detecta runs near-identical (mesmo length, escape-digit runs em mesmas posições, diffs apenas dentro runs). Single delta uniform: emite `*N+delta|` (M10 compat). Multi-delta (ADR-0016 Fase 1): `*N+d1,d2,d3,...|template` (CSV per-run se 1 único non-zero + zeros). Decoder expand_seq_marker: difere pelo `+` vs puro RLE `*N|`, shifta escape-digits por delta(s).
  params: delta: int (uniform) OR list[int] (per-run); restrict Fase 1: máximo 1 non-zero em lista; escape-digit runs identificados por find_escape_digit_runs()
  triggers: Post-encode em HCCSeqRLE.encode, após super().encode; detecta em decode se `*...+` pattern presente
### [marcador] Comma separator (ref concat ephemeral)  (src/tcf/composicional/syntax.py:92-102, 451, 673-681, 685)
  desc: Delimitador `,` une refs/ranges em single line sem criar novo ref. Sintaxe: `1,2,3` (refs atom), `1..5,10,15` (ranges+atoms), `1~2,3~4` (compositions). Emit em _emit_ref_run linha 493. Decode em _parse_decl: split por `,` antes de processar cada unit (que pode ter `~` ou `..'). Múltiplas refs=múltiplas pieces emitem `,` between (linha 451). BUG FIX ADR-0007: lit começando com `,` após refs requer `*` separator pra não ser consumido como ref continuation.
  params: sempre between unidades ref; split character em decoder
  triggers: Entre two 'refs' pieces, ou dentro run de refs atoms/compositions
### [marcador] Tilde compositor (ref concat compositional)  (src/tcf/composicional/syntax.py:104-114, 113, 435, 678, 685)
  desc: Delimitador `~` une refs E cria novo ref nomeado via pairwise left-assoc. Sintaxe: `1~2~3` emite seq de intermediários. Em decoder: refs [1,2,3] -> pairwise concat ID-1=(1+2), ID-2=(ID-1+3), exporta ID-2. Emit em _emit_composition (composition def) vs _emit_refs_range (atoms). BUG FIX ADR-0007: lit começando com `~` após refs requer `*` separator.
  params: sempre em pairwise; cada pair aloca 1 ID intermediário; K refs = K-1 IDs
  triggers: Em _emit_composition quando chain de refs em alias definition
### [token-type] Dot-dot range (syntactic sugar)  (src/tcf/composicional/syntax.py:91-101, 104-114, 674-676, 686-688)
  desc: Syntax `A..B` shorthand para range [A, A+1, ..., B] de refs consecutivos. Encoder usa quando L>=3 consecutivos (linha 97, 110). Decoder recognizes `..` pattern (linha 675-676) e expanda via range(int(a), int(b)+1) (linha 688). Case particular de _emit_composition/refs_range.
  params: A, B inteiros >= 1; B >= A; no spaces; apenas em grupos >=3 consecutivos
  triggers: Em _runs_pos identificação de consecutivos
### [marcador] Literal separator `*` (lit-lit ou boundary)  (src/tcf/composicional/syntax.py:433-442, 450-453, 667-668, 720)
  desc: Single `*` sem count/pipe emitido: (1) entre duas 'lit' pieces sucessivas (linha 434), (2) após refs->lit se lit começa com `,` ou `~` (ADR-0007 bug fix linha 435-442), (3) após lit com digit final->refs (linha 453). Decoder: skip quando em ref mode (linha 667-668, 720-breaking conditions). Função: desambiguação limites lit/ref pra parser single-pass.
  params: single `*` sem sufixo
  triggers: Sempre em lit-lit boundary ou ambiguous lit start
### [decision-point] Pairwise left-associativity (emit strategy)  (src/tcf/composicional/syntax.py:495-541, 529-538)
  desc: Quando emitir alias definition (chain de K elementos), aloca K-1 IDs por pairwise expansion: ID_1 = elem0 + elem1, ID_2 = ID_1 + elem2, ..., ID_{K-1} = ID_{K-2} + elemK. Em _emit_alias, build linear chain via expand() recursivo, depois aloca IDs by pairwise position: alias_to_final[ali] = base + idx (idx=índice no chain linear, idx>=1). Garante correctness de inline expansion com virtual refs (constraint body-order).
  params: base = current_id antes allocation; idx = position no linear chain; K = len(linear)
  triggers: Em toda primeira emissão de alias (linha 507)
### [decision-point] Inline expansion (virtual resolution)  (src/tcf/composicional/syntax.py:495-541)
  desc: Quando emitir virtual ref, resolve recursivamente: se já emitido (final_id em state), emit bare ID; senão, flatten sub recursivamente (expand inner aliases em order), aloca K-1 IDs pairwise, atribui finals. Completions tracking (list de (linear_idx, alias)) registra onde cada alias resolva no chain. Permite composition of compositions.
  params: recursão em expand() lexical; base ID allocation durante linear build; completions resolve in order
  triggers: Em _emit_alias primeira execução, ou em _emit_ref_run quando refs[i]<0
### [decision-point] Body-order ID assignment (interleaved atoms+compositions)  (src/tcf/composicional/syntax.py:391-468)
  desc: Single-pass emit: current_id increments sequencialmente enquanto percorre pieces (lit/refs). Atoms = +1 per piece (linha 443). Compositions = +K-1 (K=chain length, linha 532). Permite decoder single-pass sem preâmbulo: IDs assignados na ordem parse body.
  params: current_id starts at 0 (linha 399); incrementa atomicamente por operação emit
  triggers: Durante todo _emit_body
### [decision-point] Prev_lit_term_digit tracking  (src/tcf/composicional/syntax.py:425, 445, 452-453, 458)
  desc: Booleano mantém se última literal emitida termina em digit (via _escape_lit retorno). Usado pra decidir: se prev_lit_term_digit AND próx é 'refs' -> emit `*` separator (linha 452-453) pra evitar parser confundir `abcd1,2` como `abcd` + `1,2` com count. ADR-0007 mitigation.
  params: boolean; resetado a False exceto em 'lit' pieces
  triggers: Após _escape_lit em 'lit' pieces
### [helper] Fragment tracking (_tokenize_pieces)  (src/tcf/composicional/syntax.py:151-221)
  desc: Fase A: quebra strings em fragments (pedaços de literal/ref). frags_por_no[eid] = lista (a,b,idx) onde [a:b] é substring e idx é fragment_id. quebras[eid] = set de boundary positions (onde refs terminam). Base em OBAT tokens: TokLit -> literal fragment; TokRefPref/TokRefSuf -> herança de fragments anteriores (com ajuste de posição). Permite reuse de fragments atomizados.
  params: proximo_idx starts at 1, incrementa per fragment; eid=element id (1-based); (a,b,idx) tuples stored in order
  triggers: Em _tokenize_pieces, uma vez pra cada string única
### [helper] RLE adjacency grouping (_rle_adjacente)  (src/tcf/composicional/syntax.py:42-50)
  desc: Pré-processa linhas: agrupa strings iguais consecutivas em (string, count). Input: [a,a,b,b,b,a] -> output: [(a,2), (b,3), (a,1)]. Usado em _tokenize_pieces pra detectar runs e decidir is_rep (já emitido antes).
  params: ordem preservada; apenas run consecutivos agrupados
  triggers: Início de _tokenize_pieces
### [categoria] Piece structure (lit vs refs)  (src/tcf/composicional/syntax.py:152, 204-217)
  desc: Fase A output: pieces_per_line[li] = list de ('lit', text, idx) ou ('refs', [ids]). 'lit': literal text + fragment_id. 'refs': sequence de refs (atoms/virtuals positivo/negativo). Consecutivos 'ref' pieces merged em um 'refs' tuple com lista unificada. Ordem preservada per line.
  params: pieces = [('lit'|'refs', ...), ...]; refs list tem mixed signs
  triggers: Saída de _tokenize_pieces
### [decision-point] RLE hit detection (is_rep)  (src/tcf/composicional/syntax.py:163-166, 407-420)
  desc: Se string única já decodificada em grupo RLE anterior (eid_emitido set), marca is_rep=True. Emit usa ^eid reference em vez de recompilar. Preserva bytes quando repetição em grupos não-consecutivos (bug fix 2026-05-15).
  params: eid_emitido = set de eids já vistos; is_rep boolean por line_meta
  triggers: Durante _tokenize_pieces quando iterando _rle_adjacente
### [heuristica] Estimator de baseline (_estimate_baseline_chars)  (src/tcf/composicional/syntax.py:364-387)
  desc: Estima chars de emit `,`-separado de sub (misto atom/virtual) SEM criar nova composition. Para atoms: emit ranges se L>=3. Para virtuals: assume ~2 digits (estimador pessimista). Retorna len(','.join(parts)). Usado no net computation (baseline parameter).
  params: n_est = len(str(atom_count+comp_acc_k+1)); virtual estimate = '9'*n_est
  triggers: Em _detect_compositions pra cada candidato
### [marcador] Sub-first-line e alias-first-line tracking  (src/tcf/composicional/syntax.py:239-264, 284-287)
  desc: sub_first_line[sub] = first line index onde sub aparece como candidato. alias_first_line[alias] = first line onde alias (negativo id) aparece em body. Usado em body-order constraint: se sub tem virtual em pos>0, require alias_first_line[virt] < sub_first_line[sub].
  params: 0-based indices; initially empty dicts, populated em scanning
  triggers: Em toda iteração detector, antes candidato filtering

**NOTES**: **CATALOGAÇÃO EXAUSTIVA — HCC M8.A CAMADA 2**

**Status Canonical & Welding**:
- Código base intocado desde 2026-05-16 em dirty lab
- Welded src/tcf 2026-05-17, Bug fixes: ADR-0006, ADR-0007, ADR-0015, ADR-0016
- Format frozen v1.0 via ADR-0017: #TCF.6 imutável até v2.0; D1-D9=1523B, D17a=322B

**Caracteres Especiais Completo**:
`*` (RLE/separator), `\\` (escape), `~` (compositor), `,` (concat-ephemeral), `..` (range), `^` (ref-anterior), `+` (seq-RLE delta), `|` (delimiter), `0-9` (IDs). Nenhum outro especial.

**Refs Atômicos vs Virtuais**:
- **Unificação M8.A**: espaço único [atoms(+), virtuals(-)] permite detector capturar pares (atom_prev, composition_last) que M7.A perderia
- **Pairwise left-assoc**: ID_i = ID_{i-1} + elem_i garante correctness inline expansion via body-order constraint

**Detector Greedy**:
- Iterativo até convergência (max 99), net = (R-1)*(baseline - n_tam), tie-break Counter order
- R>=2 obrigatório, virtual_count<=1, body-order check se virtual em pos>0
- Greedy: não tree-based, não online, pick argmax(net) cada iteração

**Escape Mechanism**:
- `\\` prefixo para digit-runs + chars {*, \\, ~}
- Tracking prev_lit_term_digit decide `*` separator (ADR-0007 mitigation, não escape `,`)
- Decoder _parse_decl reconhecer `\\` + ranges

**Seq-RLE (ADR-0016)**:
- Post-process: detect near-identical, `*N+delta|` (M10 compat) ou `*N+d1,d2,...|` (Fase 1 multi-delta)
- Restrict: máximo 1 non-zero per-run em multi-delta
- Decoder: disambigua `+` pattern, shifta escape-digits

**Fluxo Camadas Funis**:
- CAMADA 0: natures pre-tx opt-in
- CAMADA 1: OBAT tokenização
- CAMADA 2: HCC greedy + Seq-RLE post-process
- CAMADA 3: Multi-col wrapper

Owner context: estudar EXAUSTIVAMENTE TODAS estratégias ANTES explorar v2.0 (dict, lossy, sort, Patricia). Catalogo COMPLETO current.

================================================================================
## CAMADA 2b — HCC seq-RLE + multi-delta (ADR-0016, welded canonical)
================================================================================

**CONTROL FLOW**: ENCODE: values → analyze_column (pre-pass, opcional) → detect_cadence → detect_min_len → OBAT tokenizes (processar ou processar_with_hint) → M8AVirtualRefsSyntax.encode() genera body_text (M9 puro, com refs/compositions) → HCCSeqRLE.encode() aplica compact_body (post-process seq-RLE) → output TCF.

DECODE: tcf_text → HCCSeqRLE.decode() expande seq-RLE markers (expand_seq_marker) → re-assembles text → M8AVirtualRefsSyntax.decode() (parent class) descodifica refs/compositions → output list[str] original.

MARKER DECISION LOGIC em compact_body:
1. detect_seq_runs identifica runs near-identical
2. Para cada run, checa _is_uniform_delta(deltas)
3. Se uniform (todos deltas = mesmo valor non-zero) → marker M10 format `*N+delta|template`
4. Senão (multi-delta com 1 non-zero, resto zeros) → marker CSV format `*N+d1,d2,d3|template`
5. Assemble output compacted + info metadata

Em decode, marker parser disambiguates automaticamente: ',' na delta_str → CSV (ADR-0016), senão int (M10).

**KNOBS**:
  - Fase 1 single non-zero restriction: compare_for_seq linha 110 hard-rejects multiple different non-zero. Futuro: Fase 2 removeria essa linha, permitindo [1,2,3] etc.
  - Overflow width handling: shift_escape_digits linha 142 zfill(width) — se new_val > width, não trunca. Config futuro: truncate_overflow flag (atualmente sempre preserve).
  - Run equality check (structural): compare_for_seq linha 90 requer runs_a == runs_b exatamente. Futuro: relaxar pra 'estruturalmente compatível' (ex: runs adicionales com zero offset).
  - M10 marker format decision: _is_uniform_delta linha 181 threshold 'all(d == deltas[0] and d != 0)'. Knob: se mudar pra all(d == deltas[0]) (aceitar uniform-zero), quebraria backward compat.
  - Escape sequence detector: find_escape_digit_runs detecta '\ seguido de isdigit(). Hardcoded: não detecta hex (\\xFF) ou octal (\\123). Futuro: extensivel pra outros bases.
  - Marker savings estimate: compact_body linha 219 = sum(original line lengths) - len(marker). Não inclui header/footer overhead de markers. Config: tunable multiplier pra prefer/avoid compaction (atualmente 1x).

**EXTENSION POINTS (v2.0 hooks)**:
  - Fase 2 multi-delta support: remover linha 110-111 reject em compare_for_seq. Permitiria [1,2] ou [1,2,3]. Impacto: marker formato ainda CSV `*N+d1,d2,d3|`, parser identico. Decoder não muda. Test suite: atualizar test_hcc_multi_delta.py:49-53 (atualmente xfail 'multiple_non_zero').
  - Parametrico run-matching: generalizar find_escape_digit_runs pra aceitar outros patterns (hex \xFF, octal \123, ou custom regex). Extensão: adicionar 'run_detector' callback em HCCSeqRLE.__init__, used em place of hardcoded find_escape_digit_runs.
  - Overflow handling strategies: adicionar knob 'overflow_mode' em HCCSeqRLE: 'preserve' (atual), 'truncate' (modulo width), ou 'reject' (skip run se overflow). Afeta shift_escape_digits linha 138-147.
  - Per-run compaction cost threshold: atualmente todos runs compactados se detectados. Futura: threshold 'min_savings' em compact_body pra rejeitar runs que economizam < K bytes. Usado em 'near-identical mas não suficientemente repetido'.
  - Multi-delta variant strategies: ADR-0016 Fase 1 usa CSV `d1,d2,d3` simples. Futuro Fase 2: (a) bitmask format `*N+*00*1|` (markers pra runs que variam), (b) delta-of-delta `*N+0,+1,-1,+2|` (compacta patterns tipo alternating), (c) base+perturb `*N+base=1,deltas=[0,0,1,2]|` (separado offset global).
  - Marker syntax evolution: atualmente `*N+deltas|template`. Futuro: optional repeat-hint `*N:3+deltas|` (já know run repeats 3x, hint pra decoder), ou compressed template se muito grande.
  - Integration com pré-processamento: HCCSeqRLE atualmente post-process puro (sem info de OBAT tokens). Futuro: token-aware seq-RLE — se sabemos que 2 tokens diferem apenas em 1 run, priorize essa compactação.
  - Partial run detection: atualmente rejeita runs diferentes. Futuro: 'suffix-only' mode — compacta se last N runs matching, ignore prefix differences (ex: timestamp prefix + counter suffix).
  - Streaming variant: HCCSeqRLE atualmente batcher (full body_lines in memory). Futuro: stream mode pra large datasets — detecta runs incrementally, emits markers on-the-fly.

**STRATEGIES** (14):

### [helper] find_escape_digit_positions  (src/tcf/composicional/hcc_seqrle.py:31-44)
  desc: Utility que mapeia posições (0-based) de cada char digit que vem após backslash (escape sequence). Itera string left-to-right, detecta '\' seguido de isdigit(), coleta indice de cada digit. Retorna lista vazia se nenhuma sequence escape-digit encontrada. Usado por find_escape_digit_runs e compare_for_seq pra localizar quais portions do template são 'numéricos' (candidatos a delta shift).
  params: line: str → list[int]
  triggers: sempre, quando precisa-se mapear estrutura escape-digit de uma linha
### [estrategia] find_escape_digit_runs  (src/tcf/composicional/hcc_seqrle.py:47-62)
  desc: Detecta RUNS (intervalos consecutivos) de digits após escape. Retorna list[tuple[int, int]] (start, end_exclusive) de cada run. Ex: '\\125.\\114' → [(1,4), (6,9)]. Crítico pra distinguir multi-run (prefix invariante + suffix cadenced) de single-run. Usado como pivô em compare_for_seq pra rejeitar pares com estruturas runs diferentes.
  params: line: str → list[tuple[int, int]]
  triggers: sempre, pré-requisito pra compare_for_seq
### [decision-point] compare_for_seq  (src/tcf/composicional/hcc_seqrle.py:65-112)
  desc: CRITERIO CENTRAL pra near-identical detection. Compara line_a e line_b; retorna list[int] de deltas (1 per run) se par é compactavel, None senão. Aceita: (1) single run com delta non-zero, (2) multi-run com EXATAMENTE 1 valor non-zero + resto zeros (ex: [0,0,0,1]). Rejeita: (1) len diferente, (2) diffs fora de escape-digit runs, (3) runs_a ≠ runs_b (estrutura diferente), (4) multiple non-zero diferentes (Fase 2 reject, linha 111), (5) all-zero (linhas identicas). ADR-0016: mudança chave vs M10 — agora aceita multi-delta [0,0,0,1] que antes rejeitava (Bug #2).
  params: line_a: str, line_b: str → list[int] | None
  triggers: em detect_seq_runs: testado entre cada par consecutivo de linhas no body
### [heuristica] _is_uniform_delta  (src/tcf/composicional/hcc_seqrle.py:176-183)
  desc: Verifica se lista de deltas é UNIFORME (todos iguais e non-zero). Se sim, retorna aquele int único; senão None. Usado em compact_body (linha 199) pra decidir marker format: M10 compat `*N+delta|` (uniform) vs ADR-0016 CSV `*N+d1,d2,d3,d4|` (mixed). Threshold: all(d == deltas[0] and d != 0). Importante pra backward compatibility.
  params: deltas: list[int] → int | None
  triggers: em compact_body, depois de detectar run near-identical
### [estrategia] shift_escape_digits  (src/tcf/composicional/hcc_seqrle.py:115-147)
  desc: Aplica delta(s) a template pra gerar linha i+1, i+2, ... em run. Aceita delta como int (M10: mesmo delta em TODOS runs) ou list[int] (ADR-0016: per-run). Algorithm: (1) parse runs do template, (2) normalize delta pra list, (3) iterate runs + deltas em sync, (4) apply int(run_old) + d → new_val, (5) format com zfill(width) pra preservar leading zeros. Edge case: se len(deltas) ≠ len(runs), retorna template inalterado (safe fallback). Linha 142: zfill preserva 3-digit de IPs ex: '\\001' ∈ run → +1 → '\\002'.
  params: template: str, delta: int | list[int] → str
  triggers: em expand_seq_marker (linha 272), por vez em cada iteração do loop count
### [estrategia] detect_seq_runs  (src/tcf/composicional/hcc_seqrle.py:150-173)
  desc: DETECTOR SEQUENCIAL de runs near-identical. Itera body_lines, chama compare_for_seq em cada par consecutivo. Quando par aceitável, estende run enquanto proxima line mantém MESMO deltas. Retorna list[tuple[int, int, list[int]]] = (start_line, end_exclusive, deltas). Invariante: runs não se sobrepõem, sequential. Usado em compact_body. ADR-0016: deltas sempre list[int] (retorno de compare_for_seq mudou de int → list). Threshold pra extend run (linha 168): next_deltas == deltas (exato, não aproximado).
  params: body_lines: list[str] → list[tuple[int, int, list[int]]]
  triggers: em compact_body:187, depois de OBAT encode pra processar body lines
### [estrategia] compact_body  (src/tcf/composicional/hcc_seqrle.py:186-227)
  desc: POST-PROCESS pós-encode. Detecta runs near-identical, substitui por markers. Decide marker format (M10 vs CSV): linha 199-210. Se uniform delta → M10 format `*count+delta|template` (compat). Senão → CSV `*count+d1,d2,...|template` (ADR-0016). Sign handling (linha 201, 209): prepend '+' apenas se delta[0] >= 0; negativo já inclui '-' via str(). Retorna (compacted_lines, info_dicts). Info dict inclui savings estimate (linha 219-220) = (sum(len original lines) + count-1) - len(marker). Invariante: cada marker ≥ 2 linhas (count >= 2).
  params: body_lines: list[str] → tuple[list[str], list[dict]]
  triggers: em HCCSeqRLE.encode, pós-super().encode
### [estrategia] expand_seq_marker  (src/tcf/composicional/hcc_seqrle.py:230-274)
  desc: DECODER REVERSO de markers. Parse `*N+delta|template` ou `*N+d1,d2,...|template`. Disambiguação (linha 255): if ',' in delta_str → CSV (ADR-0016) senão int (M10). Extracts count, deltas, template. Itera count vezes, aplicando shift_escape_digits incrementalmente. Linha 264: int(delta_str) parse single delta (compat M10). Linha 257: split(',') → list[int]. Returns list[str] de count linhas (template + shifted variantes), ou None se formato inválido.
  params: linha: str → list[str] | None
  triggers: em HCCSeqRLE.decode, para cada linha que comeca com '*'
### [estrategia] HCCSeqRLE class + control flow  (src/tcf/composicional/hcc_seqrle.py:277-314)
  desc: Subclass de M8AVirtualRefsSyntax. Override encode/decode pra adicionar seq-RLE layer. ENCODE (linha 293-298): (1) chama super().encode → body_text (M9 canonical), (2) split em lines, (3) compact_body, (4) armazena seq_rle_info em _seq_info, (5) retorna compacted text. DECODE (linha 300-313): (1) itera tcf_text.splitlines(), (2) pra cada linha, tenta expand_seq_marker, (3) se marker → adiciona expanded lines, senão passes-through, (4) re-assembles texto expandido, (5) chama super().decode. Post-condition: bytes-exato round-trip (encode → decode == original).
  params: none (class instancia)
  triggers: em encoder.py e decoder.py, sempre que cfg.hcc_seq_rle=True (default)
### [threshold] M10 backward compatibility threshold  (src/tcf/composicional/hcc_seqrle.py:199-202)
  desc: Mecanismo de preservação backward compat: se _is_uniform_delta retorna non-None (todos deltas iguais), emite marker M10 format `*N+delta|` (sem virgula). Datasets como D1-D9 (nenhum multi-run com mixed deltas) emit markers idênticos a versão M9, preservando byte-canonical invariant. Validado em test suite (19 novos tests em test_hcc_multi_delta.py, 211 total passam).
  params: none (condicional hardcoded)
  triggers: sempre em compact_body, escolhe formato marker M10 vs CSV
### [threshold] Fase 1 single non-zero restriction  (src/tcf/composicional/hcc_seqrle.py:107-111)
  desc: ADR-0016 Fase 1 limitação: multi-delta só aceita 1 valor non-zero (resto zeros). Linha 110: if len(set(non_zero)) > 1 → return None (reject). Casos [1,2] ou [3,5] rejeitados — defer para Fase 2 (futuro). Justificativa: casos [0,0,0,1] são comuns (prefix invariante + suffix cadenced, ex: IPs), mas [1,2] raro em real-world datasets. Benchmark D-IP-subnet validou suficiência.
  params: none (hardcoded check)
  triggers: em compare_for_seq:110, sempre ao validar multi-run
### [marcador] Run equality invariant  (src/tcf/composicional/hcc_seqrle.py:88-91)
  desc: Estrutural: pares são aceitáveis APENAS se runs_a == runs_b (posições de escape-digit runs exatamente iguais). Se differs → None (reject). Impede false positives tipo '\\1' vs '\\1.\\2' (número de runs diferente, diferença não-linear). Crítico pra corretude shift_escape_digits.
  params: none (structural check)
  triggers: em compare_for_seq:90, sempre
### [threshold] Escape-digit length check  (src/tcf/composicional/hcc_seqrle.py:138-144)
  desc: shift_escape_digits linha 141-144: quando aplicar delta a run, resultado new_val pode ter length diferente de original (ex: 99 + 1 = 100). zfill(width) preserva width (leading zeros); se new_str > width, não trunca (overflow preservado). Exemplo: \\99 + 1 → \\100 (width muda de 2 → 3). Necessario pra IPs com 3 dígits fixos.
  params: width: int (end - start de run)
  triggers: em shift_escape_digits:142, por run shifta
### [decision-point] Tokenizer OBAT integration point  (src/tcf/composicional/hcc_seqrle.py:1-24 (docstring))
  desc: HCCSeqRLE é post-process em cima de OBAT tokenization (CAMADA 1) + M8A atom/composition detection (CAMADA 2a). Entrada é body_text já escape-lido (escape-digit runs via OBAT _escape_lit). Saída é compactação seq-RLE. Pipeline: OBAT tokeniza → M8A emits refs → body_text → HCCSeqRLE compacts → output TCF. Camadas são sequencial, não intercalado.
  params: none (architectural)
  triggers: em encoder.py:293-298, sempre no pipeline canonical

**NOTES**: CANONICAL STATE (v1.0 welded 2026-05-24):
- M10 backward compatibility CRITICAL: D1-D9 datasets output byte-exato (211 tests pass, 322B D17a invariant preserved).
- ADR-0016 multi-delta Fase 1: single non-zero restrição suficiente pra D-IP-subnet real-world. Bug #2 fix resultou em -96.4% compression ratio vs pre-fix em 1000-IP test (15747B → 560B).
- Marker format: M10 `*N+delta|` (compat, used em 99% de cases históricos) vs CSV `*N+d1,d2,d3|` (novo, opt-in quando multi-run mixed-delta detected).
- Parser unificado: expand_seq_marker disambiguates automaticamente via ',' in delta_str.

FASE 2 PLANNING (deferred):
- Remove single non-zero restriction, allow [1,2], [1,2,3] etc.
- Parametrizável run detectors (hex, octal, custom).
- Per-run compaction cost thresholds.
- Streaming variant pra big datasets.

BUG FIXES WELDED:
- Bug #1 (T-CODE-HCC-ATOM-DETECTION-REFINE): deferred — seq-RLE multi-delta coverage já suficiente.
- Bug #2 (T-CODE-HCC-MULTI-DELTA-FIX): accepted + welded (este ADR-0016). compare_for_seq linha 88-91 now accepts [0,0,0,1].

MEASUREMENTS (real-world):
- D-IP-subnet 1000 sem nature: 15747B (117%) → 560B (4.18%), -96.4% reduction.
- vs SPEC_IP nature (ADR-0015): 229B (1.71%) — SPEC_IP still wins -59% vs seq-RLE, mas ambos disponiveis (user choice).
- D1-D9 baseline: 1523B invariant preserved (M10 compat).

KNOWN LIMITATIONS (not limitations, by design for v1.0):
- Fase 1: only 1 non-zero delta (multi-delta [1,2] rejected). Sufficient pra cadenced data (prefix invariante + suffix incrementing, comum em IPs/timestamps).
- No overflow truncation (zfill preserves). If \99 + 1 → \100 (width changes), not truncated — correct pra IPs mas pode surprise users expecting fixed width.
- Escape-digit detector hardcoded (\\ + isdigit). Not extensible in v1.0, but well-documented.

ROUND-TRIP GUARANTEES:
- encode(X) → compact_body → output TCF
- decode(TCF) → expand_seq_marker → super().decode → X (byte-exact, tested in test_hcc_multi_delta.py:170-182)
- CRITICAL: expand_seq_marker line 268-274 applies shift_escape_digits in sequence (curr becomes template after each iteration), correctly rebuilding incremental deltas.

================================================================================
## CAMADA 0-pre (Naturezas — Pre-transform opt-in per VALOR)
================================================================================

**CONTROL FLOW**: 
1. **Encoder pipeline com nature** (encode com nature param):
   - Caller: encode(values, nature=SPEC_X) [list] ou encode(dict, nature_per_col={name: SPEC_X}) [dict]
   - Dispatcher (encoder.py:96-114): detecta tipo, aplica encode_value(spec, v) em cada valor → lista pré-transformada
   - Result: valores comprimidos ('5 chars base94' ou '12 dígitos padded') ou fallback ('_' + original)
   - Flow: pre-tx CAMADA 0 → analyze_column → detect_cadence → detect_min_len → OBAT → HCC
   
2. **Decoder pipeline com nature** (decode com nature param):
   - Caller: decode(text, nature=SPEC_X) [single] ou decode(text, nature_per_col={name: SPEC_X}) [multi]
   - Dispatcher (decoder.py:52-91): detecta shebang, decodifica HCC → list[str], aplica decode_value(spec, v) em cada
   - Flow: HCC decode → reverse pre-tx CAMADA 0 (strip marker ou regenerar formato original)
   
3. **classify_value flow** (diagnostic path):
   - Caller: classify_value(spec, v) [explicit] ou chamado internamente por encode_value
   - Decision points: TemplatedCheckedSpec (lines 66-81) ou TemplatedPaddedSpec (lines 63-84)
   - Result: enum string ('compressible', 'check_invalid', 'format_mismatch', 'format_unmasked', 'empty_value', 'length_wrong', 'range_invalid', 'format_padded_zeros')
   - Usado: (a) no encode_value para determinar path (compressible vs fallback), (b) explicitamente pra diagnostico via API publica
   
4. **Pre-pass heuristics flow** (sem nature — análise estrutural):
   - Entrada: values list[str]
   - analyze_column(values) → ColumnFeatures (O(N), barato)
   - detect_cadence_from_features(features, unicas) → (bool, dict info) — determina se usa OBAT shape-preserve
   - detect_min_len_from_features(features) → int {3,4,5,6} — determina granularidade tokenização
   - Output: usados em OBAT layer (CAMADA 1), HCC layer (CAMADA 2)
   - Nota: **pre-pass é orthogonal a nature** — roda depois pre-tx CAMADA 0 (em _encode_column)
   
5. **Round-trip guarantee**:
   - Com nature: encode(values, nature=SPEC_X) → text; decode(text, nature=SPEC_X) == values ✓
   - Sem nature: encode(values) → text; decode(text) == values ✓
   - Fallback marker '_' preserva valores inválidos → round-trip sempre funciona

**KNOBS**:
  - MARKER_LITERAL = '_' (prefixo escape fallback) — linha 38 templated_checked.py
  - BASE94 alfabeto size = 80 chars (94-14-1, assert>=50) — linhas 32-36 templated_checked.py
  - SPEC_CPF.body_length = 9 (CPF body dígitos) — linha 157
  - SPEC_CPF.check_length = 2 (CPF check digits) — linha 158
  - SPEC_CPF.encoded_length = 5 (80^5 > 10^9, capacity check) — linha 161
  - SPEC_CNPJ.body_length = 12 (CNPJ body dígitos) — linha 194
  - SPEC_CNPJ.check_length = 2 — linha 195
  - SPEC_CNPJ.encoded_length = 7 (80^7 > 10^12) — linha 198
  - SPEC_IP.slot_widths = (3,3,3,3) (IPv4 octetos zero-padded a 3) — linha 123
  - _W1_CNPJ pesos mod-11 = [5,4,3,2,9,8,7,6,5,4,3,2] — linha 171
  - _W2_CNPJ pesos mod-11 = [6,5,4,3,2,9,8,7,6,5,4,3,2] — linha 172
  - CPF check_fn mod-11 threshold = 10 (se resto==10 então 0) — linhas 139, 143
  - CNPJ check_fn mod-11 threshold = 2 (se rem<2 então 0, else 11-rem) — linhas 179, 182
  - detect_cadence n_sample = 5 (primeiras N strings pra Regra 1) — linha 31 auto_cadence.py
  - detect_cadence threshold = 0.7 (LCP+LCS / length ratio mínimo) — linha 32
  - detect_cadence numeric_card_threshold = 0.5 (Regra 2 cardinality) — linha 33
  - detect_min_len n_threshold = 100 (rows mínimo pra aplicar heurística) — linha 49 auto_min_len.py
  - detect_min_len gating decision: n < 100 -> return 3 (preserva M9 baseline) — linha 50
  - analyze_column sample_size = 20 (amostra pra is_numeric check) — linha 51 column_features.py
  - CPF regex pattern = r'^(\d{3})\.(\d{3})\.(\d{3})-(\d{2})$' — linha 133
  - CNPJ regex pattern = r'^(\d{2})\.(\d{3})\.(\d{3})/(\d{4})-(\d{2})$' — linha 169
  - IPv4 regex pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$' — linha 118

**EXTENSION POINTS (v2.0 hooks)**:
  - **Adicionar nova spec Checked (ex: Luhn para cartão crédito)**: criar novo TemplatedCheckedSpec com regex próprio, body_length, check_fn(body)->list[int], formatter, encoded_length; nenhuma mudança em core — polimorfismo via spec param garante compatibilidade.
  - **Adicionar nova spec Padded (ex: MAC address, CEP brasileiro)**: implementar TemplatedPaddedSpec com regex, slot_widths tuple, separator; mesma filosofia sans check — HCC seq-RLE pode explorar estrutura se houver cadência.
  - **v2.0 lossy-recoverable (H-LR-*)**: criar `TemplatedLossySpec(name, regex, body_length, rounding_fn, error_fn, encoded_length)` — encode retorna (rounded, error_term) packed; decode soma. Não afeta rt mas reduz bytes em floats/coords com tolerância. Plugar via pipeline nature param idêntico.
  - **v2.0 strip-sufixo (V2-D)**: criar `TemplatedSuffixSpec(name, regex, suffix_dict, body_spec)` — detecta sufixo enumerated (ex: '.com' em email), enumera, encode retorna (body_encoded, suffix_idx). Composição com Templated+Enumerated.
  - **v2.0 auto-detect naturezas (Schema_builder Fase 3)**: em build_schema, para cada coluna adicionar `detect_nature_via_apply_rate(column_name, values, threshold=0.8)` — retorna SPEC_CPF se 80%+ valores são 'compressible' CPF. Popula `ColumnSchema.natures` list. Requer header carry spec id pra decoder auto-detectar (ADR-0015 futuro sec 159-161).
  - **v2.0 header carry spec id**: modificar TCF format #TCF.6 M multi-col meta line pra incluir nature spec identifier per coluna (ex: `col1=cpf col2=ip`). Decoder lê header, auto-detecta spec sem out-of-band. Single-col: adicionar marker no body inicial.
  - **Threshold tunning pra CAMADA 0**: `encode(..., layers=PipelineConfig(nature_apply_threshold=0.8))` — aplica nature só se apply_rate >= threshold. Futuro T-CODE-LAYERED-PIPELINE Fase 2.
  - **Fallback adaptativo**: atualmente '_' marker é binário (usa ou não). v2 pode ter graduated fallback: 'partial_compress' (encode parte) vs 'literal' vs 'hybrid' (mix chars base94 + literal). Requer extend Protocol NatureSpec com encode_partial method.

**STRATEGIES** (19):

### [estrategia] TemplatedCheckedSpec (classificação + encode/decode parametrico)  (src/tcf/natures/templated_checked.py:42-109)
  desc: Classificador + encoder/decoder polimórfico genérico para identificadores com layout fixo (regex template), dígito verificador derivável (check_fn), e espaço único-discreto (sem ordem). Filosofia opt-in per-value: cada valor decide se comprime (base-94 encoded, 5-7 chars) ou cai em fallback literal (marcador '_' prefixado). Parametrizado por: name, regex, body_length, check_length, check_fn, formatter, encoded_length. **Protocolo**: encode_value(v)->tuple(payload,status), decode_value(payload)->str, classify_value(v)->str (taxonomy Kim 2003). Zero isinstance check — polimorfismo via spec param (Strategy pattern).
  params: TemplatedCheckedSpec @dataclass fields: name (str), regex (re.Pattern), body_length (int), check_length (int), check_fn (Callable), formatter (Callable), encoded_length (int)
  triggers: sempre — integrado no pipeline TCF quando nature param fornecido em encode(data, nature=SPEC_X) ou decode(text, nature=SPEC_X)
### [decision-point] classify_value — Taxonomia Kim 2003 (5 categorias + 1 fallback genérico)  (src/tcf/natures/templated_checked.py:64-81)
  desc: Decision tree com 6 outcomes: (1) empty_value (v==''), (2) format_unmasked (exato body_length+check_length dígitos, isdigit()=true, mas sem máscara regex), (3) format_mismatch (regex.match falha, len<5 -> length_wrong, len>=5 -> format_mismatch), (4) length_wrong (extraído digits_str != body+check), (5) check_invalid (check digit mismatch), (6) compressible (tudo passou). Lógica exata: lines 66-81. Precedência: empty > format > length > check > compressible.
  params: v: str (valor); expected_total = body_length + check_length; extrai digits via ''.join(c for c in v if c.isdigit())
  triggers: sempre — em cada encode_value() ou quando chamado explicitamente via classify_value(spec, v) pra diagnostico
### [token-type] BASE94 alfabeto (80 chars, safe TCF)  (src/tcf/natures/templated_checked.py:32-36)
  desc: Alfabeto construído dinamicamente: todos chr(33-127) EXCETO reserved set ('\n\r\t ,~*\\#=[]<>"''\'`_'). Total = 94-14(reserved)-1(marker '_') = 79 chars efetivos (verificado assert>=50, real=80). Usado em base-94 encoding compressible: n % 80, n // 80, ... Alfabeto preserva RT — charset é deterministico e cyclic (0->BASE94[0], 1->BASE94[1], etc).
  params: nenhum — constante builtin ao modulo
  triggers: em encode_value() quando classify_value retorna 'compressible' (lines 90-95)
### [marcador] MARKER_LITERAL '_' — Fallback literal prefix  (src/tcf/natures/templated_checked.py:38)
  desc: Prefixo '_' distingue valor comprimido (base-94 encoded, 5-7 chars) de literal fallback. Ao decodificar: se payload.startswith('_'), remove marker e retorna original (line 100). Ao codificar: fallback retorna '_' + v (line 87). Semantica: '_' é um escape — tudo após é literal UTF-8 do original, preservando RT mesmo em valores não-compressible. Char escolhido porque já é reservado TCF (não em BASE94, não em regex templates típicos).
  params: nenhum — constante '_'
  triggers: em encode_value() quando classify_value != 'compressible' (line 87); em decode_value() quando payload começa com '_' (line 99)
### [estrategia] encode_value — Base-94 encoding compressible  (src/tcf/natures/templated_checked.py:83-95)
  desc: Two-path: (1) compressible: extrai body_int (primeiros body_length dígitos), converte pra base-94 em encoded_length chars via n%80, n//80 loop (lines 90-94), reversa ordem (chars built em little-endian, reversed ao final). (2) fallback: retorna '_' + v + status. Exemplo CPF: '529.982.247-25' -> body=529982247 -> 5 chars base94. Garante RT: se decoding recebe encoded, pode reverter sem ambiguidade.
  params: v: str; status = classify_value(v) determina path; body_int = int(digits[:body_length]); n = body_int; for _ in range(encoded_length): chars.append(BASE94[n % 80]); n //= 80; return reversed(chars)
  triggers: sempre em encode() pipeline quando nature param passado (encoder.py line 98-99)
### [estrategia] decode_value — Base-94 decoding + reformatting  (src/tcf/natures/templated_checked.py:97-109)
  desc: Two-path: (1) payload começa '_': strip marker, return original (line 100). (2) payload == encoded_length chars, all chars in BASE94: convert back via base-94 positional (lines 102-108). Rebuild body_str via zfill(body_length), aplica check_fn pra recalcular checks, aplica formatter pra restaurar máscara. Exemplo: '\29g/h-' -> n=0; for c in '29g/h-': n = n*80 + BASE94.index(c); body_str = str(n).zfill(9); checks = check_fn([int(d) for d in body_str]); formatter(body + checks) -> '529.982.247-25'.
  params: payload: str; expected encoded_length e all(c in BASE94); uses check_fn(body) + formatter(body+check) pra reconstruir.
  triggers: em decode() pipeline quando nature param passado (decoder.py line 89-90)
### [categoria] SPEC_CPF — (NNN.NNN.NNN-DD, mod-11 dupla)  (src/tcf/natures/templated_checked.py:130-162)
  desc: Spec concreto pra CPF brasileiro. Regex=r'^(\d{3})\.(\d{3})\.(\d{3})-(\d{2})$', body_length=9, check_length=2, encoded_length=5 (80^5 > 10^9). Check digits via _cpf_check_fn: Mod-11 dupla — d1=(S1*10)%11 (se==10 então 0), S1=sum(d*w for d,w in zip(body, range(10,1,-1))); similar d2 com body+d1 e range(11,1,-1). Formatter recombina com máscara. RT 100% em datasets validados; comprime CPF uniform/clustered 55-64% vs M10 puro (sub-exp 05-07).
  params: name='cpf', regex=_CPF_RE, body_length=9, check_length=2, check_fn=_cpf_check_fn, formatter=_cpf_formatter, encoded_length=5
  triggers: ao chamar encode(values, nature=SPEC_CPF) ou decode(text, nature=SPEC_CPF); ou explicitamente via from tcf import SPEC_CPF
### [categoria] SPEC_CNPJ — (NN.NNN.NNN/NNNN-DD, mod-11 dupla pesos diferentes)  (src/tcf/natures/templated_checked.py:165-199)
  desc: Spec concreto pra CNPJ brasileiro. Regex=r'^(\d{2})\.(\d{3})\.(\d{3})/(\d{4})-(\d{2})$', body_length=12, check_length=2, encoded_length=7 (80^7 > 10^12). Check digits via _cnpj_check_fn: mod-11 com pesos _W1_CNPJ=[5,4,3,2,9,8,7,6,5,4,3,2] e _W2_CNPJ=[6,5,4,3,2,9,8,7,6,5,4,3,2], diferente de CPF. Lógica: d1=0 se rem1<2 else 11-rem1. Formatter restaura máscara. RT 100%; comprime 54-61% vs M10 puro em datasets validados.
  params: name='cnpj', regex=_CNPJ_RE, body_length=12, check_length=2, check_fn=_cnpj_check_fn, formatter=_cnpj_formatter, encoded_length=7; _W1_CNPJ e _W2_CNPJ são arrays peso mod-11
  triggers: ao chamar encode(values, nature=SPEC_CNPJ) ou decode(text, nature=SPEC_CNPJ)
### [estrategia] TemplatedPaddedSpec (TCU-NoCheckVarLength — slots padronizados sem check)  (src/tcf/natures/templated_padded.py:37-113)
  desc: Variante de TemplatedCheckedSpec para dados SEM dígito verificador (ex: IPv4). Slots de width variável são padronizados via padding zero-leading. Diferenças: (1) sem check_fn, (2) sem base-94 (preserva dígitos pra HCC seq-RLE detectar cadência), (3) slot_widths tuple fixo. Exemplo: '192.168.1.1' -> slots=['192','168','1','1'] + slot_widths=(3,3,3,3) -> padded='192168001001' (12 dígitos). classify_value retorna 'format_padded_zeros' se slot str(int(slot))!=slot (detecta padding não-canonical, ex: '192.168.01.1'). RT 100%; D-IP-subnet comprime 1.71% ratio vs M10 puro (speedup 68x, sub-exp 08).
  params: name (str), regex (re.Pattern com grupos=slots), slot_widths (tuple int), separator (str). total_padded_length = sum(slot_widths).
  triggers: sempre — Protocolo NatureSpec idêntico a TemplatedCheckedSpec (sem isinstance check)
### [categoria] SPEC_IP — IPv4 (slot_widths=(3,3,3,3), separator='.')  (src/tcf/natures/templated_padded.py:116-125)
  desc: Spec concreto pra IPv4 canonical (sem zeros líderes em octetos, ex: '192.168.1.1'). Regex=r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'. encode_value: zfill cada slot a 3 dígitos, concatena -> '192168001001'. decode_value: split em 4 chunks de 3 dígitos, remove leading zeros via str(int(slot)), rejoin com '.'. Ganho em D-IP-subnet (1000 IPs /24) = 229B (1.71% ratio) vs M10 puro 13349B — HCC seq-RLE detecta cadência quando IPs em subnet; em D-IP-uniform (aleatório) = 102% (pior sem estrutura, esperado).
  params: name='ip', regex=_IPV4_RE, slot_widths=(3,3,3,3), separator='.'
  triggers: ao chamar encode(values, nature=SPEC_IP) ou decode(text, nature=SPEC_IP)
### [decision-point] classify_value TemplatedPaddedSpec — Taxonomy (6 categorias)  (src/tcf/natures/templated_padded.py:63-84)
  desc: Decision tree: (1) empty_value (v==''), (2) format_mismatch (regex.match falha), (3) range_invalid (slot int >= 10^width, overflow), (4) format_padded_zeros (str(int(slot))!=slot original — ex: '192.168.01.001' tem padding não-canonical), (5) compressible (todas slots parseáveis como int, no overflow, sem padding). Precedência idêntica a TemplatedCheckedSpec. Linha 82-83: detecta padding não-canonical via `str(val) != slot_str`.
  params: v: str; extrai slots via regex.groups(); para cada slot: int(slot_str) >= 10^width -> range_invalid; str(int(slot_str))!=slot_str -> format_padded_zeros
  triggers: sempre em encode_value() quando nature=SPEC_IP fornecido
### [estrategia] encode_value TemplatedPaddedSpec — Padding + preservação dígitos  (src/tcf/natures/templated_padded.py:86-97)
  desc: Dois paths: (1) compressible: extrai slots via regex.groups(), zfill cada slot a width, concatena em padded string digit-only (ex: '192.168.1.1' -> '192168001001'). (2) fallback: return '_' + v. Diferença vs TemplatedCheckedSpec: sem base-94 — preserve dígitos visíveis pra HCC seq-RLE digit-centric detectar cadência. Fallback marker idêntico ('_' prefix).
  params: v: str; status = classify_value(v); if compressible: return ''.join(slot_str.zfill(width) for slot_str, width in zip(slots, slot_widths)), 'compressible'
  triggers: em encode() pipeline quando nature=SPEC_IP passado
### [estrategia] decode_value TemplatedPaddedSpec — Unpadding + reformatting  (src/tcf/natures/templated_padded.py:99-113)
  desc: Dois paths: (1) payload começa '_': strip, return original. (2) payload == total_padded_length, all chars digit: split em slot_widths chunks, convert cada via str(int(slot)) pra remover leading zeros, rejoin com separator. Exemplo: '192168001001' -> chunks=['192','168','001','001'] -> [str(int(...))] = ['192','168','1','1'] -> '.'.join() = '192.168.1.1'. RT 100%.
  params: payload: str; len(payload)==total_padded_length e payload.isdigit(); cursor tracking per slot_widths
  triggers: em decode() pipeline quando nature=SPEC_IP passado
### [estrategia] Integration: encode() pipeline com nature param  (src/tcf/encoder.py:53-114)
  desc: Dispatcher: (1) list[str] + nature param: applica encode_value(nature, v) em CADA valor antes do M10 pipeline (lines 97-99), resultando em list[str] com valores já pré-transformados (comprimidos ou fallback). (2) dict + nature_per_col param: para cada coluna name, if name in nature_per_col, aplica encode_value(nature_per_col[name], v) em todos valores da coluna (lines 104-109). Filosofia: nature é **CAMADA 0 do funil** — anterior a analyze_column/detect_cadence/OBAT/HCC. Sem nature param: comportamento M10 inalterado (byte-canonical preservado, D17a 322B INVARIANT).
  params: nature: TemplatedCheckedSpec | None, nature_per_col: dict[str, TemplatedCheckedSpec] | None
  triggers: sempre em encode() quando nature ou nature_per_col param passado; sem param = skip (comportamento legacy M10)
### [estrategia] Integration: decode() pipeline com nature param  (src/tcf/decoder.py:52-91)
  desc: Dispatcher: (1) single-col: decode_column retorna list[str] (HCC decoded), aplica decode_value(nature, v) em cada v (lines 88-90). (2) multi-col: _decode_multi retorna dict (HCC decoded), aplica decode_value(nature_per_col[name], v) em cada coluna (lines 79-85). Filosofia: decoder é **espelho de encoder** — mesma nature spec obrigatória out-of-band (decoder não auto-detecta; futuro v2 carry spec em header). Sem nature param: skip reverse (valores já em formato original via '_' marker fallback ou HCC canonical).
  params: nature: TemplatedCheckedSpec | None, nature_per_col: dict[str, TemplatedCheckedSpec] | None
  triggers: sempre em decode() quando nature ou nature_per_col param passado; sem param = skip
### [heuristica] analyze_column — ColumnFeatures pre-pass (O(N))  (src/tcf/column_features.py:51-84)
  desc: Pre-pass unificado: calcula features básicas em 1 passada O(N) — n_rows, n_unicas (via set(values)), avg_len, cardinality=n_unicas/n_rows, is_numeric (sample check float parse), sample (primeiros 20 strings). Recebido por downstream heuristicas (detect_cadence, detect_min_len, futuras detect_X naturezas). Reduz duplicação + permite reuso. Welded T-CODE-H-DA-11c (2026-05-22). Nota: **sem natureza** — apenas features, não aplica pré-tx.
  params: values: list[str], sample_size=20 (default). n_rows = len(values); n_unicas = len(set(values)); avg_len = sum(len(v))/n; cardinality = n_unicas/n_rows; is_numeric = all(_is_numeric_string(v) for v in sample)
  triggers: sempre em _encode_column() (encoder.py:139), antes de detect_cadence/detect_min_len
### [heuristica] detect_cadence_from_features — Regra 1 + Regra 2  (src/tcf/auto_cadence.py:28-96)
  desc: Detecta estrutura cadencial (wrapper+counter ou numeric high-card) pra ativar OBAT shape-preserve hint. **Regra 1** (uniform-length + high-LCP-LCS): primeiras N strings length uniforme, calcula LCP+LCS entre pares consecutivos, ratio=(LCP+LCS)/length; se TODOS ratios >= threshold (default 0.7), aciona. **Regra 2** (numeric high-cardinality, ADR-0008): features.is_numeric=true E cardinality > 0.5, aciona. Retorna (detectou:bool, info:dict com detalhes). Se detecta: encoder chama processar_with_hint(prefer_shape_consistency=True) em vez de processar() canonical (obat_shape.py).
  params: features: ColumnFeatures, strings_unicas: list[str], n_sample=5 (primeiras N pra análise), threshold=0.7, numeric_card_threshold=0.5
  triggers: em _encode_column() linha 141 (encoder.py), após analyze_column()
### [heuristica] detect_min_len_from_features — Decision tree shallow (heurística v3)  (src/tcf/auto_min_len.py:25-68)
  desc: Decision tree pra min_len ótimo (enum {3,4,5,6}), captura 99.5% oracle real-world. Gating: n_rows < 100 -> 3 (preserva M9 baseline 1615B exato). Senão: card<0.2 -> 3; avg>=25 -> 6; avg>=8 && card>=0.4 -> 6; avg>=5 && is_numeric && card>=0.8 -> 6; avg>=12 && card>=0.7 -> 5; avg>=3 && card>=0.2 -> 4; else -> 3. Exemplos: D-CPF (baixa card) -> 3; D-datas-mundiais (avg=10, card=0.8) -> 6; D-ID-seq (avg=5, is_num=true, card=0.95) -> 6.
  params: features: ColumnFeatures, n_threshold=100 (gating). avg_len = features.avg_len; card = features.cardinality; is_num = features.is_numeric
  triggers: em _encode_column() linha 142 (encoder.py), após detect_cadence() output recebido
### [helper] Protocol NatureSpec — Polimorfismo sem isinstance  (src/tcf/natures/ (init define protocol implícito))
  desc: Estratégia de design: toda spec (TemplatedCheckedSpec, TemplatedPaddedSpec, futuras) implementa o mesmo Protocol: name:str, encode_value(v)->tuple(str,str), decode_value(payload)->str, classify_value(v)->str. Encoder/decoder são polimorfo (genéricos) — **zero isinstance(spec, TemplatedCheckedSpec)** em qualquer lugar (confirmado linha 20 encoder.py comentário). Permite adicionar specs novas (Luhn, IBAN, MAC, CEP) sem mudar API publica nem core pipeline. Refactoring 2026-05-24: converteu encode_value/decode_value/classify_value de standalone functions (backward compat mantido) para **methods no spec** (@dataclass frozen, immutable).
  params: nenhum — define contrato de interface, não implementação concreta
  triggers: sempre — em toda integração com nature param

**NOTES**: 
**CAMADA 0-pre Natures subsystem — Resumo técnico exhaustivo:**

1. **Filosofia opt-in per-value**: cada valor **decide individualmente** se comprime. Sem "all-or-nothing" — fallback literal ('_' marker) preserva RT sempre. Compressão ocorre quando valor passa validate (regex + check digit). Não-compressible caem em fallback automaticamente.

2. **Dois tipos de specs atuais**:
   - **TemplatedCheckedSpec** (CPF, CNPJ): layout fixo + dígito verificador derivável → base-94 encoded (5-7 chars)
   - **TemplatedPaddedSpec** (IP): layout fixo, slots padronizados via padding, **sem check** → digit-only padded (preserva visibilidade HCC seq-RLE)

3. **Polimorfismo Protocol-based**: encoder/decoder são **genéricos** — não há isinstance() check. Permite adicionar specs futuras (Luhn, IBAN, MAC, CEP) sem mudar pipeline core. Strategy pattern puro.

4. **Integração CAMADA 0-do funil**:
   - Pre-tx CAMADA 0 (nature): `encode_value(spec, v)` per-valor, **antes** de analyze_column
   - CAMADA 1 (pre-pass): detect_cadence, detect_min_len sobre ColumnFeatures (sem nature interference)
   - CAMADA 2 (OBAT): tokenization com hints
   - CAMADA 3 (HCC): composicional + seq-RLE

5. **Byte-canonical INVARIANT preservado**: sem nature param = sem mudança. D17a 322B INVARIANT validado. Default M10 comportamento é seguro — backwards compatible 100%.

6. **Fallback marker '_'**: escape character. Todos valores inválidos, empty, ou não-matching regex caem aqui. Decoder reconhece '_' prefix → strip → retorna original. Garante round-trip lossless **sempre**.

7. **Check digit semântica**:
   - **CPF**: Mod-11 dupla com pesos range(10,1,-1) e range(11,1,-1); se resto==10 então check=0
   - **CNPJ**: Mod-11 com pesos específicos _W1, _W2; se rem<2 então 0, else 11-rem
   - **IP**: sem check — apenas padding

8. **Validação real-world (sub-exps 05-08)**:
   - CPF 50 vals: 942B (M10) → 337B (nature) = **-64%**
   - CNPJ 50 vals: similar **-54 a -61%**
   - D-IP-subnet 1000: **1.71% ratio** (vs M10 13349B) — **speedup 68x**
   - D-IP-uniform 200: 102% (pior, sem cadência — esperado)
   - RT 100% todos datasets; tests 192 passed

9. **Decode reversibility**: decoder requer **same spec out-of-band**. Futuro v2 carry spec em header. Atualmente: caller responsável prov spec.

10. **Threshold/Heuristic landscape**:
    - `MARKER_LITERAL = '_'` — fixo, não tunável (parte do formato TCF)
    - `BASE94 = 80 chars` — fixo (segurança charset TCF)
    - `encoded_length` por spec — fixo (derivado body_length via capacity math)
    - `detect_cadence threshold = 0.7` — tunável futuro (T-CODE-LAYERED-PIPELINE Fase 2)
    - `detect_cadence numeric_card_threshold = 0.5` — tunável futuro
    - `detect_min_len n_threshold = 100` — tunável futuro (gating)

11. **Gaps/TODO v2.0 (ADR-0018 roadmap)**:
    - Auto-detect natures via apply_rate threshold (Schema_builder Fase 3)
    - Header carry spec id (decoder auto-detecta)
    - Lossy-recoverable (H-LR-*) — quando dataset real disponível
    - Strip-sufixo (V2-D) — composite Templated+Enumerated
    - IBAN, Luhn, MAC, CEP specs — quando datasets reais validarem necessidade
    - Fallback adaptativo (partial compress, hybrid)

12. **Code reachability**:
    - encode() entry: encoder.py:53-114 (lines 97-109 nature dispatch)
    - decode() entry: decoder.py:52-91 (lines 79-90 nature dispatch)
    - ColumnFeatures pre-pass: column_features.py:51-84
    - Cadence heuristic: auto_cadence.py:28-96 (2 regras, lines 64-93)
    - Min_len heuristic: auto_min_len.py:25-68 (decision tree, lines 49-68)
    - Specs registry: natures/__init__.py:34-63 (exports SPEC_CPF, SPEC_CNPJ, SPEC_IP)

13. **Documentação canonical**:
    - ADR-0015: decision + welding rationale
    - use-natures.md: how-to + exemplos
    - data-natures-taxonomy.md: teoria 8 naturezas
    - tests/test_natures.py + test_natures_ip.py: validação


================================================================================
## Dispatch, Multi-Column, PipelineConfig & Format Inventory
================================================================================

**CONTROL FLOW**: **ENCODE DISPATCH:** encode(data, nature=, nature_per_col=, layers=cfg, parallel=, side_outputs=) -> isinstance(data, list[str]) ? YES: [CAMADA 0 optional] if nature: apply encode_value() per value -> _encode_column(data, header='val', side=side, cfg=cfg) [single-col pipeline M10, returns body puro, no shebang] | NO: isinstance(data, dict) ? YES: [CAMADA 0 optional] if nature_per_col: apply encode_value() per col per value -> _encode_multi(data, side=side, parallel=parallel, cfg=cfg) [multi-col pipeline, returns #TCF.6 M + meta + bodies] | NO: raise TypeError | SINGLE-COLUMN PIPELINE (_encode_column): _encode_column(values, header, side=None, cfg=DEFAULT_PIPELINE) -> Dedup via OrderedDict (preserve first occurrence) | [CAMADA 1: Pre-Pass] if cfg.pre_pass: analyze_column(values) -> ColumnFeatures | detect_cadence_from_features(features, unicas) -> (cadence_detected, cadence_info) [Regra 1: uniform_length + high LCP+LCS; Regra 2: numeric + high_card] | detect_min_len_from_features(features) -> min_len in {3,4,5,6} [decision tree: n_threshold=100 gating, avg_len/card/is_numeric branches] | [CAMADA 2: OBAT Tokenization] -> if cadence_detected AND cfg.obat_shape_preserve: processar_with_hint(unicas, min_len=min_len, prefer_shape_consistency=True) [tries to preserve shape across consecutive strings] else: processar(unicas, min_len=min_len) [canonical OBAT: greedy best pref+suf via LCP+LCS, trigram-indexed] -> tokens_por_string, obat_log | [CAMADA 3: HCC Compaction] -> if cfg.hcc_seq_rle: syn = HCCSeqRLE() else: syn = M8AVirtualRefsSyntax() | body = syn.encode(values, unicas, tokens_por_string, header) [M8A: tokenize pieces, detect compositions, emit body with refs/atoms/aliases; M10: post-process body lines, detect near-identical runs, emit '*N+delta|' markers] | [Side Outputs] if side is not None: populate: column_features, cadence_detected, cadence_info, min_len, obat_log, obat_used_hint, hcc_trace, hcc_rede, seq_rle_runs, body_bytes | return body (text, always ends with \\n) | MULTI-COLUMN PIPELINE (_encode_multi): _encode_multi(table, side=None, parallel=, cfg=DEFAULT_PIPELINE) -> Validate: non-empty, uniform row counts, no ',' or '=' in col names | Stringify values (NULL -> '') | Dispatch: parallel flag + len(table) >= 2 ? YES (parallel=True|int AND len >= 2): _encode_columns_parallel(table_str, want_side, n_workers=N, cfg) [order cols by workload desc, submit to ProcessPoolExecutor, collect via as_completed, reorder by original dict order] -> col_bodies_bytes, per_col_sides | NO: _encode_columns_serial(table_str, want_side, cfg) [iterate in dict order, call _encode_column per col] -> col_bodies_bytes, per_col_sides | Build multi header: meta_pairs = \",\".join(f\"{len(b)}={name}\" for name, b in col_bodies_bytes) | header = b'#TCF.6 M\\n# ' + meta_pairs.encode() + b'\\n' | Byte-precise concat: body_concat = b''.join(b for _, b in col_bodies_bytes) | full = header + body_concat | [Side Outputs] if side is not None: multi_info: {n_rows, n_cols, total_bytes, header_bytes, body_bytes, parallel_workers} | per_col: dict[name, SideOutputs] | return text = full.decode('utf-8') | DECODE DISPATCH: decode(tcf_text, nature=, nature_per_col=) -> tcf_text.startswith('#TCF.6 M') ? YES: _decode_multi(tcf_text) -> dict[str, list[str]] | [CAMADA 0 optional] if nature_per_col: apply decode_value() per col per value | NO: _decode_column(tcf_text) -> list[str] | [CAMADA 0 optional] if nature: apply decode_value() per value | return result (dict or list) | SINGLE-COLUMN DECODE (_decode_column): _decode_column(tcf_text) -> syn = HCCSeqRLE() | syn.decode(tcf_text) -> list[str] [HCCSeqRLE.decode: expand '*N+delta|' markers first, then M8A decode] | return values | MULTI-COLUMN DECODE (_decode_multi): _decode_multi(tcf_text) -> Find line 1 (shebang): validate MAGIC_MULTI | Find line 2 (meta): validate META_PREFIX, parse 'size1=name1,size2=name2,...' | For each (size, name) pair: -> slice body[cursor:cursor+size] (byte-precise) | _decode_column(body_text) -> list[str] | result[name] = list[str] | cursor += size | return result (dict[str, list[str]]) | HCC M8A ENCODE (M8AVirtualRefsSyntax.encode): encode(linhas, unicas, tokens_por_string, header) -> Phase A: _tokenize_pieces(linhas, unicas, tokens_por_string) | collect breaks (QB quotient positions) | for each unique value: decompose into lit/ref pieces | pieces_per_line, line_meta (count, eid, is_rep), atom_count | Phase B: _detect_compositions(pieces_per_line, atom_count) | iterative: count sub-tuplas K>=2, apply virtual-relaxed filter, pick highest net=(R-1)*(baseline-n_tam), substitute, next iter | returns alias_to_sub, iter_traces | Phase C: _emit_body(pieces_per_line, line_meta, alias_to_sub) | walk pieces, emit lits (escape digits, *, \\, ~), emit refs (M1.E ranges + ~ composition) | emit aliases (inline-expanded chains with pairwise binarization) | body: list[str], prov_to_final, alias_to_final, ref_seqs | Build debug info (trace, rede) | return body text: '\\n'.join(body) + '\\n' | HCC M10 ENCODE (HCCSeqRLE.encode): encode(linhas, unicas, tokens_por_string, header) -> body_text = super().encode(...) (M8A) | body_lines = body_text.rstrip('\\n').split('\\n') | compact_body(body_lines) | detect_seq_runs: consecutive pairs with same escape-digit runs + consistent delta list | for each run: emit '*N+delta|template' (or '*N+d1,d2,...|' for mixed) | collect info: start_line, end_line, count, deltas, savings | return compacted_lines, info_list | return text: '\\n'.join(compacted) + '\\n'

**KNOBS**:
  - cfg.pre_pass (bool, default True) — enable pre-pass heuristics or use defaults (cadence=False, min_len=3)
  - cfg.obat_shape_preserve (bool, default True) — enable shape-consistency hint in OBAT if cadence detected
  - cfg.hcc_seq_rle (bool, default True) — enable seq-RLE near-identical compaction (M10) or use M9 pure
  - parallel (bool|int, default False) — False=serial, True=os.cpu_count(), int N=N workers; ignored if len(table)<2
  - nature (TemplatedCheckedSpec | None, default None) — apply pre-tx filter per value (list input only)
  - nature_per_col (dict[str, TemplatedCheckedSpec] | None, default None) — apply pre-tx filter per column (dict input only)
  - detect_cadence: n_sample=5 (tunable in detect_cadence_from_features) — size of prefix sample for rule 1
  - detect_cadence: threshold=0.7 (tunable) — min (LCP+LCS)/length ratio for rule 1
  - detect_cadence: numeric_card_threshold=0.5 (tunable) — cardinality threshold for rule 2
  - detect_min_len: n_threshold=100 (tunable) — gating: n_rows < 100 always 3 (M9 baseline preservation)
  - obat_shape_preserve: min_len parameter (from pre-pass) — minimum lengths for pref/suf in shape preservation
  - seq_rle: delta format (int vs list[int]) — M10-compat single delta or ADR-0016 per-run deltas
  - multi-col: col name validation — no ',' or '=' allowed in column names (hard constraint)
  - multi-col: workload heuristic — sum(len(v) for v in col) used to order columns for parallel dispatch

**EXTENSION POINTS (v2.0 hooks)**:
  - V2-A (Fallback Identity Per-Column): Inject at _encode_column return, emit marker if HCC ratio below threshold, decoder skips HCC on fallback. Meta: '=name' vs 'size=name'. Touch: multi.py header/decode, encoder dispatch.
  - V2-B (Dictionary Layer): Pre-HCC dict for high-repetition. CAMADA 2.5 dispatch: if n_unicas < threshold*n_rows, build value->id dict, emit dict meta (size/dict_id=name). Touch: multi.py meta builder, decoder dict marker.
  - V2-C (Patricia Trie Ref Index): Replace trigram hash in OBAT with prefix trie. Same tokens, backward-compat. Touch: core/online.py, obat_shape.py.
  - V2-D (Lossy Compression): New nature category (NatureLosy) with encode_value/decode_value. Marker prefix distinct from Templated. Example: float rounding. Touch: encoder.py nature dispatch, natures/.
  - V2-E (Adaptive Layer Selection): Per-column cfg markers in meta ('size:cfg=name', cfg='p0_h0_s1'). Heterogeneous pipelines. Touch: multi.py meta encode/decode.
  - V2-F (Streaming Encoder): _encode_column as generator (yield chunks). Out-of-core support. HCCSeqRLE buffering strategy. Touch: encoder.py, multi.py workers.
  - V2-G (Cross-Column Atom Sharing): Global alias namespace, sub-tuplas span cols. Multi-col body merger. Complex meta. Touch: multi.py merger, HCC detector.
  - V2-H (Custom Tokenizer Plugin): Token protocol extensible (TokCustom variant). cfg.tokenizer_plugin dispatch. Touch: encoder.py line 150/155, plugin registry.
  - V2-I (Per-Layer Decision Markers): Embed comments in body ('# CADENCE=1', '# MIN_LEN=4') for auto decoder intelligence. Touch: side_outputs, decoder comment strip.

**STRATEGIES** (27):

### [decision-point] Dispatch Strategy (encode)  (src/tcf/encoder.py:53-114)
  desc: Top-level dispatch via isinstance(data, dict). If list[str], calls _encode_column with default header='val'; if dict, delegates to _encode_multi (which routes to multi-col pipeline). Raises TypeError for other types. Nature pre-transform (CAMADA 0, opt-in) applied BEFORE pipeline if nature= or nature_per_col= provided.
  params: data type check, nature/nature_per_col specs (optional), layers (PipelineConfig), parallel flag
  triggers: encode() called with any data
### [decision-point] Dispatch Strategy (decode)  (src/tcf/decoder.py:52-91)
  desc: Routing via shebang prefix check. If tcf_text.startswith('#TCF.6 M'), calls _decode_multi (dict result); else calls _decode_column (list result). Nature reverse-transforms applied post-decode if nature/nature_per_col provided.
  params: _MULTI_MAGIC_STR = '#TCF.6 M'
  triggers: decode() called with TCF text
### [estrategia] Single-Column Encode Pipeline (M10 Canonical)  (src/tcf/encoder.py:117-178)
  desc: Core unit _encode_column orchestrates CAMADA 1-3: (1) Pre-pass: analyze_column + detect_cadence (rules 1-2 ADR-0008) + detect_min_len (heur v3 ADR-0010) IF cfg.pre_pass=True, else cadence=False, min_len=3 default; (2) OBAT tokenization: processar_with_hint(prefer_shape_consistency=True) if cadence detected AND cfg.obat_shape_preserve=True, else canonical processar; (3) HCC: HCCSeqRLE (M10) if cfg.hcc_seq_rle=True else M8AVirtualRefsSyntax (M9). Side outputs captured per-column into provided SideOutputs container.
  params: cfg.pre_pass (bool, default True), cfg.obat_shape_preserve (bool, default True), cfg.hcc_seq_rle (bool, default True), header name, side_outputs optional
  triggers: dispatch determines list[str] input OR _encode_multi calls for each column
### [estrategia] Multi-Column Encode Router  (src/tcf/multi.py:40-111)
  desc: Orchestrates dict->TCF serialization: validates (non-empty, uniform row counts, no ',' or '=' in col names), stringifies all values (NULL->'' per ADR-0013), chooses serial vs parallel dispatch based on parallel flag + column count (>= 2), encodes each column to body bytes, builds meta line '# size1=name1,size2=name2,...', outputs magic + meta + byte-precise concat.
  params: parallel: False (serial default), True (os.cpu_count workers), int N >= 1 (N workers); cfg: PipelineConfig; side_outputs optional
  triggers: encode() called with dict[str, list[str]]
### [estrategia] Parallel Encoding Strategy (Work-Stealing)  (src/tcf/multi.py:131-182)
  desc: Fase 1b (2026-05-24): Orders columns by workload descending (sum bytes per col as proxy), submits to ProcessPoolExecutor via as_completed (dynamic work-stealing), reorders results by original dict order for byte-identical output. Enabled only if parallel=True/int AND len(table) >= 2 (overhead rule). Serial fallback for 1-col or parallel=False.
  params: n_workers computed from parallel flag; heuristic: sum(len(v) for v in col) per column
  triggers: parallel=True|int and len(dict) >= 2 in _encode_multi
### [estrategia] Multi-Column Decode Router  (src/tcf/multi.py:195-234)
  desc: Parses shebang + meta line (finds 2 newlines, validates MAGIC_MULTI + META_PREFIX), splits meta into (size, name) pairs, byte-precise slices body, decodes each via _decode_column, assembles dict result. No reordering needed (serial decode preserves order).
  params: none (pure parser)
  triggers: decode() detects #TCF.6 M prefix
### [filtro] Nature Pre-Transform Filter (CAMADA 0, opt-in)  (src/tcf/encoder.py:97-99 (list), 103-109 (dict))
  desc: ADR-0015 pre-pass filter: if nature= or nature_per_col= provided, applies encode_value() per value BEFORE pipeline M10. Caller must provide spec out-of-band to decoder. Templated+Checked+Unique (CPF/CNPJ) compresses valid IDs to base-94, literals prefixed '_'. Marker: _ prefix distinguishes encoded vs literal fallback. Opt-in per-column (dict) or global (list).
  params: nature: TemplatedCheckedSpec | None (list); nature_per_col: dict[str, TemplatedCheckedSpec] | None (dict); marker MARKER_LITERAL='_'
  triggers: nature/nature_per_col params provided to encode()
### [heuristica] Pre-Pass Cadence Detection (Regra 1 + 2)  (src/tcf/auto_cadence.py:28-96)
  desc: Two-rule heuristic (ADR-0008): Regra 1 (wrapper+counter) — uniform lengths in first n_sample strings + LCP+LCS / length >= threshold (default 0.7) in consecutive pairs; Regra 2 (numeric high-card) — is_numeric=True AND cardinality > 0.5. Returns (bool, info_dict with rule_hit, reason, details). Drives obat_shape_preserve hint decision.
  params: n_sample=5 (default, tunable), threshold=0.7 (LCP+LCS ratio), numeric_card_threshold=0.5
  triggers: cfg.pre_pass=True in _encode_column
### [heuristica] Min-Len Auto-Detection (Heuristic v3)  (src/tcf/auto_min_len.py:25-68)
  desc: Decision tree (ADR-0010 H-DA-11): if n_rows < 100 return 3 (gating, preserves M9 baseline exactly); else: card < 0.2 -> 3; avg_len >= 25 -> 6; avg_len >= 8 && card >= 0.4 -> 6; avg_len >= 5 && is_numeric && card >= 0.8 -> 6; avg_len >= 12 && card >= 0.7 -> 5; avg_len >= 3 && card >= 0.2 -> 4; else 3. Achieves 99.5% oracle match on Adult+TPC-H.
  params: n_threshold=100 (gating), avg_len, cardinality, is_numeric from ColumnFeatures
  triggers: cfg.pre_pass=True in _encode_column
### [heuristica] OBAT Shape-Preserve Hint  (src/tcf/obat_shape.py:32-120)
  desc: Conditional optimization (ADR-0009): if prefer_shape_consistency=True AND last_shape exists, tries to replicate (p_src, p_len, has_L, s_src, s_len) shape on next string via _try_preserve_shape. Exact match: LCP >= p_len && LCS >= s_len; Wider fallback: reduce lens to available; Greedy fallback (canonical _escolher_par) if both fail. Preserves byte-canonical (shape replication deterministic given LCP/LCS contract).
  params: last_shape: (p_src, p_len_old, has_L, s_src, s_len_old) | None, min_len constraint
  triggers: cadence_detected=True AND cfg.obat_shape_preserve=True
### [estrategia] HCC Detector (M8A Unified Atom+Virtual)  (src/tcf/composicional/syntax.py:225-362)
  desc: Iterative composition detector (unlimited iterations, stops when no net > 0 candidate). Counter sub-tuplas K>=2 with R>=2, applies virtual-relaxed filter (<=1 virtual; if virtual at pos>0, alias must be resolved before sub's first emission), scores baseline_chars - estimated_id_chars, picks highest net=(R-1)*(baseline-n_tam). Per iteration: allocates alias_temp, substitutes in pieces, continues. Outputs alias_to_sub dict, iter_traces for debugging.
  params: atom_count (# atomics from tokenization), virtual-count filter (<=1), position-order constraint
  triggers: HCCSeqRLE.encode or M8AVirtualRefsSyntax.encode after tokenization
### [estrategia] HCC Seq-RLE Near-Identical Compaction  (src/tcf/composicional/hcc_seqrle.py:150-227)
  desc: Post-process body lines via detect_seq_runs (consecutive pairs pass compare_for_seq): same length + same escape-digit run positions + all diffs within runs + consistent delta list. For uniform delta (all equal, non-zero), emits M10-compat '*N+delta|template'; for mixed deltas (per-run), ADR-0016 '*N+d1,d2,...|template'. Expands on decode via expand_seq_marker. Detects runs greedily (consume maximal consecutive matches). Savings: sum(len(line_k)+1 for k in run) - (len(marker)+1).
  params: delta: int (M10 compat) or list[int] (ADR-0016), escape-digit run positions detected via find_escape_digit_runs
  triggers: cfg.hcc_seq_rle=True after HCC M8A body generation
### [helper] Escape Literal Encoding  (src/tcf/composicional/syntax.py:53-73)
  desc: Escapes reserved chars in literals: digits -> \d (run of digits escaped together), special chars *, \, ~ -> \ prefix. Returns (escaped_text, term_seq_flag) where term_seq=True if line terminates with escaped digit run (prevents confusion with ref-mode digit parsing in decoder).
  params: text string, reserved: {*, \, ~, digit}
  triggers: every literal in M8A _emit_body
### [helper] Ref-Run Composition Emission  (src/tcf/composicional/syntax.py:470-542)
  desc: Emits mixed atom/virtual ref runs: atomic segments -> M1.E ranges (a..b if 3+ consecutive), joined by ','; virtuals -> _emit_alias (def or use). Alias first-emission: inline-expands sub (linear chain), pairwise binarization allocates K-1 IDs, unresolved inner aliases gain final IDs at completion positions. Recursive expansion + body-order validation ensures correct final ID assignment.
  params: refs: list (mixed int > 0 for atoms, int < 0 for virtuals), state dict (current_id, prov_to_final, alias_to_final, alias_to_sub, ref_seq)
  triggers: M8A emit phase for every refs piece
### [threshold] PipelineConfig Toggle pre_pass  (src/tcf/pipeline.py:35-60)
  desc: Boolean toggle (default True). When True, runs analyze_column + detect_cadence_from_features + detect_min_len_from_features in CAMADA 1 pre-pass. When False, skips all heuristics: cadence_detected=False, min_len=3 (M9 default). Allows M9 baseline restoration for ablation studies.
  params: pre_pass: bool = True
  triggers: cfg passed to _encode_column
### [threshold] PipelineConfig Toggle obat_shape_preserve  (src/tcf/pipeline.py:35-60)
  desc: Boolean toggle (default True). When True AND cadence_detected, uses processar_with_hint(prefer_shape_consistency=True) instead of canonical processar. Shapes on consecutive strings to reduce HCC detection burden. False forces canonical OBAT regardless of cadence.
  params: obat_shape_preserve: bool = True
  triggers: cfg in _encode_column OBAT dispatch (line 149-156)
### [threshold] PipelineConfig Toggle hcc_seq_rle  (src/tcf/pipeline.py:35-60)
  desc: Boolean toggle (default True). When True, uses HCCSeqRLE (M10 with seq-RLE post-process). When False, uses M8AVirtualRefsSyntax (M9 pure, no seq-RLE). Controls whether near-identical run compaction via '*N+delta|' markers is applied.
  params: hcc_seq_rle: bool = True
  triggers: cfg in _encode_column HCC dispatch (line 159-162)
### [marcador] Side Outputs Capture Container  (src/tcf/side_outputs.py:27-51)
  desc: Optional reciprocal container (dataclass, all fields Optional). Per-column: column_features, cadence_detected, cadence_info, min_len, obat_log, obat_used_hint, hcc_trace, hcc_rede, seq_rle_runs, body_bytes. Multi-col: multi_info (n_rows, n_cols, total_bytes, header_bytes, body_bytes, parallel_workers), per_col dict. Populated only if side_outputs= provided (overhead=0 if None, logs discarded). Enables consumption by schema_builder, EncodeManager, debug tools.
  params: all fields initialized to None/empty
  triggers: side_outputs param provided to encode()
### [marcador] Format Marker: Shebang  (src/tcf/multi.py:36, src/tcf/decoder.py:49)
  desc: Multi-column magic: '#TCF.6 M' (8 bytes) followed by newline. Dispatches decoder to multi-col path. Single-column has NO shebang (body puro). Exact string comparison startswith() in decode dispatcher.
  params: MAGIC_MULTI = b'#TCF.6 M', checked via startswith()
  triggers: Every multi-col encode, every decode dispatcher
### [marcador] Format Marker: Meta Line  (src/tcf/multi.py:36-37, 95-96)
  desc: Second line: '# size1=name1,size2=name2,...' (space after '#', CSV-like col descriptor). Parsed by splitting on ',', then each pair on '=' (size is byte count as int, name is col name). Names cannot contain ',' or '='. Enables byte-precise body slicing on decode.
  params: META_PREFIX = b'# ', format: 'size1=name1,size2=name2,...', validators: no ',' or '=' in names
  triggers: Every multi-col encode output, every multi-col decode parse
### [marcador] Format Marker: RLE Count Prefix  (src/tcf/composicional/syntax.py:462-465, 747-751)
  desc: Repeat-length encoding (M8A + M10): '*N|value' emitted when consecutive identical values appear (count N >= 2, single values emit bare). Parser regex: line.startswith('*') && '|' in line, extracts count via int(line[1:bar]). Byte-preserving: N counted as decimal string. Decode re-emits [value] * N.
  params: N: count as int, separator: '|'
  triggers: M8A _emit_body or _decode when count > 1
### [marcador] Format Marker: Seq-RLE Near-Identical (M10)  (src/tcf/composicional/hcc_seqrle.py:202-210)
  desc: Extension of RLE for near-identical runs. M10-compat format: '*N+delta|template' (uniform delta) or ADR-0016 '*N+d1,d2,...|template' (per-run deltas). Delta sign explicit: +/- prefix ('+' omitted if >=0, implicit for <0). Decoder distinguishes via ',' in delta portion.
  params: N: count, delta: int | list[int], template: first line of run
  triggers: cfg.hcc_seq_rle=True after HCC body generation
### [token-type] Format Marker: Atomic Reference Ranges (M1.E)  (src/tcf/composicional/syntax.py:91-101)
  desc: Range compression for atomic refs: 3+ consecutive IDs -> 'a..b' (single/pair -> bare IDs '1,2'). Ranges separated by ','. Used in composition chains and ref-run emission. Decoder expands 'a..b' via range(a, b+1).
  params: consecutive threshold=3, separator: '..' for range, ',' between units
  triggers: M1.E composition chain emission, _emit_refs_range
### [token-type] Format Marker: Composition Chain (M1.E)  (src/tcf/composicional/syntax.py:104-114)
  desc: Chain of atomic IDs (pairwise composition via binarization): '1~2' (pair), '1~2~3' expands to intermediate '4=(1~2), 5=(4~3)'. Ranges apply: '1..3~4' = '1~2~3~4'. Separator '~'. Decoder reconstructs pairwise: frags[a+b], then frags[result+c], etc.
  params: separator: '~' for pairwise composition, ranges via '..'
  triggers: M8A _emit_composition and _emit_ref_run
### [token-type] Format Marker: Ref-Body Separator  (src/tcf/composicional/syntax.py:434-453)
  desc: Transition separators in body: lit->lit: '*'; lit->ref: optional (if ref starts with ',' or '~'); ref->lit: '*' if lit terminates digit (prevents ref-mode parser consuming digit as continuation); ref->ref: ',' (inline). Detects term_seq flag from _escape_lit. Decoder: ',' continues ref expression, '*' terminates.
  params: separators: '*' (disambiguate lit/ref), ',' (ref continuation), term_seq flag
  triggers: M8A emit_body phase for every piece transition
### [token-type] Format Marker: Virtual Alias Reference  (src/tcf/composicional/syntax.py:413-418, 755)
  desc: Caret prefix for repeated unique values: '^N' (single emit, bare ID), '*N|^N' (repeated emit N times). Used to reference earlier-emitted unique string without re-tokenization. Decoder: finds nos_decl[N-1].
  params: prefix: '^', ID: 1-indexed into nos_decl array
  triggers: M8A emit when is_rep=True (second+ occurrence of unique value)
### [categoria] Reserved Characters (All Layers)  (src/tcf/natures/templated_checked.py:34, src/tcf/composicional/syntax.py:65)
  desc: Complete reserved set (format vocabulary, no user literals allowed): { *, \, ~, ,, #, =, [, ], <, >, ", ', `, _, \n, \r, \t, space }. Nature encoder uses BASE94 (94 chars from ASCII 33-126 minus reserved). M8A escape routine handles *, \, ~ via \ prefix; digits via \d (run).
  params: _RESERVED = {\n, \r, \t, space, ',', '~', '*', '\\', '#', '=', '[', ']', '<', '>', '"', '\'', '`', '_'}, BASE94 alphabet: 50+ printable chars
  triggers: All encoding paths (literals, nature values)

**NOTES**: 
EXHAUSTIVE FORMAT INVENTORY:

SHEBANG (Line 1, multi-col only): '#TCF.6 M' (8 bytes) + newline. Dispatch decision in decode(). Absent in single-col.

META LINE (Line 2, multi-col only): '# size1=name1,size2=name2,...' (space after '#'). Parsed: split ',' then '=' (once per pair). Constraints: names cannot contain ',' or '='. Size=byte count of body. Order matches dict.

BODY (Lines 3+):
- Single-col: sequence of HCC-encoded line values
- Multi-col: column bodies concatenated byte-precise (no separators)

LINE ENCODING (HCC Output):
- RLE marker (M8A+M10): '*N|value' (N>=2). Decimal count, separator '|'
- Seq-RLE marker (M10): '*N+delta|template' or '*N+d1,d2,...|template'. M10-compat uniform or ADR-0016 mixed per-run
- Atomic ref range (M1.E): 'a..b' (3+ consecutive), '1,2,3' (bare). Threshold=3, separator='..'
- Composition chain (M1.E): '1~2' (pairwise), '1~2~3' (chained). Decoder reconstructs pairwise
- Virtual alias ref (M8A): '^N' (single), '*N|^N' (repeated). 1-indexed into nos_decl
- Literal text (M8A, escaped): digits '\\d' (run), special '\\*' '\\\\' '\\~'. term_seq=True if ends with \\d
- Ref-body separators (M8A): '*' (lit-to-lit, lit-to-ref if starts with ',' or '~', ref-to-lit if starts digit or term_seq), ',' (ref-to-ref)

RESERVED CHARACTERS (all layers): {*, \\, ~, ,, #, =, [, ], <, >, \", ', `, _, \\n, \\r, \\t, space}. Total 19 (18 printable + whitespace). BASE94 uses 50+ remaining. Marker '_' (MARKER_LITERAL) distinguishes nature-encoded vs literal.

BACKWARD COMPAT: M9 (no seq-RLE) fully readable as M10 subset. cfg toggles allow selective M9. Old pre-ADR-0013 multi without shebang not auto-detected. Brackets '[' ']' skipped for back-compat.

SIDE OUTPUTS FIELDS (optional): Per-col: column_features, cadence_detected, cadence_info, min_len, obat_log, obat_used_hint, hcc_trace, hcc_rede, seq_rle_runs, body_bytes. Multi-col: multi_info, per_col dict.

CRITICAL BYTE-CANONICAL PATHS: (1) Dedup OrderedDict.keys() order, (2) Dict iteration order + parallel reorder, (3) OBAT tie-break > strict, (4) HCC detector Counter order + net tie-break, (5) M1.E threshold=3, (6) Seq-RLE greedy consume, (7) Shape preservation exact->wider->canonical, (8) Composition pairwise left-to-right.

WHAT EACH SUBSYSTEM EMITS: CAMADA 0 (Nature): '_' prefix marker. CAMADA 1 (Pre-pass): cadence_info, min_len. CAMADA 2 (OBAT): tokens, log. CAMADA 3a (M8A): body with *, |, ^, ~, ,, ranges. CAMADA 3b (M10): '*N+delta|', '*N+d1,...|'. Multi wrapper: '#TCF.6 M', '# size=name,...', parallel_workers.

PINCH POINTS FOR V2: Nature (new categories inherit protocol), OBAT (shape preservation fallback chain), HCC (detector subclass), Multi-col (meta line delimiters), Side outputs (new Optional fields).

