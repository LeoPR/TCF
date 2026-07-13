# Lab 2026-07-13-0156 — TCF vs compressores de HTTP e Parquet

**Tipo**: experimento (probatorio) · **Status**: fechado-medido · **RT**: 4/4 True

## Pergunta

CLAUDE.md diz: TCF **nao compete** com gzip/brotli/zstd — ocupa area textual/inspecionavel,
e "se compoe" com eles. Este lab MEDE essa afirmacao em vez de assumi-la:

1. TCF sozinho vs cada compressor sozinho (sobre o dado cru).
2. **Composicao**: `compressor(TCF)` vs `compressor(raw)` — TCF ajuda a camada de transporte
   HTTP (`Content-Encoding`) ou a pagina Parquet, ou atrapalha?
3. Trade-off de legibilidade: TCF continua texto ASCII; os demais viram blob opaco.
4. **Tempo** (compress/descompress, throughput MB/s) e **memoria** (`view()` seletivo vs
   decode/descompressao total) — descomprimir MENOS custa proporcionalmente menos tempo e memoria.

## Familias medidas

- **HTTP `Content-Encoding`**: gzip (nivel 6), brotli (q=11), zstd (nivel 19) — o que trafega online.
- **Parquet column chunks**: snappy, zstd, lz4, gzip — o que existe dentro de um `.parquet`.
  (zstd/gzip aparecem nos dois mundos.)

## Datasets

As 3 colunas free-text reais do gate byte-canonical (`datasets/samples/`) + 1 tabela multi-col
sintetica realista (2000 linhas x 5 colunas, seed 20260713) pra exercitar `#TCF.8M`.

## Como rodar

```
python driver.py            # bytes: raw/TCF/composicao + amostras + contra-prova RT
python timing_memory.py     # tempo (throughput MB/s) + memoria (view vs decode, tracemalloc)
python gen_svg.py           # docs/img/view-memory.svg (barras proporcionais aos bytes medidos)
python gen_result.py        # gera result.md a partir dos dois JSON
```

## Artefatos (rastreabilidade)

Por dataset, em `artifacts/`:
- `*.01-input-sample.txt` — amostra do dado cru de entrada.
- `*.02-tcf-output-sample.txt` — amostra do `#TCF` gerado (o que se transmite).
- `*.03-rt-counterproof.txt` — **contra-prova**: `decode(encode(x)) == x` + bytes.
- `results.json` — medicao completa.

Ver **`result.md`** para os numeros e a leitura.
