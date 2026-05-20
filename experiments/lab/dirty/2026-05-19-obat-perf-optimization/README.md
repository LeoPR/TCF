---
title: 2026-05-19 — OBAT performance optimization
type: dirty-lab
status: active
tags: [obat, performance, scale, profiling, lineitem]
created: 2026-05-19
related:
  - experiments/lab/clean/EXP-014-tpch-lineitem-scale/
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
  - src/tcf/core/online.py
---

# 2026-05-19 — OBAT performance optimization

**Predecessor**: EXP-014 (encode O(N^1.75) confirmado, lineitem full
estimado 71 min).

**Pergunta cientifica**: OBAT canonical (`src/tcf/core/online.py`)
escala em O(N²) por causa do loop `_melhor_pref` / `_melhor_suf` que
itera todas anteriores. **E' possivel reduzir a O(N log N) ou O(N)
amortizado via index (hash/trie) preservando byte-canonicidade?**

## Por que primeiro

Analise comparativa de 5 candidatos pos-EXP-014 (caixeiro viajante
style):

1. **OBAT perf optimization** ← **esta aqui**
2. Pacote 2 (escape-deduction H-ED-01..04)
3. Multi-table single .tcf format
4. H-DA-09c tuning threshold v2.1
5. Lineitem full 60175 encode

**#1 desbloqueia #5 e viabiliza #3 em escala**. Sem #1, qualquer
experimento real-world em volume e' proibitivo (71 min/dataset).
Independencia reversa: #1 nao precisa dos outros, os outros se
beneficiam.

## Plano (3 sub-experimentos)

```
01-profile-baseline/    ← identifica hotspots (cProfile em 5000 rows)
02-index-prototypes/    ← testa hash/trie alternativas isoladas
03-welding-decision/    ← escolhe + integra + valida byte-canonical
```

## Restricoes (NUNCA quebrar)

1. **Byte-canonical em D1-D9** (1615 bytes, M9 baseline). Qualquer
   otimizacao que mude bytes = REJEITADA.
2. **src/tcf intocado** ate sub-exp 03 fechar com ADR aprovado.
3. **RT 100% em todas escalas testadas** (1k-20k lineitem).

## Aceite

- Profile identifica top-3 hotspots (>50% tempo cumulativo)
- Prototype isolado melhora encode em pelo menos 5x sem afetar bytes
- Welding decision documentada em ADR
- Re-run EXP-014 mostra alpha < 1.5 (linear-ish)

## Hipoteses

- **H-PERF-01**: `_melhor_pref` + `_melhor_suf` dominam (>60% tempo).
  Causa: comparacao linear contra todas anteriores. **a-validar via
  profile (01)**.
- **H-PERF-02**: indexar prefixos/sufixos via hash de bigramas
  reduz busca a O(N) amortizado preservando byte-canonical (mesma
  escolha de match, mesma tie-break). **a-validar via prototype (02)**.

## See also

- [EXP-014](../../clean/EXP-014-tpch-lineitem-scale/) — caracterizacao
- [OBAT spec](../../../../docs/algorithms/OBAT.md) — algoritmo canonical
- [src/tcf/core/online.py](../../../../src/tcf/core/online.py) — codigo alvo
