# Resultado — 07-cadencia-mensal-datetime-D11e

## Tabela consolidada

| Dataset | Granul. | Linhas | Raw | B inter | C inter | B==C? | TCF puro | TCF B | TCF C | Ganho C vs B |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| D11c-datas-mensal | day | 13 | 147 | 47 | 47 | **nao** | 109 | 53 | **22** | **+58.5%** |
| D11d-datetime-min | second | 13 | 264 | 56 | 56 | **nao** | 110 | 34 | **34** | **+0.0%** |
| D11e-datetime-mensal | second | 13 | 264 | 116 | 56 | **nao** | 121 | 80 | **34** | **+57.5%** |

## Stage outputs (visuais)

### D11c-datas-mensal

**Stage B (em unidade base):**
```
2025-01-05
31
28
31
30
31
30
31
31
30
31
30
31
```

**Stage C (com escalas):**
```
2025-01-05
1M
1M
1M
1M
1M
1M
1M
1M
1M
1M
1M
1M
```

### D11d-datetime-min

**Stage B (em unidade base):**
```
2026-05-15 09:00:00
60
60
60
60
60
60
60
60
60
60
60
60
```

**Stage C (com escalas):**
```
2026-05-15 09:00:00
1m
1m
1m
1m
1m
1m
1m
1m
1m
1m
1m
1m
```

### D11e-datetime-mensal

**Stage B (em unidade base):**
```
2025-01-05 09:00:00
2678400
2419200
2678400
2592000
2678400
2592000
2678400
2678400
2592000
2678400
2592000
2678400
```

**Stage C (com escalas):**
```
2025-01-05 09:00:00
1M
1M
1M
1M
1M
1M
1M
1M
1M
1M
1M
1M
```

## Hipoteses

- **H1 (RT preservado)**: CONFIRMADA (3/3 OK).
- **H2 (escala vence em D11e)**: CONFIRMADA.
  - D11e Stage B: 80 bytes
  - D11e Stage C: 34 bytes
  - Ganho: +57.5% (negativo = C maior).
- **H3 (backward compat D11c/D11d)**: CONFIRMADA.

## Observacao chave

Em **granularidade segundo**, escala traz ganho **quando**:
- **Lower unit varia** (segundos por mes: 28/30/31 × 86400 -> 3 valores distintos)
- **Higher unit e' exato** (mes = mes mesmo em durations diferentes)

D11e satisfaz ambos -> escala vence.
D11d (second/minute) NAO satisfaz primeiro (lower fixo em 60s) -> empate B=C.
D11c (day/mensal) ja' validou padrao analogo em day-granularity.

## Conexoes

- [`../06-staged-granularity-second/`](../06-staged-granularity-second/) — encoder source
- [`../03-cadencia-mensal-D11c/`](../03-cadencia-mensal-D11c/) — caso analogo em day
- [`../README.md`](../README.md) — T01 macro pai
