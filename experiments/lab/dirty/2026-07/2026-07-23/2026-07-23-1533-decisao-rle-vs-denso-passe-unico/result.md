# Decisão RLE-vs-denso: determinística e de passe único?

Dados pequenos (viabilidade). UM passe -> lista de runs; dela, tamanho de cada modo por FÓRMULA; materializa os 3 da própria lista de runs. Colunas: `n`/`runs`; bytes previsto (fórmula) vs real por modo; vencedor previsto vs medido; `reads/n` = leituras da fonte sobre n (1.0 = passe único, zero revisitação); `1pass` e `RT` são gates SEPARADOS.

| caso | n | runs | denso prev/real | rle prev/real | misto prev/real | prev→ | medido→ | reads/n | 1pass | RT |
|---|---:|---:|---|---|---|:---:|:---:|:---:|:---:|:---:|
| const-sm | 24 | 1 | 4/4 | 4/4 | 8/8 | denso | denso | 1.0 | ✅ | ✅ |
| const-big | 300 | 1 | 52/52 | 5/5 | 6/6 | rle | rle | 1.0 | ✅ | ✅ |
| few-big | 308 | 3 | 52/52 | 11/11 | 21/21 | rle | rle | 1.0 | ✅ | ✅ |
| alt-big | 200 | 200 | 36/36 | 401/401 | 41/41 | denso | denso | 1.0 | ✅ | ✅ |
| prefix-mix | 260 | 61 | 44/44 | 125/125 | 23/23 | misto | misto | 1.0 | ✅ | ✅ |
| noisy | 120 | 66 | 20/20 | 133/133 | 25/25 | denso | denso | 1.0 | ✅ | ✅ |

## Leitura (viabilidade + onde mexer)

- **Preditor EXATO**: em todos os casos o tamanho por FÓRMULA == tamanho real dos 3 modos. Logo a decisão `min()` NÃO precisa materializar os candidatos — basta computar 3 fórmulas sobre a lista de runs. (denso = `b64_len(n)`, puro f(n); rle/misto = soma sobre runs.)
- **Passe único / zero revisitação**: `reads/n == 1.0` sempre — a fonte é lida UMA vez (o scan de runs); tanto o dimensionamento quanto a materialização dos 3 modos saem da LISTA DE RUNS, nunca revisitando os dados. Serve ao vetor LATÊNCIA.
- **Vencedor previsto == medido** em todos — o argmin das fórmulas acerta o modo real.
- **Onde mexer (indicação)**: a decisão encaixa como um passo BARATO logo após o scan de runs (que o pipeline já faz pra RLE) — não é um loop novo sobre stream já lido, é 3 fórmulas O(nº de runs). Mantém o padrão FLOOR/min() nunca-pior, mas sem o custo de encodar tudo. TROCA de vetor explícita: quer MAIS compressão (misto) -> cede latência (segmentação greedy); quer MENOS latência -> decide por fórmula e emite 1 modo.
- **gzip (sinal)**: em dados minúsculos o gzip nivela; a decisão importa PRE-transporte e em payload cru (terminal/latência), coerente com a memória (eixo não é byte pós-brotli).

**6 casos · 0 falhas.** Regenera: `python run.py`.