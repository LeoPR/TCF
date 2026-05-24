---
title: T-EXP-MULTI-COL-SCALING — Port multi-column pra canonical M10 + real-world
status: closed-welded-canonical
priority: P1
created: 2026-05-23
updated: 2026-05-23
blocked-by: []
related:
  - experiments/lab/clean/EXP-011-multi-column-basic/
  - experiments/lab/dirty/2026-05-23-multi-column-scaling/
  - docs/adr/0004-multi-column-header-compacto.md
  - docs/adr/0011-pacote1-weld-canonical.md
---

# T-EXP-MULTI-COL-SCALING — Port multi-column canonical M10 + real-world

## Contexto / motivacao

EXP-011 (2026-05-17) validou multi-column basico em D17a sintetico
(13 x 4) usando `encode_column` do EXP-010 (prototype delta_aware,
M9 era). Desde entao:

- 2026-05-22: Pacote 1 canonical welded em src/tcf (M9 → M10, ADR-0011)
- Single-column real-world validado em EXP-012/013/014 (Adult, TPC-H)
- Multi-column real-world **nunca testado**

Lacuna: ate' agora multi-column tinha N=1 dataset, sem confirmacao
de scaling.

## Hipotese

- **H1**: Port `multi_col.py` pra canonical M10 preserva D17a baseline
  (322B + RT)
- **H2**: Multi-column em real-world (8 tabelas Adult+TPC-H) preserva
  RT + ganha vs single-col concat (sem regressao significativa)
- **H3**: Header overhead negligenciavel em datasets reais (>=1k rows)

## Plano

Sub-exp dirty `2026-05-23-multi-column-scaling/`:

1. **Port**: `multi_col_canonical.py` usando `from tcf import encode, decode`
2. **D17a validation** (controle vs EXP-011)
3. **Real-world Adult + TPC-H tier 1** (8 tabelas, total ~76k linhas)
4. **Medir**: bytes raw / multi / single, header overhead, RT, tempo
5. **Decisao** sobre welding canonical (proxima sessao)

## Criterio de aceite

KR-style mensuraveis:
- [x] D17a RT OK + bytes <= 322B
- [x] Real-world RT 100% em >= 4 tabelas (9/9)
- [x] Multi-col ganho > 0 weighted vs single-col concat (-31.46%)
- [x] Header overhead < 5% datasets >= 1500 rows (< 1% em 5/5)
- [x] **Lineitem 60k validado** (Fase 4: -17.11% raw, -30.73% single, RT OK, 16.6min)

## Resultados

### D17a (controle EXP-011)
- M10 canonical: 322 bytes (EXATO match EXP-011 baseline M9)
- RT: OK
- Pq mesmo? Cols com n=13 < gating threshold 100 (ADR-0010), entao
  M10 fallback pra M9 behavior. Esperado.

### Real-world (9 tabelas, com lineitem 60k)

| | Total |
|---|---:|
| raw_bytes | 15,848,939 |
| multi_bytes | 10,614,897 |
| single_bytes | 15,487,003 |
| **multi vs raw** | **-33.02%** weighted |
| **multi vs single** | **-31.46%** weighted |
| RT | **9/9 OK** |

Destaque:
- adult-census/adult (48k x 15): -65.14% vs raw, -44.62% vs single
- tpch-sf001/orders (15k x 9): -23.11% vs raw, -28.14% vs single
- tpch-sf001/part (2k x 9): -41.32% vs raw, -43.53% vs single
- tpch-sf001/lineitem (60k x 16): -17.11% vs raw, -30.73% vs single (16.6min)
- region (5 x 3): +3.87% vs raw (outlier — tiny dataset, header dominante)

Tempo: lineitem 16.6 min, orders 53s, partsupp 10.5s. HCC O(N^1.42)
e' gargalo dominante (especialmente em datetime cols largas).

## Riscos

1. **NULL handling** (`None -> ""`) pode causar collision com string
   vazia legitima. POC OK, requer revisao pra welding (ADR proposto
   deve cobrir).
2. **CSV proxy raw_bytes** arbitrario; comparacao com parquet/avro
   nao testada.
3. **Tempo lineitem 16.6min**: HCC dominante. Cython/Rust (H-PERF-06)
   poderia reduzir mas adiado.

## Decisao final / welding

**Criterios todos atingidos**. Pendente decisao final de welding
em src/tcf — requer aprovacao explicita user (regra: src/tcf intocado
sem aprovacao).

**Status sub-exp dirty**: closed-validated (H1/H2/H3 confirmadas em
9 tabelas).

**Plano de welding proposto** (3 opcoes API):

| Opcao | Descricao | Recomendado? |
|---|---|---|
| A. `encode_table(dict)` separado | Explicit, type-clear, backward compat | **SIM** |
| B. `encode(values)` overload | DRY 1 func; type check runtime | Nao |
| C. `encode_columns(table)` (O-FMT-05) | Nome antigo plural | Nao |

**Welding plan (Opcao A)**:
1. Novo `src/tcf/multi.py` com `encode_table` + `decode_table`
2. Atualizar `src/tcf/__init__.py`: `from tcf import encode, decode, encode_table, decode_table`
3. Magic constants definidos em src/tcf/multi.py
4. ADR novo (proposto: 0013) documentando decisao
5. tests/test_multi_col_rt.py com D17a 322B INVARIANT + edge cases
6. STATUS.md + tickets atualizados

**NAO welds sem aprovacao explicita do user**.

## Conexoes

- [EXP-011](../experiments/lab/clean/EXP-011-multi-column-basic/) — base
- [sub-exp dirty](../experiments/lab/dirty/2026-05-23-multi-column-scaling/)
- [ADR-0004](../docs/adr/0004-multi-column-header-compacto.md)
- [ADR-0011](../docs/adr/0011-pacote1-weld-canonical.md)
- [O-FMT-* registry](../experiments/lab/dirty/notas/futuras-otimizacoes-formato.md)

## Updates datados

### 2026-05-23 — abertura + 8 tabelas validadas

Ticket aberto pra documentar port canonical de EXP-011 + real-world
validation. Sub-exp dirty criado, port feito, D17a + 8 tabelas
real-world testadas. RT 8/8, -46.58% weighted vs raw, -32.40% weighted
vs single-col concat.

Lineitem 60k adiado pra Fase 4 (1 run, ~20-30 min). Welding decisao
pendente pos-lineitem.

Status mudado de `open` pra `closed-validated-welding-pending-lineitem`.

### 2026-05-23 — Fase 4 lineitem + todos criterios atingidos

Lineitem 60k x 16 rodado (16.6 min real, HCC dominante). Resultado:
- multi: 6,043,481B vs raw 7,291,252B = **-17.11%**
- multi vs single concat: 6,043,481B vs 8,724,093B = **-30.73%**
- RT: OK

Totais agregados 9 tabelas:
- raw: 15,848,939B
- multi: 10,614,897B (**-33.02%** weighted vs raw)
- single: 15,487,003B (multi **-31.46%** vs single weighted)
- RT: **9/9 OK**

Todos criterios de welding atingidos. Welding em src/tcf pendente
aprovacao explicita user (regra: src/tcf intocado).

Status: `closed-validated-welding-pending-approval`.

### 2026-05-23 — WELDED canonical em src/tcf (ADR-0013)

Owner aprovou Opcao A (encode_table separada). Welding executado:

- **Novo `src/tcf/multi.py`** — encode_table + decode_table + MAGIC_MULTI
- **`src/tcf/__init__.py` atualizado** — exports: encode, decode,
  encode_table, decode_table
- **ADR-0013 criado** — accepted + welded, documenta decisao API + header
  format + NULL handling
- **`tests/test_multi_col_rt.py` criado** — 17 tests (RT basico, D17a
  322B INVARIANT, info dict, edge cases). Todos passam (17/17).
- **Validacao byte-canonical**: D17a 322B preservado EXATO; suite
  completa 96 passed + 1 xfailed + 1 pre-existing fail (test_shaper,
  nao relacionado)

Status: `closed-welded-canonical`.
