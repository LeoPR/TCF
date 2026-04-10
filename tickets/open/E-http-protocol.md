---
title: TCF como substituto de JSON/CSV em protocolos HTTP — benchmark completo
type: experiment
status: OPEN
priority: HIGH
created: 2026-04-10
origin: Visao de TCF como protocol replacement (alem de LLM)
---

# TCF como Substituto de Protocolo HTTP

## Visao

TCF nao deve ser apenas "um formato para LLMs". Deve ser uma **referencia
de substituicao de protocolo HTTP** — um formato textual que API providers
podem adotar no lugar de JSON/CSV para transmitir dados tabulares.

Argumentos centrais:
1. Menos bytes (columnar + RLE nativo)
2. Menos bytes apos compressao (gzip/brotli/zstd favorecem sort+RLE)
3. Interpretavel por LLMs e humanos (diferente de Parquet/Arrow)
4. Decodificavel em qualquer linguagem (ver T-multi-lang)

## Experimentos necessarios

### E1: Overhead de processamento (critico)

**Pergunta:** TCF encode/decode e competitivo em tempo com JSON parse/stringify?

**Medicoes:**
- Encode: tempo de CSV/JSON/dict → TCF text (por nivel)
- Decode: tempo de TCF text → dict/records
- Comparacao: json.dumps/loads, csv.reader/writer, TOON

**Metrica:** microssegundos por linha, em escalas 100/1000/10000/100000

**Hipotese:** TCF encode e LENTO (sort + RLE + dict) mas decode e RAPIDO
(linear pass). Justifica-se para APIs read-heavy (servidor encoda uma vez,
N clientes decodam).

### E2: Compressao HTTP completa

**Formatos compressores:** gzip (default HTTP), brotli (Chrome moderno),
zstd (emergente)

**Dados:** retail_sales em escalas 50, 200, 1000, 5000, 10000
Formatos: CSV, JSONL, TCF L0, L1, L2, L3

**Metrica:** ratio final (bytes transmitidos / bytes brutos)

Parcialmente feito em P-transport-compression (so gzip). Expandir:
- [x] gzip
- [ ] brotli
- [ ] zstd
- [ ] tempo de compressao/descompressao (CPU cost)
- [ ] tempo total = compress + transmit + decompress

### E3: Latencia end-to-end simulada

**Cenario:** API retorna 1000 registros por request.
**Simulacao:** server encoda → comprime → "envia" (copy in memory) → cliente
descomprime → decoda → acessa campo X do registro Y.

**Metrica:** ms por request completo, por formato.

**Hipotese:** TCF+brotli tem menor latencia total que JSONL+gzip mesmo com
encode mais lento, porque transmit + decompress + parse sao dominantes.

### E4: Bandwidth em escala real

Estimativa: se uma API serve 1M requests/dia retornando 500 registros cada,
qual o ganho total de bandwidth com TCF+brotli vs JSON+gzip?

Multiplicar por custo de egress AWS/GCP ($0.09/GB) para ter valor em dolares.

## Comparacao com alternativas existentes

| Formato | Tipos | Comp. nativa | Legivel | LLM-friendly | Cross-language |
|---------|-------|--------------|---------|--------------|-----------------|
| JSON | Sim | Nao | Sim | Sim (default) | Sim (universal) |
| CSV | Nao | Nao | Sim | Medio | Sim (universal) |
| MessagePack | Sim | Nao | Nao (binario) | Nao | Sim |
| Protobuf | Sim | Nao | Nao (binario) | Nao | Sim (schema) |
| Parquet | Sim | Sim | Nao (binario) | Nao | Sim |
| Apache Arrow | Sim | Sim | Nao | Nao | Sim |
| **TCF** | **Futuro** | **Sim (textual)** | **Sim** | **Sim** | **Planejado (T-multi-lang)** |

**Nicho do TCF:** o unico formato que e **textual + comprimido + LLM-friendly + cross-language**. Todos os outros sacrificam uma dimensao.

## Findings esperados

- **F100-F109:** tempo de encode por nivel (hipotese: L3 e o mais lento, L0 o mais rapido)
- **F110-F119:** tempo de decode (hipotese: todos os niveis sao rapidos, <10ms para 1000 rows)
- **F120-F129:** tabela de ratios por algoritmo de compressao × formato × escala
- **F130:** calculo de economia anual em dolares para cenario realista

## Tarefas

- [ ] Implementar run_encode_decode_benchmark.py (sem LLM)
- [ ] Implementar run_http_compression_full.py (brotli + zstd)
- [ ] Implementar run_http_latency_simulation.py (encode+compress+decompress+parse)
- [ ] Documentar findings em article/07 como secao "TCF as Protocol"
- [ ] Gerar figuras: ratio bars, latency lines, savings chart
