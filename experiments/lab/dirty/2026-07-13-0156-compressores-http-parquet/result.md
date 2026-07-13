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

## Tempo (proporcional ao volume) — mediana N=9, com warmup

> **Caveat de portabilidade** (CLAUDE.md F0-3): os ms ABSOLUTOS sao desta maquina.
> O invariante e' o **throughput (MB/s)** e o fato estrutural: descomprimir menos custa
> proporcionalmente menos tempo. Tempo NUNCA e' pinado em teste.

### retail-description-2k  (entrada 27581 B de texto TCF)

| codec | comp (ms) | decomp (ms) | comp MB/s | decomp MB/s |
|---|---:|---:|---:|---:|
| gzip | 1.4151 | 0.2098 | 19.5 | 65.4 |
| brotli | 48.0961 | 0.229 | 0.6 | 54.6 |
| zstd | 8.1095 | 0.0985 | 3.4 | 135.6 |
| snappy | 0.1201 | 0.0421 | 229.7 | 500.8 |
| lz4 | 0.119 | 0.0203 | 231.8 | 1009.4 |

### lineitem-comment-2k  (entrada 50598 B de texto TCF)

| codec | comp (ms) | decomp (ms) | comp MB/s | decomp MB/s |
|---|---:|---:|---:|---:|
| gzip | 2.7798 | 0.3063 | 18.2 | 62.7 |
| brotli | 93.5571 | 0.2859 | 0.5 | 60.7 |
| zstd | 20.8515 | 0.1221 | 2.4 | 149.3 |
| snappy | 0.2012 | 0.0739 | 251.5 | 408.9 |
| lz4 | 0.2013 | 0.0359 | 251.4 | 843.0 |

### cadastro-multi-2k  (entrada 30788 B de texto TCF)

| codec | comp (ms) | decomp (ms) | comp MB/s | decomp MB/s |
|---|---:|---:|---:|---:|
| gzip | 2.0493 | 0.1716 | 15.0 | 68.7 |
| brotli | 61.1279 | 0.2278 | 0.5 | 38.1 |
| zstd | 10.7469 | 0.1133 | 2.9 | 93.1 |
| snappy | 0.09 | 0.0418 | 342.1 | 414.2 |
| lz4 | 0.0869 | 0.029 | 354.3 | 685.8 |

**Leitura do tempo:** descompressao e' barata em todos (dezenas a centenas de MB/s), mas com um
compressor opaco voce paga a descompressao sobre **100% do payload** antes de qualquer filtro;
no `view()` do TCF paga-se so' sobre a fracao das colunas tocadas. brotli comprime lento (q=11,
~0,5 MB/s) e descomprime rapido; lz4/snappy descomprimem a ~700-1000 / ~410-490 MB/s e comprimem
a ~250-350 MB/s (por isso o Parquet os usa por padrao). O ganho de latencia do TCF nao vem de
descomprimir mais rapido — vem de descomprimir **menos**.

## Memoria — view seletivo vs decode/descompressao total

Pico de memoria Python (tracemalloc) pra responder UMA query no MESMO blob:

| dataset | query | view() pico | decode() pico | materializa (view) | menos memoria |
|---|---|---:|---:|---:|---:|
| online-retail-100x8 (100x8) | `where(Country='United Kingdom').sum(Quantity)` | 10.4 KB | 45.2 KB | 6.3% | 4.34x |
| cadastro-multi-2k (2000x5) | `where(cidade='Sao Paulo').sum(valor)` | 161.1 KB | 636.7 KB | 27.9% | 3.95x |

Um compressor opaco (gzip/brotli/zstd) **exige** inflar o payload inteiro antes de filtrar —
pico = a tabela toda. O `view()` infla so' as colunas que a pergunta toca. Grafico:
[`docs/img/view-memory.svg`](../../../../docs/img/view-memory.svg) (gerado por `gen_svg.py`).
