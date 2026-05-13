---
title: E-format-comparison-bench — TCF vs CSV/JSON/TOON em multiplos cenarios
type: experiment
status: OPEN
priority: HIGH
created: 2026-04-27
origin: Decisao "TCF como sera comparado com csv, json, toon"
see_also:
  - docs/theory/components/6-test-harness.md (harness)
  - docs/workbench/tickets/open/T-test-harness-mvp.md (depende)
---

# E-format-comparison-bench — comparacao cientifica de formatos

Responder a pergunta central do paper:
> "Em quais cenarios minimos e maximos o TCF funciona bem?
>  Como ele se compara a CSV, JSON, TOON?"

Via **harness** (ver T-test-harness-mvp), rodar:

```
encoders × compressions × scenarios × iteracoes = experimento
```

## Encoders comparados

| Encoder | Status | Nota |
|---------|--------|------|
| TCF v0.4 | a desenvolver | configuracoes top do E-compression-combinations |
| CSV | imediato (csv stdlib) | baseline |
| JSON | imediato (json stdlib) | baseline tabular |
| TOON | precisa biblioteca | competidor sibling — verificar `pip install toon` ou similar |
| Parquet | opcional | binario, comparar so para contexto |

## Compressions

- `none` — text raw
- `gzip` — universal
- `brotli` — moderno

## Cenarios

- `min_dataset` (5×3) — overhead constante
- `adult_100` — single-table real-world
- `tpch_partsupp_100` — multi-tabela com FKs
- `time_series_1000` — high RLE potential
- `wide_random_100` — adverso para TCF
- `nested_flat_100` — flatten de JSON aninhado
- `categorical_heavy` — mix categorico + numerico
- (mais a definir)

## Metricas

| Metrica | Definicao |
|---------|-----------|
| `bytes` | saida final (apos compressor) |
| `bytes_uncompressed` | apenas encoder, sem compressor |
| `compression_ratio` | bytes / bytes_uncompressed |
| `vs_csv` | bytes / csv_with_same_compression |
| `vs_json` | bytes / json_with_same_compression |
| `vs_toon` | bytes / toon_with_same_compression |
| `encode_ms` | tempo encoder |
| `decode_ms` | tempo decoder |
| `roundtrip_ok` | exato? |

## Tabela esperada (formato real do paper)

| Cenario | TCF L2 | CSV | JSON | TOON | Best |
|---------|--------|-----|------|------|------|
| min_5x3 | 240 | 95 | 145 | 130 | **CSV** (TCF tem overhead) |
| adult_100 raw | 5500 | 9000 | 14000 | 7500 | **TCF** |
| adult_100 +gzip | 1500 | 3500 | 4200 | 2200 | **TCF** |
| time_series_1000 raw | 8500 | 35000 | 65000 | 25000 | **TCF** |
| wide_random_100 raw | 4500 | 4200 | 6800 | 5500 | **CSV** |
| ... | ... | ... | ... | ... | ... |

(Numeros ilustrativos — preenchidos pelos experimentos reais)

## Achados a reportar

Para o paper:
1. **Cenarios onde TCF brilha** (com magnitude)
2. **Cenarios onde TCF perde** (com explicacao)
3. **Sinergia TCF + compressao generica** vs CSV+gzip baseline
4. **Custo de encoder/decoder vs ganho em bytes**

## Criterio de aceite

- [ ] 4+ encoders + 3 compressors + 7+ scenarios
- [ ] Manifest JSONL com cada execucao
- [ ] Tabela markdown gerada automaticamente
- [ ] Plots: bytes por encoder/scenario (matplotlib)
- [ ] Documento "min_max_findings.md" resumindo ganhos/perdas

## Dependencias

- T-test-harness-mvp
- TCF v0.4 idealmente; v0.2 funciona como baseline inicial
- TOON: investigar biblioteca disponivel; se nao, **skipar TOON** e
  documentar limitacao

## Impacto estimado

2-3 semanas, depois de E-compression-combinations.

## Notas para revisar

Quando reabrir:
- Resultados em `experiments/results/harness/format-comparison/`
- Saida entra no Cap 5 (Compressao) e Cap 7 (Resultados) do paper
- Se TOON nao disponivel: documentar como limitacao no paper
