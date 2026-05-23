---
title: T-EXP-H-DA-09c-d-e — Refinos detect_cadence (threshold/multivariada/adaptativo)
status: closed
resolution: no-go-threshold-07-otimo
priority: P3
created: 2026-05-23
updated: 2026-05-23
closed: 2026-05-23
blocked-by: []
related:
  - docs/adr/0008-detect-cadence-numeric-rule.md
  - docs/adr/0011-pacote1-weld-canonical.md
  - experiments/lab/dirty/2026-05-23-h-da-09c-d-e-refinos-cadence/
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
---

# T-EXP-H-DA-09c-d-e — Refinos detect_cadence

## Contexto / motivacao

detect_cadence (welded ADR-0008 + canonical ADR-0011) usa 2 regras:
- Regra 1: lengths uniformes + LCP+LCS/length >= **0.7** (arbitrario)
- Regra 2: numeric + cardinality > **0.5** (refino ADR-0008)

Hipoteses decorrentes do sub-exp 09 do Pacote 1:
- **H-DA-09c**: tunar threshold da regra 1 (0.5 vs 0.6 vs 0.7 vs 0.8)
- **H-DA-09d**: heuristica multivariada (lengths + LCP+LCS + variance)
- **H-DA-09e**: re-avaliar heuristica a cada N strings (adaptativo)

Quaisquer dessas mudanças tem **ganho potencial incremental** (talvez
2-5% real-world weighted adicional). Custo baixo se for so' mudar
constantes.

## Plano

Lab dirty: `experiments/lab/dirty/2026-05-23-h-da-09c-d-e-refinos-cadence/`

### Sub-exp 01 — H-DA-09c varrer threshold

Pra cada coluna real-world (Adult+TPC-H 57 cols) + D1-D9 controle:
- Encode com threshold {0.5, 0.6, 0.7, 0.8}
- Comparar bytes per col + agregado weighted
- Identificar melhor threshold global

**Criterio go**: se algum threshold da ganho weighted >= 2% sem
regressao significativa em D1-D9 baseline.

### Sub-exp 02 (condicional) — H-DA-09d multivariada

Se Sub-exp 01 mostrar que NO threshold unico funciona (alguns datasets
preferem 0.5, outros 0.8): heuristica multivariada faria sentido.

### Sub-exp 03 (condicional) — H-DA-09e adaptativo

Se H-DA-09d nao bastar: adaptativo (re-avaliar threshold por
sub-segmentos da coluna).

## Criterio de aceite

- [ ] Sub-exp 01 com tabela bytes per (col, threshold)
- [ ] Decisao go/no-go documentada (>= 2% weighted)
- [ ] (se go) decisao sobre H-DA-09d/e

## Riscos

1. **Threshold 0.7 ja' otimo**: tuning pode dar 0% ou marginal.
2. **Per-col differ**: melhor threshold pode variar por col,
   requerendo H-DA-09d/e (mais complexos).
3. **Welding sem ADR novo**: se so' muda constante 0.7→X, talvez
   nao precise ADR formal — apenas commit + roadmap update.

## Conexoes

- [ADR-0008 detect_cadence](../docs/adr/0008-detect-cadence-numeric-rule.md)
- [ADR-0011 Pacote 1 canonical](../docs/adr/0011-pacote1-weld-canonical.md)
- [Roadmap H-DA-09c/d/e](../experiments/lab/dirty/notas/roadmap-hipoteses.md)

## Updates datados

### 2026-05-23 — abertura

Ticket criado seguindo convencao YAML frontmatter. Refinos decorrentes
do sub-exp 09 do Pacote 1 (welded). Priority P3 — incremental sobre
ADR-0008/0011.

### 2026-05-23 — Sub-exp 01 H-DA-09c: NO-GO

Varreu threshold {0.5, 0.6, 0.7, 0.8} em 66 colunas (9 D1-D9 + 57 real).

| Cohort | thr=0.5 | thr=0.6 | thr=0.7 (default) | thr=0.8 |
|---|---:|---:|---:|---:|
| Total | 918,431 | 918,431 | **891,237** | 891,237 |
| Real-world (57) | 916,908 | 916,908 | **889,714** | 889,714 |
| Sintetico (9) | 1,523 | 1,523 | **1,523** | 1,523 |

Distribuicao "melhor threshold" per col:
- thr=0.5: 63/66 cols (mas TOTAL maior — IGUAL ao 0.7 em quase todas)
- thr=0.6: 0/66
- thr=0.7: 3/66 (estritamente melhor — cadence dispara em 0.5 mas
  shape-preserve nao ajuda em alguns casos especificos)
- thr=0.8: 0/66

**Veredito**: threshold 0.7 atual e' robusto e otimo.
- Tunar pra baixo (0.5/0.6) introduz REGRESSAO real-world -3.06% weighted
  (cadence dispara em colunas onde shape-preserve nao ajuda)
- Tunar pra cima (0.8) nao muda nada (mesmas cadences disparam)

**H-DA-09d (multivariada) + H-DA-09e (adaptativo)**: adiados.
Heuristica atual ja' bem calibrada. Refinos teriam ganho marginal
similar (provavelmente ~0%).

**Resolution**: no-go-threshold-07-otimo.

**Aprendizado meta** (consolidando padrao desta sessao):
- Pacote 2 (escape): refutada
- Pacote 5 (enumerated): refutada
- H-DA-09c (threshold tune): refutada

TCF M10 esta bem calibrada. Refinos incrementais nas heuristicas
existentes provavelmente NAO dao ganhos significativos. Espaco de
melhoria restante:
1. Naturezas raras dataset-dependentes (financeiro/cientifico)
2. Performance (Cython/Rust H-PERF-06)
3. Bug fixes / robustness (todos os conhecidos ja' welded)
