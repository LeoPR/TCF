---
title: 2026-05-20 — HCC perf optimization (H-PERF-05) [ADIADO]
type: dirty-lab
status: closed-adiado
tags: [hcc, performance, detect-compositions, h-perf-05, adiado]
created: 2026-05-20
closed: 2026-05-20
related:
  - tickets/META-PERF-PHASE2.md
  - experiments/lab/dirty/2026-05-19-obat-perf-optimization/
  - docs/adr/0009-obat-trigram-index-optimization.md
---

# 2026-05-20 — HCC perf optimization (H-PERF-05) — **ADIADO**

**Conclusao 2026-05-20**: 6 variantes testadas (sub-exps 01-03).
Zero-risk so' deu 1.04x (insuficiente para justificar welding em
syntax.py canonical ja' modificado por ADR-0006/0007). Caps trazem
byte loss 3-6% violando regra invariante M9.

Hipoteses fechadas:
- H-PERF-05a (cache): adiada (cache hit baixo)
- H-PERF-05b (counting direto): confirmada empirica MARGINAL (1.03x)
- H-PERF-05c (skip trace/rede): confirmada empirica MARGINAL (1.04x)
- H-PERF-05e (cap K): refutada-parcial
- H-PERF-05f (cap iter): refutada (byte loss trade-off ruim)

**Permanece aberta**: H-PERF-05d (counter incremental) — zero-risk
teorico, ganho potencial alto, mas implementacao complexa. Candidato
a phase 3 se HCC perf virar prioridade.

Ver [META-PERF-PHASE2](../../../../tickets/META-PERF-PHASE2.md)
(closed-parcial) pra status consolidado do Pacote 4.

# 2026-05-20 — HCC perf optimization (H-PERF-05) [original]

**Predecessor**: [Pacote 4 sub-pacote 1](../2026-05-19-obat-perf-optimization/) +
[ADR-0009](../../../../docs/adr/0009-obat-trigram-index-optimization.md)
(OBAT hash trigrama welded). Pos-OBAT-opt, HCC `_detect_compositions`
virou gargalo dominante (~40% relativo do encode).

**Lab paralelo abortado**: [`2026-05-20-obat-perf-phase2-trigram-middle/`](../2026-05-20-obat-perf-phase2-trigram-middle/)
(H-PERF-04, adiado por inviabilidade byte-canonical em datas).

## Pergunta cientifica

HCC `_detect_compositions` consumiu 24% do encode lineitem 5k
(63s/259s pre-otimizacao OBAT). Pos-ADR-0009 OBAT, vira ~40% relativo.
**Onde exatamente o tempo e' gasto e como reduzir preservando
byte-canonical?**

Profile preliminar (sub-exp 01 do lab OBAT) ja' mostrou:
- `_detect_compositions`: 35.4s self / 63.1s cumulative (16 calls, 1/coluna)
- `_estimate_baseline_chars`: 8.5s self / 16.4s cumulative (1.1M chamadas)
- Built-ins dentro: `sum` 1.4M, `min` 1.1M, genexpr 4.3M

## Plano (3 sub-experimentos)

```
01-profile-hcc/         ← cProfile focado em _detect_compositions
02-prototipos/          ← variantes (cache, K-cap, incremental)
03-welding-decision/    ← validar byte-canonical + integrar
```

## Algoritmo atual (resumo)

`_detect_compositions` em `src/tcf/composicional/syntax.py` (~linha 225):

```python
while True:  # outer loop
    contagem = Counter()
    for li, pieces in enumerate(pieces_per_line):
        for p in pieces:
            if p[0] == 'refs':
                refs = p[1]
                for a in range(len(refs)):              # O(R)
                    for b in range(a + 2, len(refs) + 1): # O(R)
                        sub = tuple(refs[a:b])            # O(R^2)
                        contagem[sub] += 1

    # filtros candidates (1 virtual / no overlap)
    # _estimate_baseline_chars per candidate
    # pick best, substitute
    # repeat until no improvement
```

## Hipoteses de otimizacao

- **H-PERF-05a**: cache de `_estimate_baseline_chars` (sub-tuplas
  repetem entre iteracoes outer)
- **H-PERF-05b**: cap K maximo de sub-tupla (K=10? subs longas raramente
  vencem)
- **H-PERF-05c**: counter incremental (em vez de refazer Counter
  from scratch cada iteracao outer)
- **H-PERF-05d**: filtrar contagem >=2 antes do build candidates
  (mover cedo)
- **H-PERF-05e**: substituir Counter por dict simples (overhead Counter)

## Restricoes (NUNCA quebrar)

1. D1-D9 = 1615B (M9 baseline)
2. RT 100% em EXP-007/010/011/012/013/014
3. Bytes IDENTICOS em lineitem 1k/5k/10k/20k
4. NAO degradar nenhum dataset

## Aceite

- Pelo menos uma otimizacao: encode lineitem 5k <30s (vs 40.5s atual,
  meta 25% redução)
- RT 100%, bytes IDENTICOS
- Welding em src/tcf/composicional/syntax.py com cuidado extra
  (ja modificado em ADR-0006 + ADR-0007; re-validacao multi-camada
  obrigatoria)

## See also

- [META-PERF-PHASE2](../../../../tickets/META-PERF-PHASE2.md)
- [src/tcf/composicional/syntax.py](../../../../src/tcf/composicional/syntax.py) — alvo
- [Lab OBAT (sub-pacote 1)](../2026-05-19-obat-perf-optimization/) — modelo metodologico
