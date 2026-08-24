---
title: "BUG-VIEW-RECUSA-COLUNA-TIPADA: uma coluna int ou bool tira a tabela inteira do view()"
status: closed
priority: P1
severity: R1 (erra alto, mas fecha uma porta inteira da API)
created: 2026-08-23
updated: 2026-08-23
gate: decisão de arquitetura do owner antes de qualquer weld; `src/tcf` só com aprovação (I5)
blocked-by: []
related:
  - src/tcf/view.py
  - src/tcf/encoder.py
  - docs/reference/lazy-view.md
  - docs/reference/api.md
---

# BUG-VIEW-RECUSA-COLUNA-TIPADA

## O que acontece

Basta **uma** coluna não-`str` para a tabela inteira sair do `#TCF.8M` e ir para o `#TCF.8H`.
O `view()` só lê `.8M`, então ele recusa a tabela.

```python
encode({"cidade": ["SP", "SP", "RJ"], "valor": ["120", "80", "200"]})  # -> #TCF.8M, view OK
encode({"cidade": ["SP", "SP", "RJ"], "valor": [120, 80, 200]})        # -> #TCF.8H, view ERRA
# ValueError: não é #TCF.8M multi-col
```

Medido em 2026-08-23. O `sum()` sobre a versão string funciona e devolve `float`, então a
consulta numérica existe: o que não existe é a consulta sobre a coluna **tipada**.

## Por que é arquitetura, não um caso de borda

Palavras do owner, que definem a direção:

> o `view` tem que aceitar os números até como forma mais **nativa**, e ser **tolerante** com
> a versão em texto

> o simples fato do tipo primitivo do dataset existir, como num ou bool, já é implicitamente
> um **spec** que não precisa ser declarado, e ele será transportado no header

O tipo primitivo é uma declaração que o dado já traz. Tratá-lo como caso especial inverte a
relação: número e bool são o caso natural, e string é o fallback tolerado.

## O que o wire já oferece

O `.8H` de tabela retangular carrega nome, tamanho e **tipo** por coluna, e o corpo vem
seccionado por coluna:

```
#TCF.8H#Ocidade#:3[]:9,valor#:3[]:14n
```

O `n` final marca o tipo de `valor`, e os sizes (`9`, `14`) delimitam os corpos. A informação
que o `view()` precisa para ser lazy está lá; o que falta é ele saber ler.

## Consequência prática, hoje

Todo exemplo de `view()` na documentação usa número como **string**. Isso não é escolha de
didática: é a única forma que funciona. Um leitor razoável lê o exemplo e conclui que o autor
foi desleixado, quando na verdade a API o obrigou.

## Critério de aceite

- [x] `view()` aceita tabela retangular com coluna tipada, mantendo a laziness (decodificar
      só a coluna consultada), ou está registrado por que isso não é possível.
- [x] Os agregadores devolvem o tipo do dado, e continuam tolerando a coluna em texto.
- [x] O que não é tabela retangular (aninhado, ragged) segue com fail-loud, e a mensagem
      diz o que fazer.
- [x] Round-trip preservado nas duas rotas; gates byte-canônicos verdes ou re-pin registrado.
- [x] Os exemplos da documentação passam a usar o tipo natural.

## Decisão pendente do owner

A investigação de 2026-08-23 levanta as opções (ler `.8H` no view; dar tag de tipo ao `.8M`;
ou um híbrido) com custo e risco de cada uma. **Nada em `src/tcf` antes da escolha.**

## Fechamento

`closed-done` em 2026-08-23, pela **opção A**: a view aprendeu a ler o `#TCF.8H` que é
tabela retangular. Decisão do owner, com a observação que guiou a implementação: *"a
arrumação do view suportar tipos é altamente simples, é como se tivesse declarado só isso"*.
E era: o tipo e os tamanhos já viajavam no header, então o trabalho foi ler o que estava
declarado, não inventar mecanismo.

O que entrou, tudo em `src/tcf/view.py`:

- `_parse_hier` preenche as **mesmas** estruturas internas do `.8M` (`_mode`, `_body`,
  `_order`, `_nature`), então `where`, `sum`, `select` e `group_count` funcionam sem
  uma linha a mais. Cobre as duas formas retangulares: `encode(dict)` e `encode(list[dict])`.
- os valores voltam no **tipo declarado**: `int`, `float`, `bool`, via `_dec_scalar`.
- `where` compara com o tipo **da coluna**. Numa coluna `n`, `where(col, 120)` é a forma
  natural, e `where(col, "120")` levanta `TypeError` dizendo o tipo. Antes, a comparação
  impossível respondia zero linhas em silêncio, nos dois sentidos.
- **nulo** também: um `None` tirava a tabela do `.8M` sem tipo nenhum envolvido. A máscara
  é uma coluna core comum, e a reidratação vem antes da nature e do tipo, senão o
  alinhamento de linha quebraria.
- o que **não** é tabela (aninhado, ragged, campo opcional, raiz escalar) segue recusado,
  agora com mensagem que manda usar `decode()`.

Medido: `view == decode` em valor e tipo; laziness intacta (consulta de 2 colunas em 2000
linhas materializa **9,4%** do blob, `count()` sozinho **4,5%**); suíte 1366 -> **1377**,
gates byte-canônicos verdes **sem re-pin** (a rota é read-only, não toca o encode).

## O que este ticket NÃO resolve

A causa raiz continua de pé: `_tabela_flat` ([encoder.py](../src/tcf/encoder.py)) exige
`all(isinstance(x, str))`, então **uma** coluna tipada tira a tabela do `.8M` e ela perde a
competição `min(tcf, raw, dict, split)`. Medido: +43,6% de bytes no adult-census, +55,6% num
caso sintético de 500 linhas. Junto vão o `schema=` (levanta `HierarchicalError` se qualquer
coluna for tipada) e os knobs do multi-col.

A correção dessa causa é a **opção B** (o `.8M` ganha tag de tipo por coluna), que muda o
formato e é decisão do owner, registrada no `ROADMAP` para antes do `.9`. Detalhe técnico
que já custou uma tentativa: a tag **não** pode vir depois do size, porque `b` é dígito
hexadecimal válido e `@1b=age` parseia como size 27. A única posição livre é o slot `:id`.
