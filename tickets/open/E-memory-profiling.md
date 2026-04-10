---
title: Profiling de memoria — peak RAM durante encode/decode
type: experiment
status: OPEN
priority: MEDIUM
created: 2026-04-10
origin: Dimensao 7 de G-utility-analysis (consumo de memoria)
parent: G-utility-analysis
---

# Profiling de Memoria

## Motivacao

Se TCF ganha em bytes transmitidos mas exige 10x mais RAM que JSON,
nao vale a pena para servers com restricao de memoria (containers,
serverless, IoT).

Precisamos medir **quanta RAM** cada formato consome durante:
- Encode (converter dict → text)
- Decode (converter text → dict)
- Peak usage durante operacao

## Hipotese

**H-memory:** TCF usa mais memoria peak durante encode (porque precisa
processar colunas inteiras de uma vez para sort + RLE) mas menos durante
decode (leitura linear).

JSON usa memoria proporcional ao tamanho do output (streaming possivel).
CSV usa memoria baixa em ambos (linear em ambos).
Parquet usa memoria moderada (buffered).

## Design

### Ferramenta
`tracemalloc` do stdlib Python — preciso, sem dependencias.

```python
import tracemalloc

tracemalloc.start()
snapshot_before = tracemalloc.take_snapshot()

result = encode(data, ...)

snapshot_after = tracemalloc.take_snapshot()
stats = snapshot_after.compare_to(snapshot_before, 'lineno')
peak = tracemalloc.get_traced_memory()[1]
tracemalloc.stop()
```

### Cenarios

Para cada formato e cada operacao:
- **Input:** retail_sales em escala 100, 1000, 10000, 100000
- **Medir:**
  - Peak memory durante encode
  - Peak memory durante decode
  - Memory overhead vs input size (ratio)

### Formatos testados
- CSV (stdlib csv)
- JSONL (stdlib json)
- TCF L0, L2, L3
- TOON (quando implementado)

## Metricas

| Formato | Input (10K rows) | Encode peak | Decode peak | Output size |
|---------|------------------|-------------|-------------|-------------|
| CSV | 500KB | 600KB | 550KB | 490KB |
| JSONL | 500KB | 800KB | 900KB | 1400KB |
| TCF L0 | 500KB | ? | ? | 490KB |
| TCF L2 | 500KB | ? (sort) | ? | 430KB |
| TCF L3 | 500KB | ? (dict + sort) | ? | 280KB |
| TOON | 500KB | ? | ? | ? |

Valores sao hipoteticos — vao ser medidos.

## Hipoteses especificas

### H-mem-1: TCF L2/L3 tem peak alto por causa do sort
Sort exige N*log(N) em memoria. CSV nao precisa.

### H-mem-2: Decode e linear em todos os formatos
Leitura row-by-row (ou column-by-column) pode ser streaming.

### H-mem-3: Python tem overhead alto
dict/list de Python tem overhead maior que dataclasses ou arrays.
Um decoder em C teria memoria muito menor (ver T-multi-lang).

## Caso de uso critico: serverless

AWS Lambda tem 128MB-10GB. Se TCF exige 2GB para encode de 100K rows,
esta fora do mercado de edge computing.

**Teste:** encode 100K rows com limite de 128MB — funciona?

## Relacao com outros tickets

- **G-utility-analysis**: dimensao 7 do guia mestre
- **T-multi-lang**: implementacoes C/Rust podem ter memoria muito menor
- **E-direct-conversion**: adapters diretos podem economizar memoria
  (nao alocam CSV intermediario)

## Tarefas

- [ ] Implementar `memory_profile.py` com tracemalloc
- [ ] Rodar 5 formatos × 4 escalas × encode/decode = 40 medicoes
- [ ] Tabela final: peak memory por formato por escala
- [ ] Documentar nos resultados do paper
