---
title: CAMADA 0 — Pre-pass: Column Feature Analysis, Cadence Detection, Min-Len Auto-detection
type: reference
parent: strategies-map
subsystem: prepass-filtros
---

# CAMADA 0 — Pre-pass: Column Feature Analysis, Cadence Detection, Min-Len Auto-detection

**Como decide caminhos**:
PIPELINE CANONICO M10 em encoder.py _encode_column(encoder.py:117-178):

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

### Estrategias (14)

| Nome | Kind | Local | Parametros | Triggers |
|---|---|---|---|---|
| **analyze_column** | estrategia | [src/tcf/column_features.py:51-84](../../../src/tcf/column_features.py) | sample_size=20 (tamanho amostra pra check is_numeric). Computacao O(N) on n_rows. | Sempre computa (barato, util pra side outputs). Entrada obrigatoria em encoder.p |
| **detect_cadence_from_features** | estrategia | [src/tcf/auto_cadence.py:28-96](../../../src/tcf/auto_cadence.py) | n_sample=5 (tamanho amostra regra 1, default primeiras 5 unicas). threshold=0.7 (limiar ratio LCP+LC | Disparada em encoder.py:141 IF cfg.pre_pass=True. Entrada: ColumnFeatures pre-co |
| **detect_min_len_from_features** | estrategia | [src/tcf/auto_min_len.py:25-68](../../../src/tcf/auto_min_len.py) | n_threshold=100 (lower gating: n<100→return 3, datasets pequenos recebem default seguro). Thresholds | Disparada em encoder.py:142 IF cfg.pre_pass=True. Entrada: ColumnFeatures pre-co |
| **_is_numeric_string** | helper | [src/tcf/column_features.py:26-34](../../../src/tcf/column_features.py) | Nenhum parametro; logica fixa float() try-except. | Disparada por analyze_column:75 para cada string em sample (sample_size=20). Res |
| **processar_with_hint** | estrategia | [src/tcf/obat_shape.py:64-120](../../../src/tcf/obat_shape.py) | prefer_shape_consistency={True\|False} (toggleavel via cfg.obat_shape_preserve=True default). min_le | Disparada em encoder.py:150-155 baseado em cadence_detected AND cfg.obat_shape_p |
| **_try_preserve_shape** | helper | [src/tcf/obat_shape.py:32-61](../../../src/tcf/obat_shape.py) | Nenhum parametro configuravel; logica deterministica. | Disparada por processar_with_hint:92 IF prefer_shape_consistency=True AND last_s |
| **PipelineConfig** | marcador | [src/tcf/pipeline.py:35-60](../../../src/tcf/pipeline.py) | 3 boolean flags, todos default=True → M10 canonical invariant. | Passado via layers= param em encode() (encoder.py:60). Usado em _encode_column ( |
| **lcp_len (Longest Common Prefix)** | helper | [src/tcf/core/online.py:59-64](../../../src/tcf/core/online.py) | Nenhum; logica fixa. | Disparada por detect_cadence_from_features:70 em cada par (sample[i-1], sample[i |
| **lcs_len (Longest Common Suffix)** | helper | [src/tcf/core/online.py:67-72](../../../src/tcf/core/online.py) | Nenhum; logica fixa. | Disparada por detect_cadence_from_features:71 em cada par. Disparada por _try_pr |
| **Cardinality Threshold (0.5, 0.2, etc)** | threshold | [src/tcf/auto_cadence.py:33, src/tcf/auto_min_len.py:56-66](../../../src/tcf/auto_cadence.py) | 0.5 (numeric_card_threshold), 0.2/0.4/0.7/0.8 (implicit em auto_min_len). Tunaveis, nenhum exposto v | Usados em detect_cadence_from_features:87 (Regra 2) e detect_min_len_from_featur |
| **Average Length Buckets** | threshold | [src/tcf/auto_min_len.py:58-66](../../../src/tcf/auto_min_len.py) | Buckets fisos: {3, 5, 8, 12, 25}. Tunaveis, nenhum exposto API publica. | Usados em detect_min_len_from_features:58-66 (decision tree sequencial). |
| **LCP+LCS Ratio Threshold (0.7)** | threshold | [src/tcf/auto_cadence.py:32, linha 76](../../../src/tcf/auto_cadence.py) | threshold=0.7 (default, parametro tunable em detect_cadence_from_features). | Usado em detect_cadence_from_features:76 condicao ALL ratios >= threshold. |
| **n_rows Gating (n >= 100)** | decision-point | [src/tcf/auto_min_len.py:49-50](../../../src/tcf/auto_min_len.py) | n_threshold=100 (limite gating, tunable via detect_min_len_from_features param). Default M9 ml=3 qua | Avaliada primeira em detect_min_len_from_features:49 ANTES de decision tree. |
| **Sample Size (n_sample=5)** | threshold | [src/tcf/auto_cadence.py:31, linha 59](../../../src/tcf/auto_cadence.py) | n_sample=5 (default, tunable). | Usado em detect_cadence_from_features:59 pra limitar analise a primeiras N unica |

### Detalhamento

**`analyze_column`** (estrategia, [src/tcf/column_features.py:51-84](../../../src/tcf/column_features.py))  
Computa features basicas de uma coluna em 1 passada O(N) sobre values. Extrai: n_rows (total), n_unicas (distinct count), avg_len (media de comprimentos), cardinality (n_unicas/n_rows como razao), is_numeric (check amostragem), sample (tuple de primeiras N strings para analises posteriores). is_numeric eh True somente se TODAS strings do sample parsam float(). Edges: coluna vazia retorna features zerados com is_numeric=False. Sample padrao=20.

**`detect_cadence_from_features`** (estrategia, [src/tcf/auto_cadence.py:28-96](../../../src/tcf/auto_cadence.py))  
2-regra heuristica pra detectar se coluna tem cadencia estrutural (justifica usar processar_with_hint com prefer_shape_consistency=True). Regra 1 (wrapper+counter): lengths uniformes em primeiras n_sample strings E (LCP+LCS)/L >= threshold em TODOS pares consecutivos → rule_hit='1-uniform-length-high-lcp-lcs'. Regra 2 (numeric high-card, ADR-0008): is_numeric=True AND cardinality > numeric_card_threshold → rule_hit='2-numeric-high-cardinality'. Retorna (bool, dict info) onde info contem rule_hit, reasoning, lcp_lcs_ratios se aplicavel, cardinality, is_numeric. Requer len(strings_unicas) >= 2; senao retorna False+reason='muito poucas strings'.

**`detect_min_len_from_features`** (estrategia, [src/tcf/auto_min_len.py:25-68](../../../src/tcf/auto_min_len.py))  
Heuristica v3 (shallow decision tree) auto-detecta min_len otimo baseado em avg_len, cardinality, is_numeric. Decision tree com gating (n < n_threshold→3) + 6 regras sequenciais (primeira match wins): card<0.2→3 (baixa-card seguro), avg_len>=25→6 (long-form), avg_len>=8 AND card>=0.4→6 (dates/mid-len high-card), avg_len>=5 AND is_numeric AND card>=0.8→6 (numeric high-card), avg_len>=12 AND card>=0.7→5 (phone-like), avg_len>=3 AND card>=0.2→4 (IDs sequenciais), else→3. Captura 99.5% do oracle (melhor min_len possivel) em 58 colunas real-world (Adult+TPC-H). Gating n<100 preserva M9 baseline EXATO (1615B D1-D9).

**`_is_numeric_string`** (helper, [src/tcf/column_features.py:26-34](../../../src/tcf/column_features.py))  
Helper que determina se uma string individual eh numerica (aceita int, float, negativos, exponencial '1e5'). Implementacao: try float(v) return True, except ValueError/TypeError return False. Empty string retorna False. Usado em analyze_column para compor is_numeric field (sample-based check).

**`processar_with_hint`** (estrategia, [src/tcf/obat_shape.py:64-120](../../../src/tcf/obat_shape.py))  
Variante de OBAT tokenizer com dica opcional prefer_shape_consistency. Quando False, comporta-se identico ao processar() canonical. Quando True: apos cada string emitida, memoriza shape=(p_src, p_len, has_L, s_src, s_len); pra proxima string, tenta replicar exatamente via _try_preserve_shape. Fallbacks: (1) exato: lcp_avail>=p_len_old AND lcs_avail>=s_len_old, (2) wider: reduz p_len/s_len a max possivel se exato falhar (lcp_avail, lcs_avail), (3) greedy: cai pra OBAT canonical se nem wider funciona. Input: strings_unicas (deduplicated), min_len (from pre-pass), prefer_shape_consistency (from cadence detection). Output: (tokens_por_string, log_string).

**`_try_preserve_shape`** (helper, [src/tcf/obat_shape.py:32-61](../../../src/tcf/obat_shape.py))  
Tenta replicar last_shape em string s. Valida: last_shape deve ter has_L=True (literal existe entre prefix e suffix), p_src/s_src devem estar em range (idx_limit). Calcula lcp_avail/lcs_avail contra s e prev strings. Tenta exato (lcp_avail>=p_len_old AND lcs_avail>=s_len_old); se falhar, tenta wider reduzindo ambos a minimo disponivel, validando new_len > 0 e ambos >= min_len. Retorna (p_src, p_len, s_src, s_len) tupla ou None.

**`PipelineConfig`** (marcador, [src/tcf/pipeline.py:35-60](../../../src/tcf/pipeline.py))  
Dataclass frozen com 3 boolean toggles controlando CAMADA 0-3 comportamento. pre_pass (default=True): ativa analyze_column+detect_cadence+detect_min_len. obat_shape_preserve (default=True): usa processar_with_hint com hint=True se cadence detected. hcc_seq_rle (default=True): aplica HCCSeqRLE vs M8AVirtualRefsSyntax. Default singleton DEFAULT_PIPELINE = PipelineConfig() equivale a M10 canonical. Motivacao: ablation + debug sem hardcode.

**`lcp_len (Longest Common Prefix)`** (helper, [src/tcf/core/online.py:59-64](../../../src/tcf/core/online.py))  
Computa LCP length entre duas strings a,b via scan caractere-por-caractere ate' mismatch ou fim da menor string. Usa min(len(a), len(b)) como limite. O(min(|a|,|b|)) simples. Usado em detect_cadence para computar ratio (lcp+lcs)/L em pares consecutivos (regra 1), e em obat_shape para validar se pode replicar shape anterior.

**`lcs_len (Longest Common Suffix)`** (helper, [src/tcf/core/online.py:67-72](../../../src/tcf/core/online.py))  
Computa LCS length entre duas strings a,b via scan de tras pra frente (indices negativos) ate' mismatch. O(min(|a|,|b|)). Dual de lcp_len. Mesmos usos em detect_cadence + obat_shape.

**`Cardinality Threshold (0.5, 0.2, etc)`** (threshold, [src/tcf/auto_cadence.py:33, src/tcf/auto_min_len.py:56-66](../../../src/tcf/auto_cadence.py))  
Multiplos thresholds de cardinalidade (razao n_unicas/n_rows) usados em decisoes: (1) numeric_card_threshold=0.5 em detect_cadence Regra 2 (valores numericos com >50% distinct → cadence estrutural, ADR-0008). (2) Implicit thresholds em detect_min_len: card<0.2→ml=3, card>=0.2→ml=4, card>=0.4→ml=6 (com avg_len), card>=0.7→ml=5. (3) card>=0.8 com is_numeric+avg_len>=5→ml=6. Empirico em 58 colunas reais; pode nao generalizar a datasets novos.

**`Average Length Buckets`** (threshold, [src/tcf/auto_min_len.py:58-66](../../../src/tcf/auto_min_len.py))  
Decision tree em auto_min_len usa buckets de avg_len (media tamanho string na coluna) como gating: avg_len<3→ml=3 (default), avg_len>=3 AND card>=0.2→ml=4, avg_len>=5 (+ is_num+card>=0.8)→ml=6, avg_len>=8 (+ card>=0.4)→ml=6, avg_len>=12 (+ card>=0.7)→ml=5, avg_len>=25→ml=6. Empirico em real-world. Representa padrao: strings muito longas=higher min_len safe.

**`LCP+LCS Ratio Threshold (0.7)`** (threshold, [src/tcf/auto_cadence.py:32, linha 76](../../../src/tcf/auto_cadence.py))  
Regra 1 de detect_cadence requer que em TODOS os pares consecutivos do sample, (lcp+lcs)/L >= 0.7 (default). L = tamanho uniforme string. Threshold 0.7 significa >=70% dos caracteres em pair sao LCP ou LCS (comuns). Escolhido empiricamente para detectar wrapper+counter patterns (ex: wrapper='[' L=']', numeric counter no meio). Valor atual reflete ADR-0008 real-world validation (0.7 bom balance para HELP vs HURT).

**`n_rows Gating (n >= 100)`** (decision-point, [src/tcf/auto_min_len.py:49-50](../../../src/tcf/auto_min_len.py))  
Gating em detect_min_len_from_features: IF n_rows < n_threshold (100 default), return 3 (fallback seguro). Justificativa: datasets pequenos (D1-D9 sinteticos, n=12-20) com heuristica complexa pode quebrar M9 baseline invariant. Empirico: n<100 recebem default ml=3, preserva 1615B exato em D1-D9. Datasets reais (Adult/TPC-H n=1000-5000) passam gating, recebem heuristica completa.

**`Sample Size (n_sample=5)`** (threshold, [src/tcf/auto_cadence.py:31, linha 59](../../../src/tcf/auto_cadence.py))  
Tamanho da amostra de strings unicas para regra 1 (wrapper+counter) em detect_cadence. Default=5 significa primeiras 5 strings unicas sao analisadas pra uniformidade de length e ratios LCP+LCS. Escolha empirica: suficiente pra detectar pattern, sem overhead grande. Tunable via parametro detect_cadence_from_features(n_sample=...).

### Notas

SUBSISTEMA CAMADA 0 EXAUSTIVO — PRE-PASS UNIFICADO:

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

---
