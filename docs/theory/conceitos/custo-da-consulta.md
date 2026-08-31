---
title: "O custo da consulta: por que a view responde barato"
type: explanation
parent: conceitos
subsystem: conceitos
---

# O custo da consulta

A `view` responde perguntas sobre um blob sem descomprimir. Esta página explica o princípio
que torna isso possível, e o que exatamente "barato" quer dizer.

O contrato de cada chamada está na
[referência da `view`](../../reference/lazy-view.md); aqui está o porquê.

## O princípio: oportunista no custo

A `view` busca a **resposta mais completa pela menor evidência suficiente** que já existe no
wire. Ela começa pela fonte segura mais barata para cada pergunta:

1. declarações do header;
2. estrutura compacta, como contadores, separadores e tamanhos;
3. a tabelinha de K valores e o stream de índices de largura fixa;
4. apenas as colunas pedidas e as posições filtradas;
5. uma coluna inteira;
6. materialização completa, somente como fallback de correção.

## O oportunismo é de execução, não de significado

Um caminho estrutural e um fallback precisam devolver **a mesma resposta**. Trocar o modo de
compressão pode mudar o custo, nunca a semântica de vazios, nulos, grupos ou agregados. Se a
estrutura não consegue provar uma resposta com segurança, a `view` decodifica em vez de
adivinhar.

Essa é a regra que separa uma otimização de um bug: um atalho que dá outra resposta não é
mais rápido, é errado.

## O que "menor" quer dizer, e o que ele não promete

"Menor" é o caminho mais barato **já demonstrado** como suficiente, e não uma afirmação sem
prova de ótimo global.

A distinção tem consequência prática no que pode entrar quando. Caminhos estruturais óbvios
e correções podem fechar na superfície atual. Fusão, pushdown posicional e rotas compactas
novas ficam para lab e para o ciclo de otimização do `.9`, porque nelas o custo menor ainda
precisa ser demonstrado.

## De onde vem a economia

Do cabeçalho. Ele declara, por coluna, o nome, o modo e o tamanho, **antes** de qualquer
valor. Então uma pergunta como "quantas linhas?" se responde na declaração, e uma pergunta
como "quais linhas têm `uf = SP`?" abre a coluna `uf` e mais nenhuma.

O modo da coluna decide o resto. Em dicionário, muitas perguntas se respondem sobre os **K
valores distintos** e o stream de índices, sem construir as N linhas: é por isso que um
`n_unique` numa coluna de 600 linhas com 3 valores distintos custa três, e não seiscentos.

Como ler o cabeçalho e reconhecer os modos:
[o wire em uma página](o-wire-em-uma-pagina.md).

## Onde continuar

- o que dá para perguntar, com o custo medido de cada pergunta:
  [`docs/how-to/consultar-sem-decodificar.md`](../../how-to/consultar-sem-decodificar.md)
- o contrato de cada chamada:
  [`docs/reference/lazy-view.md`](../../reference/lazy-view.md)
