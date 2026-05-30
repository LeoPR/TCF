---
title: CAMADA 2b — HCC seq-RLE + multi-delta (ADR-0016, welded canonical)
type: reference
parent: strategies-map
subsystem: hcc-seqrle
---

# CAMADA 2b — HCC seq-RLE + multi-delta (ADR-0016, welded canonical)

**Como decide caminhos**:
ENCODE: values → analyze_column (pre-pass, opcional) → detect_cadence → detect_min_len → OBAT tokenizes (processar ou processar_with_hint) → M8AVirtualRefsSyntax.encode() genera body_text (M9 puro, com refs/compositions) → HCCSeqRLE.encode() aplica compact_body (post-process seq-RLE) → output TCF.

DECODE: tcf_text → HCCSeqRLE.decode() expande seq-RLE markers (expand_seq_marker) → re-assembles text → M8AVirtualRefsSyntax.decode() (parent class) descodifica refs/compositions → output list[str] original.

MARKER DECISION LOGIC em compact_body:
1. detect_seq_runs identifica runs near-identical
2. Para cada run, checa _is_uniform_delta(deltas)
3. Se uniform (todos deltas = mesmo valor non-zero) → marker M10 format `*N+delta|template`
4. Senão (multi-delta com 1 non-zero, resto zeros) → marker CSV format `*N+d1,d2,d3|template`
5. Assemble output compacted + info metadata

Em decode, marker parser disambiguates automaticamente: ',' na delta_str → CSV (ADR-0016), senão int (M10).

### Estrategias (14)

| Nome | Kind | Local | Parametros | Triggers |
|---|---|---|---|---|
| **find_escape_digit_positions** | helper | [src/tcf/composicional/hcc_seqrle.py:31-44](../../../src/tcf/composicional/hcc_seqrle.py) | line: str → list[int] | sempre, quando precisa-se mapear estrutura escape-digit de uma linha |
| **find_escape_digit_runs** | estrategia | [src/tcf/composicional/hcc_seqrle.py:47-62](../../../src/tcf/composicional/hcc_seqrle.py) | line: str → list[tuple[int, int]] | sempre, pré-requisito pra compare_for_seq |
| **compare_for_seq** | decision-point | [src/tcf/composicional/hcc_seqrle.py:65-112](../../../src/tcf/composicional/hcc_seqrle.py) | line_a: str, line_b: str → list[int] \| None | em detect_seq_runs: testado entre cada par consecutivo de linhas no body |
| **_is_uniform_delta** | heuristica | [src/tcf/composicional/hcc_seqrle.py:176-183](../../../src/tcf/composicional/hcc_seqrle.py) | deltas: list[int] → int \| None | em compact_body, depois de detectar run near-identical |
| **shift_escape_digits** | estrategia | [src/tcf/composicional/hcc_seqrle.py:115-147](../../../src/tcf/composicional/hcc_seqrle.py) | template: str, delta: int \| list[int] → str | em expand_seq_marker (linha 272), por vez em cada iteração do loop count |
| **detect_seq_runs** | estrategia | [src/tcf/composicional/hcc_seqrle.py:150-173](../../../src/tcf/composicional/hcc_seqrle.py) | body_lines: list[str] → list[tuple[int, int, list[int]]] | em compact_body:187, depois de OBAT encode pra processar body lines |
| **compact_body** | estrategia | [src/tcf/composicional/hcc_seqrle.py:186-227](../../../src/tcf/composicional/hcc_seqrle.py) | body_lines: list[str] → tuple[list[str], list[dict]] | em HCCSeqRLE.encode, pós-super().encode |
| **expand_seq_marker** | estrategia | [src/tcf/composicional/hcc_seqrle.py:230-274](../../../src/tcf/composicional/hcc_seqrle.py) | linha: str → list[str] \| None | em HCCSeqRLE.decode, para cada linha que comeca com '*' |
| **HCCSeqRLE class + control flow** | estrategia | [src/tcf/composicional/hcc_seqrle.py:277-314](../../../src/tcf/composicional/hcc_seqrle.py) | none (class instancia) | em encoder.py e decoder.py, sempre que cfg.hcc_seq_rle=True (default) |
| **M10 backward compatibility threshold** | threshold | [src/tcf/composicional/hcc_seqrle.py:199-202](../../../src/tcf/composicional/hcc_seqrle.py) | none (condicional hardcoded) | sempre em compact_body, escolhe formato marker M10 vs CSV |
| **Fase 1 single non-zero restriction** | threshold | [src/tcf/composicional/hcc_seqrle.py:107-111](../../../src/tcf/composicional/hcc_seqrle.py) | none (hardcoded check) | em compare_for_seq:110, sempre ao validar multi-run |
| **Run equality invariant** | marcador | [src/tcf/composicional/hcc_seqrle.py:88-91](../../../src/tcf/composicional/hcc_seqrle.py) | none (structural check) | em compare_for_seq:90, sempre |
| **Escape-digit length check** | threshold | [src/tcf/composicional/hcc_seqrle.py:138-144](../../../src/tcf/composicional/hcc_seqrle.py) | width: int (end - start de run) | em shift_escape_digits:142, por run shifta |
| **Tokenizer OBAT integration point** | decision-point | [src/tcf/composicional/hcc_seqrle.py:1-24 (docstring)](../../../src/tcf/composicional/hcc_seqrle.py) | none (architectural) | em encoder.py:293-298, sempre no pipeline canonical |

### Detalhamento

**`find_escape_digit_positions`** (helper, [src/tcf/composicional/hcc_seqrle.py:31-44](../../../src/tcf/composicional/hcc_seqrle.py))  
Utility que mapeia posições (0-based) de cada char digit que vem após backslash (escape sequence). Itera string left-to-right, detecta '\' seguido de isdigit(), coleta indice de cada digit. Retorna lista vazia se nenhuma sequence escape-digit encontrada. Usado por find_escape_digit_runs e compare_for_seq pra localizar quais portions do template são 'numéricos' (candidatos a delta shift).

**`find_escape_digit_runs`** (estrategia, [src/tcf/composicional/hcc_seqrle.py:47-62](../../../src/tcf/composicional/hcc_seqrle.py))  
Detecta RUNS (intervalos consecutivos) de digits após escape. Retorna list[tuple[int, int]] (start, end_exclusive) de cada run. Ex: '\\125.\\114' → [(1,4), (6,9)]. Crítico pra distinguir multi-run (prefix invariante + suffix cadenced) de single-run. Usado como pivô em compare_for_seq pra rejeitar pares com estruturas runs diferentes.

**`compare_for_seq`** (decision-point, [src/tcf/composicional/hcc_seqrle.py:65-112](../../../src/tcf/composicional/hcc_seqrle.py))  
CRITERIO CENTRAL pra near-identical detection. Compara line_a e line_b; retorna list[int] de deltas (1 per run) se par é compactavel, None senão. Aceita: (1) single run com delta non-zero, (2) multi-run com EXATAMENTE 1 valor non-zero + resto zeros (ex: [0,0,0,1]). Rejeita: (1) len diferente, (2) diffs fora de escape-digit runs, (3) runs_a ≠ runs_b (estrutura diferente), (4) multiple non-zero diferentes (Fase 2 reject, linha 111), (5) all-zero (linhas identicas). ADR-0016: mudança chave vs M10 — agora aceita multi-delta [0,0,0,1] que antes rejeitava (Bug #2).

**`_is_uniform_delta`** (heuristica, [src/tcf/composicional/hcc_seqrle.py:176-183](../../../src/tcf/composicional/hcc_seqrle.py))  
Verifica se lista de deltas é UNIFORME (todos iguais e non-zero). Se sim, retorna aquele int único; senão None. Usado em compact_body (linha 199) pra decidir marker format: M10 compat `*N+delta|` (uniform) vs ADR-0016 CSV `*N+d1,d2,d3,d4|` (mixed). Threshold: all(d == deltas[0] and d != 0). Importante pra backward compatibility.

**`shift_escape_digits`** (estrategia, [src/tcf/composicional/hcc_seqrle.py:115-147](../../../src/tcf/composicional/hcc_seqrle.py))  
Aplica delta(s) a template pra gerar linha i+1, i+2, ... em run. Aceita delta como int (M10: mesmo delta em TODOS runs) ou list[int] (ADR-0016: per-run). Algorithm: (1) parse runs do template, (2) normalize delta pra list, (3) iterate runs + deltas em sync, (4) apply int(run_old) + d → new_val, (5) format com zfill(width) pra preservar leading zeros. Edge case: se len(deltas) ≠ len(runs), retorna template inalterado (safe fallback). Linha 142: zfill preserva 3-digit de IPs ex: '\\001' ∈ run → +1 → '\\002'.

**`detect_seq_runs`** (estrategia, [src/tcf/composicional/hcc_seqrle.py:150-173](../../../src/tcf/composicional/hcc_seqrle.py))  
DETECTOR SEQUENCIAL de runs near-identical. Itera body_lines, chama compare_for_seq em cada par consecutivo. Quando par aceitável, estende run enquanto proxima line mantém MESMO deltas. Retorna list[tuple[int, int, list[int]]] = (start_line, end_exclusive, deltas). Invariante: runs não se sobrepõem, sequential. Usado em compact_body. ADR-0016: deltas sempre list[int] (retorno de compare_for_seq mudou de int → list). Threshold pra extend run (linha 168): next_deltas == deltas (exato, não aproximado).

**`compact_body`** (estrategia, [src/tcf/composicional/hcc_seqrle.py:186-227](../../../src/tcf/composicional/hcc_seqrle.py))  
POST-PROCESS pós-encode. Detecta runs near-identical, substitui por markers. Decide marker format (M10 vs CSV): linha 199-210. Se uniform delta → M10 format `*count+delta|template` (compat). Senão → CSV `*count+d1,d2,...|template` (ADR-0016). Sign handling (linha 201, 209): prepend '+' apenas se delta[0] >= 0; negativo já inclui '-' via str(). Retorna (compacted_lines, info_dicts). Info dict inclui savings estimate (linha 219-220) = (sum(len original lines) + count-1) - len(marker). Invariante: cada marker ≥ 2 linhas (count >= 2).

**`expand_seq_marker`** (estrategia, [src/tcf/composicional/hcc_seqrle.py:230-274](../../../src/tcf/composicional/hcc_seqrle.py))  
DECODER REVERSO de markers. Parse `*N+delta|template` ou `*N+d1,d2,...|template`. Disambiguação (linha 255): if ',' in delta_str → CSV (ADR-0016) senão int (M10). Extracts count, deltas, template. Itera count vezes, aplicando shift_escape_digits incrementalmente. Linha 264: int(delta_str) parse single delta (compat M10). Linha 257: split(',') → list[int]. Returns list[str] de count linhas (template + shifted variantes), ou None se formato inválido.

**`HCCSeqRLE class + control flow`** (estrategia, [src/tcf/composicional/hcc_seqrle.py:277-314](../../../src/tcf/composicional/hcc_seqrle.py))  
Subclass de M8AVirtualRefsSyntax. Override encode/decode pra adicionar seq-RLE layer. ENCODE (linha 293-298): (1) chama super().encode → body_text (M9 canonical), (2) split em lines, (3) compact_body, (4) armazena seq_rle_info em _seq_info, (5) retorna compacted text. DECODE (linha 300-313): (1) itera tcf_text.splitlines(), (2) pra cada linha, tenta expand_seq_marker, (3) se marker → adiciona expanded lines, senão passes-through, (4) re-assembles texto expandido, (5) chama super().decode. Post-condition: bytes-exato round-trip (encode → decode == original).

**`M10 backward compatibility threshold`** (threshold, [src/tcf/composicional/hcc_seqrle.py:199-202](../../../src/tcf/composicional/hcc_seqrle.py))  
Mecanismo de preservação backward compat: se _is_uniform_delta retorna non-None (todos deltas iguais), emite marker M10 format `*N+delta|` (sem virgula). Datasets como D1-D9 (nenhum multi-run com mixed deltas) emit markers idênticos a versão M9, preservando byte-canonical invariant. Validado em test suite (19 novos tests em test_hcc_multi_delta.py, 211 total passam).

**`Fase 1 single non-zero restriction`** (threshold, [src/tcf/composicional/hcc_seqrle.py:107-111](../../../src/tcf/composicional/hcc_seqrle.py))  
ADR-0016 Fase 1 limitação: multi-delta só aceita 1 valor non-zero (resto zeros). Linha 110: if len(set(non_zero)) > 1 → return None (reject). Casos [1,2] ou [3,5] rejeitados — defer para Fase 2 (futuro). Justificativa: casos [0,0,0,1] são comuns (prefix invariante + suffix cadenced, ex: IPs), mas [1,2] raro em real-world datasets. Benchmark D-IP-subnet validou suficiência.

**`Run equality invariant`** (marcador, [src/tcf/composicional/hcc_seqrle.py:88-91](../../../src/tcf/composicional/hcc_seqrle.py))  
Estrutural: pares são aceitáveis APENAS se runs_a == runs_b (posições de escape-digit runs exatamente iguais). Se differs → None (reject). Impede false positives tipo '\\1' vs '\\1.\\2' (número de runs diferente, diferença não-linear). Crítico pra corretude shift_escape_digits.

**`Escape-digit length check`** (threshold, [src/tcf/composicional/hcc_seqrle.py:138-144](../../../src/tcf/composicional/hcc_seqrle.py))  
shift_escape_digits linha 141-144: quando aplicar delta a run, resultado new_val pode ter length diferente de original (ex: 99 + 1 = 100). zfill(width) preserva width (leading zeros); se new_str > width, não trunca (overflow preservado). Exemplo: \\99 + 1 → \\100 (width muda de 2 → 3). Necessario pra IPs com 3 dígits fixos.

**`Tokenizer OBAT integration point`** (decision-point, [src/tcf/composicional/hcc_seqrle.py:1-24 (docstring)](../../../src/tcf/composicional/hcc_seqrle.py))  
HCCSeqRLE é post-process em cima de OBAT tokenization (CAMADA 1) + M8A atom/composition detection (CAMADA 2a). Entrada é body_text já escape-lido (escape-digit runs via OBAT _escape_lit). Saída é compactação seq-RLE. Pipeline: OBAT tokeniza → M8A emits refs → body_text → HCCSeqRLE compacts → output TCF. Camadas são sequencial, não intercalado.

### Notas

CANONICAL STATE (v1.0 welded 2026-05-24):
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

---
