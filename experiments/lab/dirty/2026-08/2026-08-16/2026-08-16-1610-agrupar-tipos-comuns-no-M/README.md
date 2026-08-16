# Agrupar tipos comuns no `.8M` — as duas metades da ideia, e qual delas tem dinheiro

> **Owner (2026-08-16)**: *"uma estratégia seria agrupar tipos comuns, né? ... grupos de tipos
> comuns, como true/false, podem compartilhar solidariamente o header de spec? ... o problema
> é criar isso no arquivo de forma vantajosa e sem colisões e ambiguidades."*

## A resposta curta

A intuição está certa — há dinheiro em compartilhar. **Mas o exemplo escolhido é o pior caso**,
e o ganho está numa terceira coisa:

| | teto medido |
|---|---:|
| compartilhar a **declaração** de 5 flags | 20 B = **0,13%** |
| compartilhar o **domínio**, bool (k=2) | 20 B = **0,5%** |
| compartilhar o **domínio**, k=500 | 2.956 B = **21,2%** |
| **ter o candidato certo** nas 5 flags | **5,7×** (10.079 → 1.755 B) |

**O tipo não é a variável — o tamanho do domínio sobreposto é.** E as duas metades da proposta
somadas valem **1/206** do candidato que falta.

## O que este lab NÃO reabre

O `cross-dict`/`H-GDICT` já mediu **−19,2% em same-domain-refs** e o owner já escopou:
*"B2/B3 cross-dict → **0.9**"* (2026-06-24). Os 21,2% aqui **reproduzem** aquilo na mesma
faixa — a medição **confirma o escopo**, não pede exceção.

## Estado — era / foi / é / será

- **Era**: "agrupar tipos comuns compartilha o header de spec?"
- **Foi**: separar as duas metades (declaração × domínio) e confrontar com o candidato faltante.
- **É**: 4 predições, todas confirmadas. Declaração 0,13%; domínio governado por `k` (0,5% em
  bool, 21,2% em k=500); disjuntos rendem **zero**; o candidato vale 206× as duas metades.
  Resultado em [`result.md`](result.md).
- **Será**: `.9`, com o **gatilho corrigido** — de "tipos comuns" para "domínio sobreposto e
  grande", detectável no pré-passe que já calcula cardinalidade.

## Sobre "sem colisões e ambiguidades"

O owner nomeou o problema difícil certo. O que já restringe o desenho, medido:

1. **67 chars são seguros como marcador, 16 são perigosos** — `a-f`/`A-F` viram dígito hex
   calado, e **`+`, `-`, espaço e tab** também. Regra: *só serve se `int(<char>+dígitos,16)`
   levantar*.
2. **Referência cruzada tem precedente**: o `%split` já embute uma sub-tabela `.8M` dentro do
   slot de uma coluna (`multi/split.py:48`).
3. **Nome posicional colide** (`T-META-COLISAO-NOME-POSICIONAL`) — o guard vem antes.
4. **A ordem já é livre** (lab `1450`): reagrupar não custa nada hoje. Falta o mecanismo, não
   a permissão.

## O preço em paralelismo: barreira, não perda

O lab `1530` provou I2 (independência das colunas). Domínio compartilhado transforma o decode
de *N tarefas independentes* em *1 tarefa + N independentes* — uma fase a mais. O `view` já faz
isso dentro de uma coluna, e o H-GDICT registrou *"lazy lê o dict 1×"* como ganho.

## Como rodar

```
python run.py    # sai 0 só se os RTs fecharem
```

`src/tcf` intocado. Todas as medidas de "compartilhar" são **tetos** (o duplicado que existe),
não ganhos de mecanismo implementado.

## Vínculo

O-FMT-06 (cross-column) · O-FMT-01/02 (ordenação livre) · cross-dict/H-GDICT (−19,2%,
escopado `.9`) · `T-UM-CAMINHO-SO` · `T-BAIXA-CARD-EM-TABELA` (5–12,8×) ·
`T-META-COLISAO-NOME-POSICIONAL` · `T-META-NAO-DECLARA-MODO` (o alfabeto seguro) ·
labs [`1450`](../2026-08-16-1450-ordem-de-colunas-no-M/) e
[`1530`](../2026-08-16-1530-piso-do-header-e-fronteira-paralela/)
