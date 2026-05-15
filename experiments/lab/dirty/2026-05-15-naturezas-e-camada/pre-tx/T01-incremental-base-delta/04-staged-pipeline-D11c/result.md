# Resultado — 04-staged-pipeline-D11c-datas-mensal

## Estagios em sequencia

### Stage A (identify) — metadata

```json
{
  "n_samples": 13,
  "type": "date",
  "format": "YYYY-MM-DD",
  "granularity": "day"
}
```

### Stage B (normalize) — 47 bytes intermediarios

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

### Stage C (optimize) — 47 bytes intermediarios

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

### TCF (de C) — 22 bytes

```
\2025-\01-\05
*12|\1M
```

## Comparacao de pipelines

Raw CSV: 147 bytes

| Pipeline | TCF bytes | vs raw csv | vs TCF puro |
|---|---:|---:|---:|
| TCF puro | 109 | 74.1% | 100.0% |
| Stage A+B (= encoder v0) | 53 | 36.1% | 48.6% |
| **Stage A+B+C (= encoder v1)** | **22** | **15.0%** | **20.2%** |

## Hipoteses

- **H1 (RT preservado em ambos os pipelines)**: CONFIRMADO
  - RT full via C (com escala): OK
  - RT full via B (so dias): OK
- **H2 (bytes iguais a v1 monolitico do sub-exp 03)**: CONFIRMADO

## Comparacao com encoder monolitico (sub-exp 03)

Sub-exp 03 (encoder v1 monolitico): 22 bytes em D11c.
Sub-exp 04 (encoder em 3 estagios): 22 bytes em D11c.

Resultado: IDENTICO — separar em estagios
preserva compressao final, com vantagem de ter estados intermediarios
visiveis pra inspecao e raciocinio futuro.

## Conexoes

- [`README.md`](README.md) — pergunta cientifica + metodo
- [`stage_a_identify.py`](stage_a_identify.py) — estagio A
- [`stage_b_normalize.py`](stage_b_normalize.py) — estagio B
- [`stage_c_optimize.py`](stage_c_optimize.py) — estagio C
- [`decoder.py`](decoder.py) — inverso completo
- [`../03-cadencia-mensal-D11c/`](../03-cadencia-mensal-D11c/) — encoder monolitico equivalente
