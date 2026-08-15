# Procedência dos dados — e o viés declarado

## Inteiramente sintético, por decisão do owner

> *"é absolutamente fácil achar um corpus com datetime, ao mesmo tempo que não é necessário
> nesse momento. E mesmo o sintético é muito simples e na maioria das vezes os tipos são
> comportados, já que têm origem em bancos de dados que já tratam esse tipo de dado como
> canônico."*

O lab roda **sem `Z:`**. Nada aqui vem do corpus.

## Geração

Tudo em `casos.py`, **sem `random`** — um LCG determinístico (`_lcg`), para o lab ser
reprodutível byte-a-byte. Instante base: `2026-03-02 08:26:00` (uma segunda-feira).

**Os dois eixos nunca variam juntos**: o Bloco 1 fixa o regime (`r_comercial`) e varia a
grafia; o Bloco 2 fixa a grafia (`g_sql_espaco`) e varia o regime. Cruzá-los daria 104 colunas
sem dizer qual eixo explica o resultado.

## As 13 grafias — por que estas

Cada uma é o **default de algum produtor real**, não invenção:

| grafia | quem emite assim |
|---|---|
| `YYYY-MM-DD HH:MM:SS` | SQLite, MySQL `DATETIME` — e é a do corpus |
| `...T...` | ISO 8601, JSON, .NET |
| `...T...Z` · `...-03:00` | RFC 3339 (UTC e com offset) |
| `.ffffff` · `.fff` | PostgreSQL `timestamp` · SQL Server `datetime2(3)`, Java |
| `HH:MM` sem segundo | formulário, relatório |
| `YYYYMMDDHHMMSS` | mainframe, COBOL, chave composta |
| `YYYYMMDDTHHMMSS` | ISO 8601 forma básica |
| `DD/MM/YYYY` · `MM/DD/YYYY AM/PM` | convenção pt-BR · US |
| epoch s · epoch ms | Unix · Java/JavaScript |

## Os 8 regimes — e o viés de cada um

| regime | construção | viés declarado |
|---|---|---|
| `r1-comercial` | 08–18h, sem sábado, segundo `00`, avanço em 4% das linhas | **calibrado para imitar o corpus** (97,61% comercial, segundo constante, alta repetição adjacente). É a única imitação de dado real aqui, e imita **uma** coluna |
| `r2-log-alta-card` | passo de 1–7 s com microssegundo | pior caso de cardinalidade — todo instante distinto |
| `r3-batimento-5min` · `r4-batimento-1s` | progressão exata | **melhor caso possível** para qualquer mecanismo aritmético. Existe para exibir o efeito, não para estimar ganho |
| `r5-esparso-multi-ano` | saltos de 0–3 dias por 5 anos | muitas datas distintas |
| `r6-um-dia-so` | data constante, hora aleatória | isola a metade-hora |
| `r7-constante` | todos iguais | degenerado; existe como piso |
| `r8-comercial-embaralhado` | **os mesmos instantes do r1, permutados** | **o par de contra-prova** — mesma cardinalidade, mesma distribuição, só a ordem muda. É o que isola o `*N|` |

**O viés mais forte do conjunto**: quatro dos oito regimes têm estrutura aritmética ou
repetição alta, porque são justamente os que fazem os mecanismos aparecerem. **Nenhum estima
frequência no mundo.** O que o lab mede é *comportamento sob regime*, e a leitura honesta é
sempre "neste regime, X" — nunca "datetime rende X".

## Nota sobre o `campos-6`

Ele **não reconstrói a grafia** — decodifica para um dict de 6 colunas. Portanto o RT dele é
contra o dict, e ele entra na tabela como **piso** do split, não como concorrente. A diferença
medida (28 B constantes) é o custo do template. Tratar como vitória seria comparação injusta.
