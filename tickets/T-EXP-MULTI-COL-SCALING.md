---
title: T-EXP-MULTI-COL-SCALING — Port multi-column pra canonical M10 + real-world
status: closed-validated-welding-pending-lineitem
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
- [x] Real-world RT 100% em >= 4 tabelas
- [x] Multi-col ganho > 0 weighted vs single-col concat
- [x] Header overhead < 5% datasets >= 1500 rows
- [ ] Lineitem 60k validado (adiado pra Fase 4)

## Resultados

### D17a (controle EXP-011)
- M10 canonical: 322 bytes (EXATO match EXP-011 baseline M9)
- RT: OK
- Pq mesmo? Cols com n=13 < gating threshold 100 (ADR-0010), entao
  M10 fallback pra M9 behavior. Esperado.

### Real-world (8 tabelas, sem lineitem)

| | Total |
|---|---:|
| raw_bytes | 8,557,687 |
| multi_bytes | 4,571,416 |
| single_bytes | 6,762,910 |
| **multi vs raw** | **-46.58%** weighted |
| **multi vs single** | **-32.40%** weighted |
| RT | **8/8 OK** |

Destaque:
- adult-census/adult (48k x 15): -65.14% vs raw, -44.62% vs single
- tpch-sf001/orders (15k x 9): -23.11% vs raw, -28.14% vs single
- tpch-sf001/part (2k x 9): -41.32% vs raw, -43.53% vs single
- region (5 x 3): +3.87% vs raw (outlier — tiny dataset, header dominante)

Tempo: orders 53s, partsupp 10.5s. HCC O(N^1.42) e' gargalo.

## Riscos

1. **NULL handling** (`None -> ""`) pode causar collision com string
   vazia legitima. POC OK, revisar pra welding.
2. **Lineitem nao testado** — pode mudar metricas weighted
   (lineitem peso ~20% do real-world weight).
3. **CSV proxy raw_bytes** arbitrario; comparacao com parquet/avro
   nao testada.

## Decisao final / welding

**RECOMENDACAO**: welding adiado ate' validar lineitem (Fase 4 ~30min)
+ decisao sobre nome funcao publica.

**Status sub-exp dirty**: closed-validated (H1/H2/H3 confirmadas em
8 tabelas).

**Pendente pra welding**:
1. Lineitem 60k validation
2. Nome da funcao: `encode_table` / `encode_dict` / `encode(dict|list)` overload?
3. ADR atualizado documentando decisao (estender ADR-0004 ou novo)
4. tests/test_multi_col_rt.py com >= 3 tabelas

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
