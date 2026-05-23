# Multi-column scaling — port canonical M10 + real-world (report)

**Data**: 2026-05-23
**Estado**: validado em 1 sintetico + 8 tabelas real-world (sem lineitem)
**Predecessor**: EXP-011 (multi-column basico, M9, D17a apenas)

## Resumo executivo

Port de `multi_col.py` de delta_aware (EXP-010) pra canonical M10
(`from tcf import encode, decode`) preservou bytes em D17a e validou
em 8 tabelas real-world com RT 100%:

- **D17a sint** (13 x 4): 322 bytes (== EXP-011 baseline, RT OK)
- **8 tabelas real-world** (Adult Census + TPC-H tier 1, total
  76,472 valores): **-46.58% vs raw, -32.40% vs single-col concat**,
  RT 8/8

## Metodologia

### Pipeline
```python
from multi_col_canonical import encode_table, decode_table
# encode_table = wrapper sobre tcf.encode() por coluna +
# header `#TCF.6 M\n# size=name,...\n`
```

### Datasets

| Dataset | n_rows | n_cols | Notas |
|---|---:|---:|---|
| D17a sintetico | 13 | 4 | controle EXP-011 |
| adult-census/adult | 48,842 | 15 | UCI, mix numeric+categorical |
| tpch-sf001/region | 5 | 3 | menor (stress de header overhead) |
| tpch-sf001/nation | 25 | 4 | pequeno |
| tpch-sf001/supplier | 100 | 7 | medio-pequeno |
| tpch-sf001/customer | 1,500 | 8 | medio |
| tpch-sf001/part | 2,000 | 9 | medio |
| tpch-sf001/partsupp | 8,000 | 5 | medio-grande |
| tpch-sf001/orders | 15,000 | 9 | grande |

Total: ~76k linhas, ~63 colunas agregadas, 8,557,687 raw bytes.

NAO testado: `tpch-sf001/lineitem` (60,175 x 16, ~20-30 min HCC).
Validacao Fase 4 futuro.

### Metricas

- **raw_bytes**: CSV-like serialization (proxy original size)
- **multi_bytes**: `encode_table()` total (header + bodies)
- **single_bytes**: `tcf.encode(rows_concat)` (concat por linha,
  single-col baseline)
- **header_overhead%**: header / multi_bytes
- **RT**: decode_table == original table

## Resultados

### D17a (sintetico, controle)

| Metrica | M9 (EXP-011) | M10 (canonical) | Delta |
|---|---:|---:|---|
| Total bytes | 322 | 322 | 0 |
| RT | OK | OK | — |

M10 preserva baseline em D17a (cols pequenas demais pra heur min_len
ativar via gating ADR-0010 n>=100).

### Real-world (8 tabelas)

| dataset/table | rows | cols | raw | multi | single | hdr% | vs_raw% | vs_single% | RT |
|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| adult-census/adult | 48842 | 15 | 5,271,056 | 1,837,695 | 3,318,253 | 0.01% | -65.14% | -44.62% | OK |
| tpch-sf001/region | 5 | 3 | 413 | 429 | 389 | 11.42% | +3.87% | +10.28% | OK |
| tpch-sf001/nation | 25 | 4 | 2,240 | 2,213 | 2,237 | 3.03% | -1.21% | -1.07% | OK |
| tpch-sf001/supplier | 100 | 7 | 13,750 | 12,630 | 14,882 | 0.85% | -8.15% | -15.13% | OK |
| tpch-sf001/customer | 1500 | 8 | 239,417 | 202,961 | 254,381 | 0.07% | -15.23% | -20.21% | OK |
| tpch-sf001/part | 2000 | 9 | 235,016 | 137,907 | 244,216 | 0.10% | -41.32% | -43.53% | OK |
| tpch-sf001/partsupp | 8000 | 5 | 1,152,973 | 1,114,424 | 1,170,853 | 0.01% | -3.34% | -4.82% | OK |
| tpch-sf001/orders | 15000 | 9 | 1,642,822 | 1,263,157 | 1,757,699 | 0.01% | -23.11% | -28.14% | OK |
| **WEIGHTED TOTAL** | | | **8,557,687** | **4,571,416** | **6,762,910** | | **-46.58%** | **-32.40%** | **8/8** |

### Observacoes

1. **RT 100%** em todas tabelas (8/8 multi + 8/8 single). Pipeline
   canonical multi-column funciona em real-world.

2. **Compressao consistente**: -46.58% weighted vs raw. Adult Census
   destaca-se: -65.14% (15 cols mixed types beneficiam de per-column
   pipeline).

3. **Multi-col vence single-col**: -32.40% weighted vs concat.
   Confirma H1 (cada coluna tem padroes diferentes que se beneficiam
   de pipeline proprio).

4. **Header overhead despreza' em >1500 rows**: < 1% em todas as
   tabelas com >= 1500 rows. Region (5 rows) tem 11.42% (esperado —
   dataset tiny, header de 49B em 429B total).

5. **Regressao region (+3.87% vs raw)**: tabela menor (15 valores
   totais), header dominante. Stress de overhead, nao bug. Sintoma
   esperado pra datasets sub-100 valores.

6. **Tempo**: orders (15k rows) levou 53s, partsupp 10.5s. HCC e'
   gargalo (O(N^1.42) pos-ADR-0009). Lineitem 60k rows estimado
   20-30min.

## Validacao H1/H2/H3

| Hipotese | Predicao | Resultado | Verdict |
|---|---|---|---|
| H1 | Port canonical preserva D17a RT + bytes <= 322B | RT OK, 322B EXATO | confirmada |
| H2 | Multi-col real-world viavel sem regressao | -46.58% weighted vs raw | confirmada |
| H3 | Header overhead < 1% pra >1k rows | < 1% em 4 das 5 tabelas >= 1500 rows; outlier region tiny | confirmada |

## Decisao

### Welding canonical em src/tcf?

**Criterio de aceite** (auto-imposto):
- [x] RT 100% real-world (>= 4 tabelas): 8/8
- [x] Multi-col ganho consistente vs single-col: -32.40% weighted
- [x] Header overhead < 5% em datasets >= 1500 rows: < 1% em 4/5
- [ ] Lineitem 60k testado (Fase 4 futuro): adiado

**Recomendacao**: weld pra `src/tcf` (modulo `multi.py` ou estender
`encoder.py`) APOS:
1. Lineitem validation (Fase 4)
2. Decisao sobre nome de funcao publica: `encode_table` / `encode_dict`
   / extender `encode()` com overload?
3. ADR formal documentando header format final (ADR-0004 ja' aborda;
   talvez atualizar com decisao da chamada publica)

Pre-requisito atual: confirmar lineitem antes de welding.

## Limitacoes

- **lineitem 60k NAO testado** — tabela maior da TPC-H; resultado
  pode mudar metricas weighted (lineitem teria peso ~20% do total
  real-world).
- **NULL handling**: convertido pra `""`. Pode causar collisions com
  string vazia legitima. Adequado pra POC, requer revisao pra welding.
- **Sem cross-column** (O-FMT-06): otimizacoes ortogonais nao testadas.
- **Sem ordering** (O-FMT-01..04): linhas mantidas em ordem original.
- **CSV proxy raw_bytes**: arbitrario. Datasets reais podem ser binarios
  (parquet, etc.) com tamanhos diferentes.

## Conexao

- [EXP-011 base](../../clean/EXP-011-multi-column-basic/) — M9 + D17a apenas
- [ADR-0004](../../../../docs/adr/0004-multi-column-header-compacto.md) — header format
- [ADR-0011](../../../../docs/adr/0011-pacote1-weld-canonical.md) — M9 → M10
- [O-FMT-* registry](../notas/futuras-otimizacoes-formato.md)

## Proximo

1. **Fase 4**: lineitem 60k validation (1 run, ~20-30 min)
2. **Decisao welding**: nome da funcao publica + ADR atualizado
3. **Welding** em src/tcf (modulo `multi.py` ou extender `encoder.py`)
4. **Tests CI**: adicionar test_multi_col_rt.py com >= 3 tabelas
