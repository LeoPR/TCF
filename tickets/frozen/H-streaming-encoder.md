---
title: Streaming / chunked encoder — compressao em blocos incrementais
type: hypothesis
status: OPEN
priority: MEDIUM
created: 2026-04-10
origin: Hipotese de que TCF batch atual perde em memoria/TTFB vs streaming
see_also: docs/research-notes/2026-04-10-compression-tokens-streaming.md
---

# Streaming Encoder

## Problema atual

TCF encoder atual faz **batch completo**:
1. Carrega todas as linhas na memoria (list of dicts)
2. Processa colunas inteiras (sort global, RLE, dict)
3. Emite string completa

**Consequencias:**
- **Memoria O(N)** — dataset de 100K rows pode estourar
- **Latencia alta** antes do primeiro byte (precisa processar tudo)
- **Nao compativel** com HTTP chunked transfer nativamente
- **Nao viavel** em IoT/edge com memoria limitada

## Comparacao com alternativas

### gzip streaming (Python stdlib)
```python
compressor = zlib.compressobj(level=6, wbits=31)  # gzip format
output = b""
for chunk in input_stream:
    output += compressor.compress(chunk)
output += compressor.flush()
```
- **Memoria:** ~32KB buffer LZ77 (janela fixa)
- **Latencia:** primeiros bytes saem cedo
- **Ratio:** ~95% do batch (perde um pouco de visao global)

### heatshrink (embedded)
Compressao LZSS com janela de 256-1024 bytes. Memoria em kilobytes.
Usado em firmware/IoT. [heatshrink GitHub](https://github.com/atomicobject/heatshrink)

### HTTP chunked transfer
Protocolo HTTP/1.1: envia dados em blocos independentes com tamanho prefixado.
Cliente monta em streaming.

## Hipotese

**H-stream:** e possivel implementar TCF chunked (por blocos de N linhas)
com perda < 10% de compressao vs batch, mas com:
- **Memoria:** O(chunk_size) em vez de O(N)
- **TTFB (time to first byte):** constante, independente do total
- **Streaming compativel:** cada chunk pode ser gzip'ed independentemente

## Design proposto

### Formato TCF chunked

```
# TCF v0.2 level=1 chunked=true chunk_size=1000
## vendas n=5000 chunks=5

## chunk 1 rows=1-1000
pessoa:
8*Ana 12*Bruno 5*Carla ...
produto:
3*Caneta 10*Lapis ...
total:
2.5 3.0 11.0 ...

## chunk 2 rows=1001-2000
pessoa:
...
```

Cada chunk e **auto-suficiente** — decoder consegue reconstruir
apenas lendo o header + chunk, sem depender de chunks anteriores.

### Niveis e streaming

| Level | Streamable? | Por que |
|-------|------------|---------|
| L0 (expanded) | **Sim facil** | Sem sort, sem dict, emite linear |
| L1 (RLE) | **Sim** | RLE local por chunk, overhead minimo |
| L2 (sort+RLE) | **Parcial** | Sort **local** por chunk (perde ratio global) |
| L3 (dict+sort+RLE) | **Dificil** | Dict global precisa 2 passadas. Alternativa: dict local por chunk |

**Decisao:** comecar por L0 e L1 (triviais). Avaliar L2 com sort local.

## Tarefas

- [ ] Implementar modo chunked em encoder (L0, L1)
- [ ] Medir memoria peak: batch vs chunked (tracemalloc)
- [ ] Medir TTFB: batch vs chunked (timing primeiros bytes)
- [ ] Medir ratio: batch vs chunked (gzip apos ambos)
- [ ] Comparar com gzip streaming direto (baseline)
- [ ] Testar L2 com sort local — perda de ratio aceitavel?
- [ ] Avaliar se decoder chunked e mais complexo (T-multi-lang impact)

## Relacao com outros tickets

- **E-http-protocol:** streaming e critico para APIs HTTP modernas
- **E-memory-profiling:** streaming reduz memoria peak drasticamente
- **T-multi-lang:** decoders em C/JS devem suportar streaming se possivel
- **H-advanced-encodings:** delta/FOR podem ser streamable, dict nao

## Caveats

1. **Decodificadores ficam mais complexos** — loop over chunks
2. **Ratio de compressao cai** em L2/L3 (sort local vs global)
3. **Cada chunk tem overhead** de header (`## chunk N rows=A-B`)
4. **Para datasets pequenos (<1000 rows),** chunking e puro overhead

## Quando streaming vale a pena

- APIs HTTP servindo dados tabulares grandes
- IoT/edge com memoria <100MB
- Pipelines de ingestao contínua
- Integracao com HTTP/2 ou gRPC streaming

Quando **nao** vale:
- Dados <1K rows (cabe tudo em memoria)
- Storage a longo prazo (batch da melhor compressao)
- Scripts ad-hoc (simplicidade > performance)
