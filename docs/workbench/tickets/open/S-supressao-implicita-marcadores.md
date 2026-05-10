---
title: Supressão implícita de marcadores, espaços e quebras de linha
type: study
status: open
priority: medium
created: 2026-05-10
---

## Contexto

A gramática TCF v0.5 atual usa marcadores explícitos para
desambiguar tokens em uma linha:

| Marcador | Função |
|----------|--------|
| `*<text>` | declaração de fragmento (idx implícito = ordem) |
| `*<N>=<text>` ou `*<N>=<P>+<ext>` | declaração com idx explícito (encadeamento) |
| `<n>` (digitos) | referência a idx |
| `_<text>` | literal numérico (desambig) |
| `=<n>` | referência à linha n |
| `<text>` | literal puro |
| ` ` (espaço) | separador entre tokens |
| `\n` | fim de linha |

Em alguns contextos, esses marcadores podem ser **deduzidos** —
isto é, omitidos sem perda de informação porque o decoder consegue
inferir do contexto.

## Casos onde marcador eh deduzivel

### 1. Espaco entre token-tipo distinto

Se um token termina com letra e o proximo comeca com digito, ja
sabemos que sao tokens distintos sem precisar do espaco.

Exemplo:
```
abc123    →  pode ser parsed como [abc, 123] sem ambiguidade?
```

**Cuidado**: so se a coluna nao permitir alfanuméricos misturados.
Em coluna de texto livre `abc123` eh um token unico. Em coluna
com separacao tipo-tipo, pode ser deduzido.

### 2. Quebra de linha vs separador

Algumas linhas TCF tem so um token (literal puro). Em sequencia,
varias linhas de 1 token poderiam usar separador no lugar de
`\n` se o contexto permitir um delimitador alternativo.

Exemplo: 100 categoricas em coluna de cardinalidade 5:
```
red
red
=1
*green
=1
...
```
vs
```
red red =1 *green =1 ...
```

Em uma fila so. Mas isso quebra o paradigma "1 valor = 1 linha".
Trade-off: legibilidade vs bytes.

### 3. Marcador `_` redundante

`_` desambigua texto de digitos. Se a coluna inteira eh numerica
(declarado no header), o `_` pode ser omitido. Como em:
```
PED-2026-0001  →  body emite "*PED-2026- _0001"
```

Se sabemos pelo header que aquela posicao da linha eh numero, o
`_` vira ruido. **Opcional por header flag**.

## Casos NAO deduziveis

- **Idx vs literal**: `1` pode ser idx 1 ou literal "1". Sem `_` ou
  contexto numerico, ambiguo.
- **Decl vs literal com `*`**: `*green` pode ser declaracao OU
  literal que comeca com `*`. Resolvido por escape ou contexto
  (cabec do tipo da coluna).

## Quando estudar/implementar

Apos lab 24 e port pra clean prototype:
1. Implementar versao baseline (sem supressao)
2. Medir bytes em datasets reais (TPC-H, GitHub events, etc.)
3. Estimar ganho potencial das supressoes
4. Implementar so as que tem ganho >= 5% e nao quebram parsing

## Trade-off honesto

Supressao implicita ganha bytes mas:
- Aumenta complexidade do decoder
- Reduz legibilidade humana (paradigma TCF de "ler com olho")
- Risco de bugs em casos patologicos

Provavelmente fica como **flag opt-in** (`SRDM` vs `SRDMI`?), nao
default.

## Relacionado

- [S-representacao-de-indice](S-representacao-de-indice.md) — mesma
  filosofia "ASCII-safe densidade" mas para idx
- [S-idx-universal-linha-fragmento](S-idx-universal-linha-fragmento.md)
  — proposta de unificacao do namespace
- Lab 22 (deducoes) — explorou D1/D2/D3, marginal ganho mas
  D2 teve ambiguidade
