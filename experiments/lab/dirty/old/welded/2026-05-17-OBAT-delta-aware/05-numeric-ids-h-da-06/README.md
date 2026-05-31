# Sub-exp 05 — Numeric IDs (H-DA-06)

**Data**: 2026-05-17
**Estado**: ativo
**Macro pai**: [`../README.md`](../README.md)
**Hipotese**: H-DA-06 (`../../notas/roadmap-hipoteses.md`)

## Hipotese a validar

**H-DA-06**: O pipeline OBAT fork (shape-preserve) + HCC fork
(seq-RLE) — confirmado em datasets datetime D11a-h — generaliza
para outros tipos de delta? Especificamente: IDs numericos
sequenciais.

## Datasets (novos, criados para este sub-exp)

| Dataset | Conteudo | Cardinality transition | Linhas |
|---|---|---|---:|
| D16a-ids-3digits | "100", "101", ..., "112" | sim (9→10) | 13 |
| D16b-ids-4digits | "1000", "1001", ..., "1012" | nao (todos 4 digits) | 13 |
| D16c-ids-prefixados | "USR-100", ..., "USR-112" | sim (com prefixo) | 13 |

Escolhidos pra cobrir:
- D16a: caso analogo a D11d (transition 9→10 em sequencia numerica)
- D16b: controle sem transition (deveria ter ganho menor pra
  shape-preserve, pois ja' tem shape uniforme)
- D16c: prefix + numerico (mais realista; testa se prefix muda
  comportamento)

## Pipelines (mesmos do sub-exp 04)

| Pipeline | Descricao |
|---|---|
| Baseline | OBAT canonical + HCC canonical |
| t02 | OBAT canonical + HCC fork seq-RLE |
| sub-exp 04 | OBAT fork shape-preserve + HCC fork seq-RLE |

## Expectativas (pra falsificar)

| Dataset | t02 esperado | sub-exp 04 esperado |
|---|---|---|
| D16a | Bom ganho (s2-s9 pattern), s10-s12 fora | Ganho adicional (s10-s12 capturados) |
| D16b | Bom ganho geral (sem transition, shape uniforme) | Pouco ganho adicional (shape ja' uniforme) |
| D16c | Bom ganho (prefix fixo + var) | Ganho adicional similar a D11d |

Hipoteses derivadas:
- **H-DA-06a**: hint shape-preserve **nao prejudica** datasets sem
  transition (D16b) — comportamento equivalente a greedy
- **H-DA-06b**: gain pattern em D16c (com prefix) similar a D11d
  (sem prefix), confirmando que hint funciona em qualquer
  comprimento prefixo

## Restricoes herdadas

- src/tcf intocado
- Reusa `obat_fork.py` (sub-exp 04) e `hcc_fork.py` (sub-exp 02)
- Sem nova implementacao algoritmica (so' aplicacao)

## Estrutura

```
05-numeric-ids-h-da-06/
├── README.md
├── run.py             (reusa pipeline do sub-exp 04 em D16a-c)
├── summary.md
├── result.md
└── outputs/<ds>/
    ├── 1-tokens-canonical.txt
    ├── 2-tokens-fork.txt
    ├── 3-body-fork-canonical-obat.tcf
    ├── 4-body-fork-fork-obat.tcf
    ├── 5-rt-status.txt
    └── 6-diff-bodies.md
```
