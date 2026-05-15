# EXP-008 — Resumo executivo

**Data execucao**: 2026-05-15T04:04:10.940958+00:00

**Datasets**: 15
**Formatos input**: csv, jsonl, json, tcf
**Compressores**: gzip, brotli, zstd, lzma, bz2 (niveis maximos)
**Reps**: serialize/parse=20, compress/decompress=30

## Totais por formato (sem compressao)

| formato | bytes total |
|---|---:|
| csv | _4872_ |
| jsonl | 7001 |
| json | 5409 |
| tcf | **3131** |

**Bold** = formato mais compacto sem compressao. _Italico_ = segundo mais compacto.

## Totais por formato × compressor

| formato | gzip | brotli | zstd | lzma | bz2 |
|---|---:|---:|---:|---:|---:|
| csv | 1978 | **1742** | _1840_ | 2680 | 2328 |
| jsonl | 2214 | **1954** | _2037_ | 2856 | 2666 |
| json | 2057 | **1789** | _1913_ | 2732 | 2446 |
| tcf | 2383 | **2141** | _2228_ | 3276 | 2632 |

Cada celula = **bytes totais** da soma dos 15 datasets comprimidos com (formato, compressor). **Bold** = melhor compressor pra esse formato. _Italico_ = segundo.

## Combinacao mais compacta

- **Vencedor (bytes totais)**: `csv → brotli` com 1742 bytes total (35.8% do raw CSV).
- **Limite inferior empirico** (menor por dataset): `1700` bytes total.

## Roundtrip

- RT formato (parse(serialize(D)) == D): **60/60** OK.
- RT full (parse(decompress(compress(serialize(D)))) == D): **300/300** OK.
- **Sem falhas detectadas.**

## Indice de reports

- [01-bytes-por-formato.md](01-bytes-por-formato.md) — bytes por dataset × formato
- [02-bytes-por-classe.md](02-bytes-por-classe.md) — bytes agregados por classe de compressor
- [03-latencia.md](03-latencia.md) — latencia serialize/parse/compress/decompress
- [04-roundtrip.md](04-roundtrip.md) — verificacao de RT em todas as combinacoes
- [05-campeao-por-dataset.md](05-campeao-por-dataset.md) — menor combinacao por dataset
