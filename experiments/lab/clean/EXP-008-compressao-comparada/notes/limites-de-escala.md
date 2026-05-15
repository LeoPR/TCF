# Limites de escala no EXP-008

## Tamanho dos dados

D1-D15 sao **datasets de controle**, projetados pra cobrir
variedade de **formato semantico**, nao escala. Estatisticas:

- Linhas por dataset: 12-20
- Raw CSV bytes/dataset: 160-537 (mediana ~341)
- Raw CSV total (D1-D15): 4872 bytes

## Por que importa pra interpretacao

Compressores de fluxo geral tem **overhead fixo** independente
do input:

| Compressor | Header overhead aproximado |
|---|---:|
| gzip | ~18 bytes (mtime=0) |
| brotli | ~3 bytes |
| zstd | ~10-15 bytes (depende do level) |
| lzma | ~40 bytes (xz container) |
| bz2 | ~6 bytes |

Pra um dataset de 200 bytes raw, gzip puro consome ~18 bytes em
header — **9% do input vira overhead obrigatorio**. Em datasets
de 5 KB, mesmo overhead e' 0.4%.

Conclusao operacional: **resultados de bytes em D1-D15 sao um
fragmento — nao representam o regime de uso real do TCF**.

## Implicacoes

### Para TCF stand-alone

TCF acompanha proporcao raw (sem overhead fixo significativo em
v0.6; o `~` marker e' inline). Em datasets maiores, espera-se
ratio **monotono** (mais redundancia → mais compactacao).

### Para compressores gerais

- Em D1-D9 (raw ~150-540 bytes): brotli compete bem por causa
  do **dicionario estatico** pre-loaded de 120 KB (otimizado pra
  text/HTML/CSS/JS).
- Em datasets maiores (10 KB+), o dicionario estatico se torna
  marginal e a **redundancia local** domina.

### Para o stack `tcf → C`

EXP-008 mostra `tcf → C` quase sempre **piora** vs `C` puro nessa
escala. Hipoteses (nao validadas):

1. **Overhead estrutural do TCF supera reducao**: marcadores `~`,
   `*N`, `\` por linha. Em datasets pequenos, esses marcadores
   sao % alto do output TCF.
2. **Brotli ja' explorou a mesma redundancia**: dicionario
   estatico + LZ77 + Huffman captura prefix/suffix locais que TCF
   tambem captura. Sobreposicao alta → composicao penaliza.
3. **Escala muda o jogo**: em datasets maiores, OBAT detecta
   redundancia em **escopo maior** (LCP/LCS bidirecional varre
   todo o buffer) enquanto brotli tem **janela limitada** (32 KB
   typical).

## O que EXP-008 NAO mede

- **Escala variavel**: D1-D15 sao todos pequenos. Replicas com
  N=100, 1k, 10k linhas mostrariam tendencia.
- **Cardinalidade alta**: datasets de controle tem 12-20 valores
  unicos. Cardinalidades reais podem ser milhares de unicos com
  padroes esparsos.
- **Memoria**: footprint em RAM dos compressores nao foi medido.
  Brotli q=11 usa ~24 MB de working memory; lzma usa mais ainda.
  TCF e' streaming-friendly em principio.

## Direcoes pra fechar essas lacunas

| Experimento futuro | Pergunta | Datasets necessarios |
|---|---|---|
| EXP-010 escala | Razao de TCF varia com N? | D1-D9 inflados (N=100, 1k, 10k) |
| EXP-011 cardinalidade | TCF mantem ratio em cardinality alta? | Datasets sinteticos de cardinalidade controlada |
| EXP-012 memoria | Footprint RAM TCF vs gzip/brotli/zstd | medicao com tracemalloc / psutil |
| EXP-013 reais | Comportamento em Adult Census, TPC-H | datasets canonicos |

## Conclusao para leitor

**Bytes de EXP-008 valem como teto inferior em controle, nao como
prognostico em producao.** Reports tem que mencionar isso pra evitar
"TCF perde pra brotli em todos os datasets" como conclusao
generalizada. A conclusao correta e' "TCF perde pra brotli **neste
regime de escala**".
