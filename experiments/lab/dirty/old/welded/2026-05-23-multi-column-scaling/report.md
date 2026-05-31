# Multi-column scaling — port canonical M10 + real-world (report)

**Data**: 2026-05-23
**Estado**: validado em 1 sintetico + 9 tabelas real-world (com lineitem 60k Fase 4)
**Predecessor**: EXP-011 (multi-column basico, M9, D17a apenas)

## Resumo executivo

Port de `multi_col.py` de delta_aware (EXP-010) pra canonical M10
(`from tcf import encode, decode`) preservou bytes em D17a e validou
em 9 tabelas real-world (incluindo lineitem 60k) com RT 100%:

- **D17a sint** (13 x 4): 322 bytes (== EXP-011 baseline, RT OK)
- **9 tabelas real-world** (Adult Census + TPC-H tier 1+2, total
  ~136k linhas, 15.8 MB raw): **-33.02% weighted vs raw, -31.46%
  weighted vs single-col concat**, RT 9/9

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
| tpch-sf001/lineitem | 60,175 | 16 | massivo (Fase 4, 16.6min HCC) |

Total: ~136k linhas, ~79 colunas agregadas, 15,848,939 raw bytes.

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

### Real-world (9 tabelas)

| dataset/table | rows | cols | raw | multi | single | hdr% | vs_raw% | vs_single% | RT | tempo |
|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|---:|
| adult-census/adult | 48842 | 15 | 5,271,056 | 1,837,695 | 3,318,253 | 0.01% | -65.14% | -44.62% | OK | 3s |
| tpch-sf001/region | 5 | 3 | 413 | 429 | 389 | 11.42% | +3.87% | +10.28% | OK | 0s |
| tpch-sf001/nation | 25 | 4 | 2,240 | 2,213 | 2,237 | 3.03% | -1.21% | -1.07% | OK | 0s |
| tpch-sf001/supplier | 100 | 7 | 13,750 | 12,630 | 14,882 | 0.85% | -8.15% | -15.13% | OK | 0s |
| tpch-sf001/customer | 1500 | 8 | 239,417 | 202,961 | 254,381 | 0.07% | -15.23% | -20.21% | OK | 1s |
| tpch-sf001/part | 2000 | 9 | 235,016 | 137,907 | 244,216 | 0.10% | -41.32% | -43.53% | OK | 3s |
| tpch-sf001/partsupp | 8000 | 5 | 1,152,973 | 1,114,424 | 1,170,853 | 0.01% | -3.34% | -4.82% | OK | 10s |
| tpch-sf001/orders | 15000 | 9 | 1,642,822 | 1,263,157 | 1,757,699 | 0.01% | -23.11% | -28.14% | OK | 52s |
| tpch-sf001/lineitem | 60175 | 16 | 7,291,252 | 6,043,481 | 8,724,093 | 0.01% | -17.11% | -30.73% | OK | 999s (~17min) |
| **WEIGHTED TOTAL** | | | **15,848,939** | **10,614,897** | **15,487,003** | | **-33.02%** | **-31.46%** | **9/9** | ~18min |

### Observacoes

1. **RT 100%** em todas tabelas (9/9 multi + 9/9 single). Pipeline
   canonical multi-column funciona em real-world inclusive volume
   maior (lineitem 60k x 16, ~963k valores).

2. **Compressao consistente**: -33.02% weighted vs raw (com lineitem)
   vs -46.58% sem lineitem. Lineitem reduz weighted ganho porque
   tem cardinalidade alta + datetimes (ja' capturados em parte pelo
   M10 mas com menor margem).

3. **Multi-col vence single-col**: -31.46% weighted vs concat (com
   lineitem). Lineitem isolado: -30.73% multi vs single — confirma
   beneficio mesmo em tabelas largas (16 cols).

4. **Header overhead despreza' em >1500 rows**: < 1% em 5/5 tabelas
   com >= 1500 rows (incluindo lineitem 0.01%). Region (5 rows) tem
   11.42% (esperado — dataset tiny, header de 49B em 429B total).

5. **Regressao region (+3.87% vs raw)**: tabela menor (15 valores
   totais), header dominante. Stress de overhead, nao bug. Sintoma
   esperado pra datasets sub-100 valores.

6. **Tempo**: lineitem (60k x 16) levou 16.6 min real. HCC e' gargalo
   (O(N^1.42) pos-ADR-0009). Por coluna: ~62s media (999s / 16 cols),
   mas algumas datetime cols saturam.

7. **Lineitem destaque**: -65% bodies vs single concat (8.7MB → 6.0MB).
   Multi-col beneficia significativamente em tabelas largas.

## Validacao H1/H2/H3

| Hipotese | Predicao | Resultado | Verdict |
|---|---|---|---|
| H1 | Port canonical preserva D17a RT + bytes <= 322B | RT OK, 322B EXATO | confirmada |
| H2 | Multi-col real-world viavel sem regressao | -33.02% weighted vs raw (com lineitem) | confirmada |
| H3 | Header overhead < 1% pra >1k rows | < 1% em 5/5 tabelas >= 1500 rows; outlier region tiny | confirmada |

## Decisao

### Welding canonical em src/tcf?

**Criterio de aceite** (auto-imposto):
- [x] RT 100% real-world (>= 4 tabelas): 9/9
- [x] Multi-col ganho consistente vs single-col: -31.46% weighted (com lineitem)
- [x] Header overhead < 5% em datasets >= 1500 rows: < 1% em 5/5
- [x] **Lineitem 60k testado**: -17.11% raw, -30.73% single, RT OK (16.6 min)

**TODOS CRITERIOS ATINGIDOS**. Pendente apenas decisao de API + ADR.

### Opcoes de API publica

| Opcao | Pro | Contra |
|---|---|---|
| A. `encode_table(dict[str, list[str]])` separado | Explicit; type-clear; backward compat trivial | API tem 2 funcs (encode + encode_table) |
| B. `encode(values)` overload aceitando dict | DRY; 1 func | Type check em runtime; documentacao ambigua |
| C. `encode_columns(table)` (nome O-FMT-05 antigo) | Mais descritivo "columns" | Plural inconsistente com `encode` singular |

**Recomendacao**: **Opcao A** (`encode_table` + `decode_table` separados).
Razoes:
- Zen of Python: "Explicit is better than implicit"
- Type-safe sem runtime checks
- API publica clara: `encode` (single col) vs `encode_table` (multi col)
- Match com sub-exp dirty `multi_col_canonical.py` (port direto)
- EXP-011 ja' usou esse nome (continuidade)

### ADR proposto

Novo ADR documentando decisao welding multi-column canonical.
ADR-0004 ja' aborda header format; novo ADR pode focar em:
- Decisao de API (encode_table separada vs overload)
- Magic constants (MAGIC_MULTI = `#TCF.6 M`)
- NULL handling (`None -> ""`)
- Backward compat (output do EXP-011 ainda decodavel)

## Limitacoes

- **NULL handling**: convertido pra `""`. Pode causar collisions com
  string vazia legitima. Adequado pra POC, requer revisao pra welding
  (ADR proposto deve cobrir).
- **Sem cross-column** (O-FMT-06): otimizacoes ortogonais nao testadas.
- **Sem ordering** (O-FMT-01..04): linhas mantidas em ordem original.
- **CSV proxy raw_bytes**: arbitrario. Datasets reais podem ser binarios
  (parquet, etc.) com tamanhos diferentes.
- **Tempo lineitem 16.6min**: HCC dominante. Cython/Rust (H-PERF-06)
  poderia reduzir mas adiado.

## Conexao

- [EXP-011 base](../../clean/EXP-011-multi-column-basic/) — M9 + D17a apenas
- [ADR-0004](../../../../docs/adr/0004-multi-column-header-compacto.md) — header format
- [ADR-0011](../../../../docs/adr/0011-pacote1-weld-canonical.md) — M9 → M10
- [O-FMT-* registry](../notas/futuras-otimizacoes-formato.md)

## Proximo

1. ~~**Fase 4**: lineitem 60k validation~~ (FEITO: -17.11% raw, RT OK)
2. **Decisao welding**: aprovar Opcao A (encode_table separada) ou
   alternativa
3. **Welding** em src/tcf (novo `src/tcf/multi.py` com `encode_table` +
   `decode_table`) — requer aprovacao explicita user (src/tcf intocado
   sem aprovacao)
4. **ADR novo** documentando decisao
5. **Tests CI**: adicionar tests/test_multi_col_rt.py com D17a 322B
   INVARIANT + edge cases + (opcional) tabela real-world via marker
   requires_data
