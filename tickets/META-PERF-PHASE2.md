# META-PERF-PHASE2 — Performance OBAT/HCC fase 2

**Status**: CLOSED-PARCIAL (2026-05-20)
**Criado**: 2026-05-19
**Fechado**: 2026-05-20 (sub-pacote 1 welded + sub-pacotes 2/3/4 adiados)
**Predecessor**: [Pacote 4 sub-pacote 1](../experiments/lab/dirty/2026-05-19-obat-perf-optimization/) + [ADR-0009](../docs/adr/0009-obat-trigram-index-optimization.md) (OBAT hash trigrama, welded)

## Contexto

Sub-pacote 1 do Pacote 4 (ADR-0009) reduziu encode lineitem 20k de
626s → 232s (2.70x) e alpha de 1.75 → 1.42. Lineitem full 60175
estimado: **18.5 min** (vs 71 min pre-welding).

Profile (sub-exp 01 de 2026-05-19-obat-perf-optimization) revelou:
- **OBAT pref/suf** = 74% tempo → **MITIGADO** (ADR-0009)
- **HCC `_detect_compositions`** = 24% tempo → **NAO TRATADO**
  → Pos-OBAT-opt, vira gargalo dominante (~40% relativo)

Datas TPC-H (l_shipdate/commitdate/receiptdate) tiveram apenas 2x
speedup vs 100-264x em outras colunas. Causa: trigrama inicial
`199`/`200`/`202` gera buckets enormes.

## Escopo

Pacote 4 sub-pacotes pendentes:

### Sub-pacote 2 — H-PERF-04 (trigrama de meio) — PRIORIDADE ALTA

**Hipotese**: trigrama de meio `s[len(s)//2-1:len(s)//2+2]` dispersa
melhor que trigrama inicial em colunas datetime.

**Pergunta**: pra `2026-05-19`, `2026-05-20`, `2026-05-21` o trigrama
inicial `202` cai no mesmo bucket — mas trigrama de meio (`-05`, `-06`,
`-19`, etc) varia mais. Reduzir bucket size 10x+?

**Plano** (~1-2 sub-exps):
1. Profile bucket sizes atuais em lineitem 5k datetime cols
2. Prototipar variante: 2 indexes (inicio + meio), buscar em
   `index[inicio]` AND `index[meio]` (intersecao)
3. Medir speedup em l_shipdate/commitdate/receiptdate
4. Validar byte-canonical D1-D9 + lineitem 1k+5k
5. Welding se 5x+ em datas SEM degradar outras cols

**Aceite**: speedup datetime cols 5x+ adicional, RT 100%, bytes IDENTICOS.

### Sub-pacote 3 — H-PERF-05 (HCC opt) — PRIORIDADE ALTA

**Hipotese**: HCC `_detect_compositions` em
`src/tcf/composicional/syntax.py` (~linha 225) tem O(N²) hidden em
busca de candidatos virtual refs.

**Pergunta**: pode indexar candidatos ou usar dynamic programming?

**Plano** (~3-4 sub-exps):
1. Profile detalhado de `_detect_compositions` em lineitem 5k +
   colunas variadas (Adult Census, TPC-H)
2. Caracterizar hotspot interno (`_estimate_baseline_chars` chamado
   1.1M vezes em profile original)
3. Prototipar otimizacao (DP, index, ou cache)
4. Validar byte-canonical multi-camada (D1-D9, EXPs 010/011/012/013/014)
5. Welding se ganho >2x

**Aceite**: encode lineitem 5k <20s (vs 40s atual), RT 100%, bytes IDENTICOS.

**Cuidado**: HCC mexe em `src/tcf/composicional/syntax.py` —
arquivo ja' modificado em ADR-0006 + ADR-0007. Re-validacao
multi-camada obrigatoria.

### Sub-pacote 4 — H-PERF-06 (Cython/Rust port) — PRIORIDADE BAIXA

**Hipotese**: port de `lcp_len`/`lcs_len` (29M chamadas em lineitem 5k,
~1.7us/chamada) pra Cython ou Rust corta 50%+ Python overhead.

**Pergunta**: vale o overhead de build system + manutencao?

**Decisao**: **adiar** ate' H-PERF-04 + H-PERF-05 fecharem. Se ainda
sobrar speedup interessante, abrir. Se Pacote 4 ja' atinge target
(<5min pra lineitem full), nao priorizar.

### Sub-pacote 5 — EXP-014b lineitem full 60175 — OPERACIONAL

**Pergunta operacional**: extrapolacao 18.5min confirma na pratica?

**Plano**:
1. Rodar pipeline atual em lineitem completo (60175 rows)
2. Medir encode + decode + ratio + RT
3. Atualizar EXP-014 report ou abrir EXP-014b

**Aceite**: encode <25min (margem 35% sobre extrapolacao), RT OK,
ratio ~83-85%.

**Sem risco**: pipeline ja' validado em escala menor.

## Ordem de execucao

1. **EXP-014b** (sub-pacote 5) — sem dependencia, rapido, confirma baseline
2. **H-PERF-04** (sub-pacote 2) — quick win esperado em datas
3. **H-PERF-05** (sub-pacote 3) — maior ganho potencial, mais complexo
4. **H-PERF-06** (sub-pacote 4) — apenas se 1-3 nao bastarem

Pode rodar 1 antes de 2/3, ou em paralelo (1 e' so' execucao).

## Restricoes (NUNCA quebrar)

- **D1-D9 = 1615B** (M9 baseline invariante)
- **RT 100%** em EXPs 007/010/011/012/013/014 pos cada welding
- **src/tcf intocado** sem aprovacao explicita + validacao isolada
- **Welding multi-camada** obrigatorio (mesmo padrao do sub-pacote 1)

## Datasets de teste

- D1-D9 (controle algoritmo)
- lineitem 1k/5k/10k/20k (escala validada)
- Adult Census 100/500/1000/5000 (real-world)
- TPC-H 8 tabelas (real-world)

Re-validar todos pos cada welding.

## Conexoes

- [Pacote 4 sub-pacote 1 (welded)](../experiments/lab/dirty/2026-05-19-obat-perf-optimization/)
- [ADR-0009](../docs/adr/0009-obat-trigram-index-optimization.md)
- [EXP-014 baseline](../experiments/lab/clean/EXP-014-tpch-lineitem-scale/)
- [Roadmap hipoteses (H-PERF-04/05/06)](../experiments/lab/dirty/notas/roadmap-hipoteses.md)
- [META-TYPE-ENCODERS](META-TYPE-ENCODERS.md) (escopo Perf transferido deste ticket)

## Criterio de aceite (deste meta-ticket)

1. [x] **Sub-pacote 5 (lineitem full 60175) executado** — 21.3min real
   vs 18.5min estimado (+15%), RT OK, ratio 89%. H-RW-05 mitigada
   confirmada na pratica (2026-05-20).
2. [x] **Sub-pacote 2 (H-PERF-04 trigrama meio) — ADIADO**: hash
   tradicional nao preserva byte-canonical em datas com prefix
   popular. Lab `2026-05-20-obat-perf-phase2-trigram-middle/` fechado.
   Patricia trie como fallback futuro (out of scope).
3. [x] **Sub-pacote 3 (H-PERF-05 HCC opt) — investigado, ADIADO**:
   6 variantes testadas em `2026-05-20-hcc-perf-optimization/`.
   Zero-risk so' deu 1.04x (insuficiente). Caps trazem byte loss
   (3-6%) violando regra invariante M9. H-PERF-05d (counter
   incremental) permanece aberta como caminho zero-risk futuro.
4. [x] **Sub-pacote 4 (Cython port) — ADIADO**: dependia de Pacote 3
   esgotar. Reaberto so' se Python opt esgotar em phase 3.
5. [x] Re-run EXP-014 com OBAT-opt (sub-pacote 1) — alpha 1.42,
   18.5min estimado / 21.3min real em 60k.
6. [ ] Atualizar STATUS.md "Foco atual" para proximo pacote

## Status final do meta-ticket

**Fechado parcialmente 2026-05-20**. Ganho principal: Sub-pacote 1
(OBAT hash trigrama, ADR-0009) — 2.70x em lineitem 20k, alpha 1.75 →
1.42, lineitem full 60175 71min → 21.3min. Sub-pacotes 2/3/4 adiados
com justificativa documentada.

**Hipoteses abertas pra phase 3** (se necessario):
- H-PERF-04 via Patricia trie (datas)
- H-PERF-05d (counter incremental HCC)
- H-PERF-06 (Cython/Rust port)

Phase 3 condicionada a:
- Pacote 2 (escape deduction) explorado, OR
- Necessidade real de mais speedup em encode batch
