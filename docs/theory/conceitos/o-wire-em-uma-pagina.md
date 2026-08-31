---
title: "O wire em uma página: como ler um .tcf a olho"
type: explanation
parent: conceitos
subsystem: conceitos
---

# O wire em uma página

O TCF sai como texto, e a promessa é que dá para abrir e ler. Esta página ensina a ler.
Todos os wires abaixo foram gerados por execução; você pode reproduzir cada um.

## A anatomia

```python
encode(["ana", "bruno", "carla"])
'#TCF.8\nana\nbruno\ncarla\n'
```

Duas partes: a **assinatura** (`#TCF.8`) na primeira linha, e o **corpo** depois. A
assinatura diz a versão do formato e, quando há mais de uma coluna, também o mapa delas.

Sem nada para fatorar, o corpo é o dado. É por isso que o TCF **nunca infla**: no pior caso
ele é o texto original mais o cabeçalho.

## Os dois marcadores que você mais vai ver

**`*N|` é um repetidor de linha.** Ele diz "a próxima linha vale por N":

```python
encode(["sim", "sim", "sim", "nao"])
'#TCF.8\n*3|sim\nnao\n'
```

Três `sim` viraram `*3|sim`. Repare que dá para **contar** três ocorrências sem expandir
nada, e é isso que permite à `view` responder um `count()` sem descomprimir.

**`^N` é uma referência.** Ele aponta para um valor que já apareceu:

```python
encode(["ana", "bruno", "ana"])
'#TCF.8\nana\nbruno\n^1\n'
```

O terceiro valor é `^1`, ou seja "o mesmo que o de índice 1". A numeração é interna ao wire
e o decoder a reconstrói contando na mesma ordem em que o encoder contou.

## O afixo, que é o coração do OBAT

Quando os valores compartilham começo ou fim, o TCF guarda a parte comum uma vez:

```python
encode(["user1", "user2", "user3"])
'#TCF.8\nuser*\\1\n1\\2\n1\\3\n'
```

`user*` é o prefixo fatorado. O `\` antes do dígito é **escape**: ele existe para o `1` do
dado não se confundir com a numeração de referências. O `decode` desfaz o escape exatamente.

É aqui que a densidade aparece: quanto mais o TCF fatora, menos óbvio o texto fica de ler.
**Legível não quer dizer evidente à primeira vista.**

## O cabeçalho de várias colunas

```python
encode({"id": ["1", "2", "3"], "uf": ["SP", "SP", "RJ"]})
'#TCF.8M!5=id,!uf\n1\n2\n3SP\nSP\nRJ'
```

O `M` na assinatura declara multi-coluna. Depois dele vem o meta: `!5=id,!uf` são duas
colunas, `id` e `uf`, com o tamanho da primeira em hexadecimal (`5`) e **a última sem
tamanho**, porque ela vai até o fim.

E repare no corpo: `3SP` numa linha só. **Os corpos vêm concatenados, delimitados por
tamanho, não por quebra de linha.** O `3` é o fim da coluna `id` e o `SP` é o começo da `uf`.
Essa é a economia que o header mínimo compra, e é a coisa que mais confunde quem lê um wire
pela primeira vez.

## Os três modos de coluna

O caractere antes do nome diz como aquela coluna foi guardada. O encoder escolhe sozinho,
por bytes, e cada coluna decide separado:

| marca | modo | quando ganha |
|---|---|---|
| *(nenhuma)* | **tcf** | o caminho normal: OBAT fatora afixos, HCC compõe |
| `!` | **raw** | quando o dado não tem estrutura nenhuma e fatorar sairia mais caro |
| `@` | **dicionário** | poucos valores distintos, muitas linhas |
| `%` | **split** | valor com template uniforme (data, decimal, CPF), fatiado em campos |

O `raw` e o `dicionário` no mesmo dado:

```python
encode({"x": ["q7z", "w2k", "e9m"]})
'#TCF.8M!x\nq7z\nw2k\ne9m'

encode({"uf": ["SP","RJ","SP","RJ","SP","RJ","SP","RJ"]})
'#TCF.8M@uf\n6\nSP\nRJ\n!"!"!"!"'
```

No dicionário, `SP` e `RJ` aparecem **uma vez cada**, e o resto (`!"!"!"!"`) é o stream de
índices, de largura fixa. Oito linhas em quatro bytes.

## Por que isso importa para a consulta

O cabeçalho declara nome, modo e tamanho de cada coluna **antes** de qualquer valor. É por
isso que a `view` consegue responder perguntas lendo pouco: ela lê a declaração, decide se
a estrutura já basta, e só desce até o corpo quando precisa. Ver
[o custo da consulta](custo-da-consulta.md).

## Onde continuar

- a especificação completa, com todos os discriminadores:
  [`docs/algorithms/TCF-format.md`](../../algorithms/TCF-format.md)
- as camadas: [OBAT](../../algorithms/OBAT.md) (afixos) e
  [HCC](../../algorithms/HCC.md) (composição)
- o vocabulário controlado: [`docs/vocabulary.md`](../../vocabulary.md)
