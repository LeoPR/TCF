# 0008 — detect_cadence: adicionar regra para colunas numericas

**Status**: accepted
**Date**: 2026-05-19
**Deciders**: project owner
**Tags**: heuristic, detect-cadence, pre-stage, h-da-09b, real-world

## Context and Problem Statement

`detect_cadence` (sub-exp 09 do Pacote 1 / H-DA-09b) usa heuristica:
- lengths uniformes nas primeiras N strings
- LCP+LCS / length >= 0.7 em pares consecutivos

Em real-world (EXP-012 Adult Census + EXP-013 TPC-H), heuristica
detecta cadence em **0/76 colunas** (Adult) ou apenas em wrapper
patterns (TPC-H).

Audit em 76 colunas reais (sub-exp 01) mostrou:
- **HELP**: 12 cols (hint deveria estar enabled)
- **HURT**: 22 cols (hint deveria estar disabled)
- **NO-OP**: 42 cols (irrelevante)

Heuristica atual: captura **4/12 HELP** (perde 8 numericos).
Net: -113B (PIOR que always-off na soma).

## Considered Options

### Opcao A — Tunar threshold

Reduzir threshold de 0.7 → 0.5 ou 0.3. Capturaria mais HELP mas
TAMBEM mais HURT (false positives).

### Opcao B — Heuristica multivariada (numeric + cardinality)

Adicionar regra 2: `is_numeric AND cardinality > 0.5 → enable`.

Justificativa empirica:
- HELP avg cardinality: 0.905 (alta)
- HURT avg cardinality: 0.723
- HELP numeric_frac: 33%
- **HURT numeric_frac: 0%** (forte sinal!)

### Opcao C — Auto-tune por dataset

Tentar varios parametros e escolher empiricamente. Multi-pass, viola
single-pass.

### Opcao D — Probabilistic / ML

Treinar classifier nos audit data. Overhead alto, complexidade
desproporcional ao problema.

## Decision Outcome

**Opcao B — Adicionar regra numeric high-cardinality.**

Implementacao em `detect_cadence`:
```python
# Regra 1 (existente): wrapper+counter
if uniform_length AND all LCP+LCS >= threshold:
    return True

# Regra 2 (nova): numeric + high cardinality
if is_numeric AND cardinality > numeric_card_threshold:
    return True

return False
```

Onde `is_numeric` aceita int + float + negativos (via `float()`).

## Validacao empirica

### Sub-exp 02 (heuristica isolada em audit data)

| Metric | v1 (existente) | **v2 (refinada)** |
|---|---:|---:|
| TP (HELP captured) | 4 | **12** (todos) |
| FN (HELP missed) | 8 | **0** |
| FP (incorrect enable) | 8 | 15 (+7 NO-OP delta 0) |
| Bytes total | +113 (vs off) | **-448** (vs off) |
| Oracle ideal | — | -1626 |

### Sub-exp 03 (end-to-end EXP-012 + EXP-013)

| | Bytes total | vs raw |
|---|---:|---:|
| raw CSV | 3,077,395 | — |
| v1 (atual) | 2,421,316 | 78.7% |
| **v2 (refinada)** | **2,285,678** | **74.3%** |
| **Gain** | **-135,638 B** | **-5.6%** |

RT 12/12 OK em todas as combinacoes (4 volumes Adult + 8 tabelas TPC-H).

Maiores ganhos absolutos:
- tpch.partsupp 5000 rows: -44,809B (ps_supplycost numeric high-card)
- tpch.orders 5000 rows: -43,949B (o_totalprice, o_custkey)
- tpch.lineitem 5000 rows: -21,728B (l_partkey, l_extendedprice)
- adult 5000 rows: -19,766B (fnlwgt numeric)

## Pros and Cons

| Opcao | Pros | Cons |
|---|---|---|
| A (tunar threshold) | Simples | Insuficiente: numericos nao tem LCP+LCS alto |
| **B (numeric+card)** | Captura todos HELP; baseado em sinal forte (HURT 0% numeric) | +7 NO-OP FPs (custo zero) |
| C (auto-tune) | Adaptativo | Viola single-pass |
| D (ML) | Potencialmente otimo | Overhead, manutencao |

## Justificativa pra mexer em EXP-010 (clean)

EXP-010 e' prototype clean (v0.6→v0.7 candidato). Fix vive aqui ate'
welding em src/tcf canonical (futuro). Por enquanto, src/tcf nao
precisa mudar — heuristica vive em `auto_pre.py` do prototype.

## Validacao multi-camada pos-welding

| Camada | Antes | Depois |
|---|---|---|
| EXP-007 (D1-D9 byte-canonical) | 1615B, 9/9 OK | **1615B, 9/9 OK** |
| EXP-010 (20 datasets) | RT 20/20 OK | **RT 20/20 OK** |
| EXP-011 (D17a) | RT OK | **RT OK** |

Zero regressao.

## Riscos residuais

- Cardinalidade threshold 0.5: arbitraria. Pode ser tunada.
- `is_numeric` aceita exponential notation ("1e5"): pode ser
  excessivo em casos especificos. Nao observado problema ate' agora.
- 7 NO-OP FPs em sub-exp 02: custo zero, ignoravel.

## Hipoteses decorrentes (registrar)

- **H-DA-09c-v2** (re-aberta): tunar threshold (0.5 vs 0.6 etc.)
  pode capturar mais HELP edge cases
- **H-DA-09d** (multivariada full): cardinality + lengths + ratio
  combinados em score

## Cross-references

- [ADR-0003](0003-tripartite-pre-obat-hcc.md) — tripartite original
- [Sub-exp 09 Pacote 1](../../experiments/lab/dirty/2026-05-17-OBAT-delta-aware/09-auto-detect-cadence-heuristic/) — H-DA-09b original
- [Lab H-DA-09b refino](../../experiments/lab/dirty/2026-05-19-h-da-09b-refino-real-world/)
- [EXP-012 Adult](../../experiments/lab/clean/EXP-012-real-world-adult-census/)
- [EXP-013 TPC-H](../../experiments/lab/clean/EXP-013-real-world-tpch/)
