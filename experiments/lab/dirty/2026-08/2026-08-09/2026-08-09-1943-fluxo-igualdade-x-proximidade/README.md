# 2026-08-09-1943 — o fluxo do núcleo: IGUALDADE × PROXIMIDADE

Pergunta do owner sobre a estrutura do fluxo (quebrar similaridades → encaixes; o núcleo
cego × a semântica dos specs; "ver se tem algum encaixe melhor"). Este lab **não propõe
mecanismo** — mede o que cada mecanismo consegue *enxergar*.

Conclusões: [`result.md`](result.md).

## Como rodar

```
python run.py
```

Quatro sondas. `src/tcf` NÃO é tocado — `encode`/`decode` reais + leitura das estruturas
internas pelo caminho que o `_encode_column` de fato usa (pre-pass → OBAT com hint → HCC).

| sonda | pergunta |
|---|---|
| **S1** | o índice do OBAT é Patricia? indexa alguma coisa numa coluna de data? |
| **S2** | o split estrutural (ADR-0026, que já corta `ano\|mês\|dia`) vale quanto, e em que rota está disponível? |
| **S3** | decompondo `ano\|mês\|dia`, qual peça custa caro? |
| **S4** | **a chave**: o que o seq-RLE consegue ler depois que o HCC dedupou? |

## Guia de nomes

| onde | o quê |
|---|---|
| `inputs/<coluna>--json-lib-like.json` | as colunas de data usadas nas sondas |
| `intermediates/S4-*--corpo.txt` | as 20 primeiras linhas do corpo canônico de cada caso do S4 — é onde se vê a virada `\12` → `^1` |
| `outputs/sondas.json` | todas as medições em máquina |

## O achado em uma linha

A leitura aritmética morre na linha **k** (primeira repetição → dedup por referência):
com `k=12` sobram 11 deltas legíveis e o custo é 423 B; a mesma aritmética sem repetição
custa 20 B.
