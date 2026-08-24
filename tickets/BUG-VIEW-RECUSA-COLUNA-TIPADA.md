---
title: "BUG-VIEW-RECUSA-COLUNA-TIPADA: uma coluna int ou bool tira a tabela inteira do view()"
status: open
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

- [ ] `view()` aceita tabela retangular com coluna tipada, mantendo a laziness (decodificar
      só a coluna consultada), ou está registrado por que isso não é possível.
- [ ] Os agregadores devolvem o tipo do dado, e continuam tolerando a coluna em texto.
- [ ] O que não é tabela retangular (aninhado, ragged) segue com fail-loud, e a mensagem
      diz o que fazer.
- [ ] Round-trip preservado nas duas rotas; gates byte-canônicos verdes ou re-pin registrado.
- [ ] Os exemplos da documentação passam a usar o tipo natural.

## Decisão pendente do owner

A investigação de 2026-08-23 levanta as opções (ler `.8H` no view; dar tag de tipo ao `.8M`;
ou um híbrido) com custo e risco de cada uma. **Nada em `src/tcf` antes da escolha.**
