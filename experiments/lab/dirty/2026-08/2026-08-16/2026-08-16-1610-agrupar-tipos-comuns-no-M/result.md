# Resultado — agrupar tipos comuns: a intuição está certa, o exemplo é o pior caso

n=2000, 4 predições declaradas antes, **todas confirmadas**, 0 falhas.

---

## O resumo em três linhas

1. **Compartilhar a DECLARAÇÃO rende 0,13%** do wire — é ~5 B/coluna, não há o que economizar.
2. **Compartilhar o DOMÍNIO rende em função de `k`, não do tipo**: bool (k=2) dá **0,5%**;
   k=500 dá **21,2%**. **`true/false` é justamente o pior caso da ideia.**
3. **As duas metades somadas valem 1/206 do candidato que falta** — as 5 flags custam 10.079 B
   na tabela contra 1.755 B como colunas isoladas (**5,7×**), e isso é o `T-UM-CAMINHO-SO`.

---

## 1. Metade 1 — compartilhar a declaração (o "header de spec" literal)

| | |
|---|---:|
| linha 1 com nomes | 90 B (10,0 B/coluna) |
| linha 1 sem nomes (`drop_names`) | 46 B (**5,1 B/coluna** — o piso da declaração) |
| **teto** de agrupar 5 flags numa declaração só | **~20 B** |
| como % do wire (16.200 B) | **0,13%** |

O `.8M` já declara cada coluna em ~5 bytes quando os nomes saem. Agrupar cinco delas economiza
quatro declarações — vinte bytes. **P1 confirmada.**

---

## 2. Metade 2 — compartilhar o domínio: quem manda é `k`

Duas colunas do **mesmo domínio**. No modo `@dict` o slot é `<ntable>\n<tabela><stream>`: a
**tabela** é a parte compartilhável, o **stream** de índices é por-linha e não compartilha.

| k | wire | tabela/col | stream/col | teto de compartilhar | % do wire |
|---:|---:|---:|---:|---:|---:|
| **2** (bool) | 4.074 | 20 | 2.000 | 20 B | **0,5%** |
| 6 | 4.106 | 36 | 2.000 | 36 B | 0,9% |
| 50 | 4.558 | 261 | 2.000 | 261 B | 5,7% |
| **500** | 13.957 | 2.956 | 4.000 | **2.956 B** | **21,2%** |
| 2.000 | 27.960 | — | — | 0 B | 0,0% ¹ |

¹ o `@dict` nem se aplica — gate `K < N` (`dict_v2b.py:61`).

**P2 confirmada, e ela reposiciona a proposta**: o eixo não é *"tipos comuns"*, é **tamanho do
domínio sobreposto**. Um grupo de booleanos tem domínio de 2 valores — não há tabela para
economizar. Um par `origem`/`destino` com 500 cidades tem.

E isto **reproduz o que o projeto já mediu**: o `cross-dict`/`H-GDICT` registrou *"GANHA no
regime **same-domain-refs** (origem/destino, de/para, FK repetida): **−19,2% textual**"*. Os
21,2% aqui são o mesmo fenômeno, na mesma faixa.

---

## 3. O confronto — e é aqui que a proposta muda de lugar na fila

| estratégia sobre as 5 flags | bytes |
|---|---:|
| como estão hoje, dentro da tabela | **10.079** |
| como colunas isoladas (modo `#TCF.8B1…`, o bN) | **1.755** |
| **ganho de ter o candidato certo** | **5,7× (−8.324 B)** |
| ganho de agrupar a declaração | 20 B |
| ganho de agrupar o domínio (k=2) | 20 B |

**O candidato que falta vale 206× as duas metades somadas.** **P3 confirmada.**

Não é que agrupar seja ruim — é que ele opera sobre o resto. Enquanto o `.8M` gastar 10.079 B
onde 1.755 bastam, otimizar os 40 B da declaração e do domínio é ruído.

---

## 4. Contra-prova (P4) — domínios disjuntos não têm o que compartilhar

| k | mesmo domínio | disjuntos |
|---:|---:|---:|
| 50 | 261 B | **0 B** |
| 500 | 2.944 B | **0 B** |

Com domínios disjuntos a união das tabelas tem `k1+k2` entradas — não se elimina nada.
**P4 confirmada**, e é exatamente o *"PERDE em disjunto/entidade → híbrido V2"* que o H-GDICT
já havia registrado.

**Consequência de desenho**: agrupar por **tipo** (o critério proposto) não prediz o ganho —
`bool`+`bool` são o mesmo tipo e não compartilham nada útil; `origem`+`destino` podem ser
ambas string e compartilhar 21%. O critério que prediz é **sobreposição de domínio**, que é
detectável no pré-passe (o projeto já calcula cardinalidade por coluna em `column_features`).

---

## 5. O preço em paralelismo — é barreira, não perda

O lab `1530` provou **I2 (independência)**: cada coluna decoda só do seu recorte, e o decode
paralelo é N tarefas independentes (7 threads == serial).

Com domínio compartilhado a tabela vira uma **dependência**: o decode passa a ser **1 tarefa
(a tabela) + N tarefas independentes**. Continua paralelo, com uma **barreira no início** —
uma fase a mais, não uma perda.

E há precedente vivo: o `view` **já faz isso dentro de uma coluna** (lê a tabela do `@` e
depois varre o stream), e o H-GDICT registrou *"lazy lê o dict 1×"* como **ganho**, não custo.

---

## 6. Sobre "sem colisões e ambiguidades" — o que o projeto já sabe

O owner nomeou o problema difícil corretamente. O que já está medido e restringe o desenho:

1. **O marcador do grupo não pode ser qualquer char.** Medido em 2026-08-16: dos chars ASCII,
   **67 são seguros** (o `_parse_meta` fail-louda) e **16 são perigosos** — `a-f`/`A-F` viram
   dígito hex calado (`B178` → size 45.432), e **`+`, `-`, espaço e tab** também são engolidos
   por `int(s,16)`. A regra é comportamental: *só serve se `int(<char>+dígitos,16)` levantar*.
2. **Referência cruzada tem precedente**: o `%split` já embute uma **sub-tabela `.8M`** dentro
   do slot de uma coluna (`multi/split.py:48` recursa em `_encode_multi`). Uma tabela
   compartilhada é a mesma forma, um nível acima.
3. **Nome posicional colide** — `T-META-COLISAO-NOME-POSICIONAL` (lab `1450` P4): coluna
   anônima na posição 0 + coluna nomeada `"0"` faz o decode perder uma coluna calado. Qualquer
   esquema de grupo que introduza um segundo espaço de nomes **precisa do guard antes**.
4. **A ordem já é livre** (lab `1450`): reagrupar colunas não custa nada hoje — corpos
   byte-idênticos em qualquer permutação, 3 B de variação total. **O que falta não é permissão
   de reordenar, é mecanismo que explore a adjacência.**

---

## 7. Onde isto deixa a proposta

- **Não é `.8`.** O cross-dict já foi escopado pelo owner em 2026-06-24: *"B2/B3 cross-dict
  (#TCF.8) + F2/spec-dict/filtros → **0.9**"*. Esta medição **confirma o escopo** em vez de
  reabri-lo.
- **O critério de agrupamento tem de mudar**: de *"tipos comuns"* para **"domínio sobreposto e
  grande"**. É o mesmo mecanismo, com o gatilho certo.
- **A ordem não muda**: fechar o `T-UM-CAMINHO-SO` (candidato certo por coluna, 5,7× aqui)
  vem antes — depois disso, os 21,2% do same-domain passam a ser a maior sobra do `.8M`, e aí
  a proposta vira o próximo item natural, já no `.9`.
