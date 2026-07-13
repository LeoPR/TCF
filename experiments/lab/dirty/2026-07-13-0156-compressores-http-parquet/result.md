# Resultado — TCF vs compressores HTTP/Parquet (2026-07-13)

> Gerado por `gen_result.py` a partir de `artifacts/results.json`. RT 4/4 True.
> `tcf_helps` = 1 - comp(TCF)/comp(raw): **positivo** = TCF+compressor menor que
> compressor(raw) (TCF ajuda a camada); **negativo** = TCF atrapalha o compressor.

## retail-description-2k  (2000 linhas x 1 col)  ·  RT=True

- raw = **55897 B** · TCF = **27581 B** (TCF sozinho: **50.66%** menor que o cru)

| compressor | comp(raw) | comp(TCF) | tcf_helps |
|---|---:|---:|---:|
| gzip | 12758 | 13725 | -7.58% |
| brotli | 11333 | 12497 | -10.27% |
| zstd | 11628 | 13360 | -14.90% |
| snappy | 20926 | 21084 | -0.76% |
| lz4 | 22120 | 20491 | +7.36% |

## retail-stockcode-2k  (2000 linhas x 1 col)  ·  RT=True

- raw = **12236 B** · TCF = **11437 B** (TCF sozinho: **6.53%** menor que o cru)

| compressor | comp(raw) | comp(TCF) | tcf_helps |
|---|---:|---:|---:|
| gzip | 4471 | 5118 | -14.47% |
| brotli | 3654 | 4696 | -28.52% |
| zstd | 3784 | 4836 | -27.80% |
| snappy | 7562 | 8466 | -11.95% |
| lz4 | 7865 | 8657 | -10.07% |

## lineitem-comment-2k  (2000 linhas x 1 col)  ·  RT=True

- raw = **55940 B** · TCF = **50598 B** (TCF sozinho: **9.55%** menor que o cru)

| compressor | comp(raw) | comp(TCF) | tcf_helps |
|---|---:|---:|---:|
| gzip | 13914 | 19194 | -37.95% |
| brotli | 12718 | 17355 | -36.46% |
| zstd | 12923 | 18229 | -41.06% |
| snappy | 22940 | 30217 | -31.72% |
| lz4 | 25895 | 30264 | -16.87% |

## cadastro-multi-2k  (2000 linhas x 5 col)  ·  RT=True

- raw = **111467 B** · TCF = **30788 B** (TCF sozinho: **72.38%** menor que o cru)

| compressor | comp(raw) | comp(TCF) | tcf_helps |
|---|---:|---:|---:|
| gzip | 18794 | 11791 | +37.26% |
| brotli | 12411 | 8669 | +30.15% |
| zstd | 13807 | 10552 | +23.57% |
| snappy | 34483 | 17314 | +49.79% |
| lz4 | 33716 | 19889 | +41.01% |

## Leitura

1. **TCF sozinho sempre encolhe vs o cru** (6,5% a 72%), continuando texto ASCII inspecionavel.
2. **Coluna free-text unica** (retail-description, stockcode, lineitem-comment): os compressores
   binarios ganham em ratio absoluto sobre o TCF sozinho, e compor `comp(TCF)` em geral **atrapalha**
   o compressor (−7% a −41%) — a reescrita em referencias do TCF perturba o modelo de entropia dele,
   que ja acha aquelas repeticoes sozinho. Nesse regime o valor do TCF e' **legibilidade**, nao ratio.
3. **Tabela multi-coluna estruturada** (cadastro 2000x5): TCF sozinho fica **72% menor** que o CSV,
   E compor ajuda o compressor **+24% a +50%** (ex.: TCF+brotli 8669 B < brotli(raw) 12411 B).
   Aqui o TCF ganha nos DOIS eixos — o que ele fatora (padroes de campo, colunas dict) segue
   comprimivel pela camada de transporte.

**Conclusao (honesta):** a frase 'gzip/brotli compoem por cima' vale para **dados estruturados**
multi-coluna; para **coluna free-text densa unica** o compressor binario sozinho vence e o TCF
por baixo atrapalha — ali o TCF entrega inspecionabilidade, nao menor payload. zstd/gzip do mundo
Parquet exibem o MESMO padrao dos de HTTP (a estrutura, nao o container, decide).
