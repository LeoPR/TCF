# Resultado — 08-granularidades-finas

Pipeline staged estendido pra **ms/us/ns** com sufixos multi-char
(`ms`, `us`, `ns`). 8 datasets testados (5 backward compat + 3 novos).

## Tabela consolidada

| Dataset | Granul. | Linhas | Raw | B inter | C inter | B==C? | TCF puro | TCF B | TCF C | Esperado | RT |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| D11a-datas-dia | day | 12 | 136 | 34 | 34 | sim | 87 | 42 | **42** | 42 | OK |
| D11b-datas-borda | day | 14 | 158 | 45 | 45 | sim | 173 | 59 | **59** | 59 | OK |
| D11c-datas-mensal | day | 13 | 147 | 47 | 47 | **nao** | 109 | 53 | **22** | 22 | OK |
| D11d-datetime-min | second | 13 | 264 | 56 | 56 | **nao** | 110 | 34 | **34** | 34 | OK |
| D11e-datetime-mensal | second | 13 | 264 | 116 | 56 | **nao** | 121 | 80 | **34** | 34 | OK |
| D11f-datetime-ms | ms | 13 | 316 | 84 | 60 | **nao** | 115 | 41 | **39** | — | OK |
| D11g-datetime-us | us | 13 | 355 | 87 | 75 | **nao** | 120 | 45 | **43** | — | OK |
| D11h-datetime-ns | ns | 13 | 394 | 90 | 78 | **nao** | 123 | 48 | **46** | — | OK |

## Stage C outputs (so' os 3 novos)

### D11f-datetime-ms
```
2025-05-15 09:00:00.000
1s
1s
1s
1s
1s
1s
1s
1s
1s
1s
1s
1s
```

### D11g-datetime-us
```
2025-05-15 09:00:00.000000
1ms
1ms
1ms
1ms
1ms
1ms
1ms
1ms
1ms
1ms
1ms
1ms
```

### D11h-datetime-ns
```
2025-05-15 09:00:00.000000000
1us
1us
1us
1us
1us
1us
1us
1us
1us
1us
1us
1us
```

## Linguagem das escalas (cumulativa apos sub-exps 03-08)

| Sufixo | Significado | Valido em granularidade |
|---|---|---|
| (none) | unidade base detectada em A | sempre |
| `Y` | ano | sempre |
| `M` | mes (capital pra distinguir minuto) | sempre |
| `D` | dia | second, ms, us, ns |
| `h` | hora | second, ms, us, ns |
| `m` | minuto | second, ms, us, ns |
| `s` | segundo | ms, us, ns |
| `ms` | milissegundo (multi-char) | us, ns |
| `us` | microssegundo (multi-char) | ns |
| sinal `-` | negativo | sempre |

## Hipoteses

- **H1 (RT preservado em 8 datasets)**: CONFIRMADA (8/8 OK).
- **H2 (backward compat byte-exato D11a-e)**: CONFIRMADA.
- **H3 (Stage A detecta ms/us/ns)**: D11f=ms, D11g=us, D11h=ns.

## Conexoes

- [`../07-cadencia-mensal-datetime-D11e/`](../07-cadencia-mensal-datetime-D11e/) — base do pipeline
- [`../README.md`](../README.md) — T01
