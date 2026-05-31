# Tokens (raiz exp 16) vs sintaxes M1.A / M1.B

Este documento explica o que o script `compare_tokens_vs_syntax.py`
mostra: a relacao entre a **semantica abstrata** (tokens do
algoritmo do exp 16) e as **representacoes textuais** das
sintaxes M1.A (escape) e M1.B (quote).

## 3 camadas mostradas

Para cada string unica:

```
  eid=N: 'string original'
    tokens (online.py raiz): [tokens abstratos do algoritmo]
    fragmentos literais: [pedacos literais apos quebras]
    M1.A: linha TCF na sintaxe escape
    M1.B: linha TCF na sintaxe quote
```

- **Tokens**: o que o algoritmo do exp 16 produziu. Vem em 3
  formas: `L('text')` literal, `P(j, k)` pref de no j com k chars,
  `S(j, k)` suf de no j com k chars.

- **Fragmentos literais**: pedacos do que era `L('text')` sub-
  divididos por **quebras propagadas** (positions onde outras
  strings vao referenciar). Cada fragmento ganha um idx.

- **M1.A/M1.B**: como cada sintaxe representa os mesmos tokens.

## O que aprender olhando

### Caso simples (D2 eid=2) — empate

```
eid=2: "d'angelo42@gmail.com"
  tokens: [P(1,8), L('42'), S(1,10)]
  fragmentos: [8:10]='42'
  M1.A: 1,2,3\4\25,6,7      ← '\4\2' (2 escapes)
  M1.B: 1,2,3'42'5,6,7      ← "'42'" (aspas)
```

Token `L('42')` com K=2 digitos. M1.A: +2 escapes. M1.B: +2 aspas.
**Empate em bytes.**

### Caso K=3 — M1.B vence

```
eid=11: "o'connor103@yahoo.com"
  tokens: [L("o'connor103@yahoo"), S(1,4)]
  fragmentos: [0:11]="o'connor103" | [11:17]='@yahoo'
  M1.A: o'connor\1\0\3*@yahoo7    ← '\1\0\3' (3 escapes = 6 chars)
  M1.B: 'o\'connor103'@yahoo7      ← aspas + escape de "'" interno
```

Fragmento "o'connor103" tem K=3 digitos. M1.A: +3 escapes (=6 chars
literais com `\` + digit). M1.B: aspas (+2) + escape de `'` interno
(+1) = +3 chars.

**M1.B ganha 3 bytes** nesse fragmento.

### Caso onde tokens ja escondem ambiguidade — empate forcado

```
eid=4: "ana@gmail.com"
  tokens: [L('an'), S(2,11)]
  fragmentos: [0:2]='an'
  M1.A: an8,3,4,5,6
  M1.B: an8,3,4,5,6
```

Fragmento "an" sem ambiguidade. Tanto M1.A quanto M1.B emitem raw.
**Empate.**

### Caso onde o token nao tem literal (puro ref)

```
eid=8: 'ana@hotmail.com'
  tokens: [P(4,4), S(5,11)]
  fragmentos: (nenhum — so' refs)
  M1.A: 10,8,3,11,5,6
  M1.B: 10,8,3,11,5,6
```

So' refs. Nenhuma sintaxe gasta marcacao. **Empate.**

## Por que olhar isto

A pergunta central: **onde a compressao ja foi feita pelo
algoritmo, e onde os marcadores adicionam custo?**

- Tokens P/S sao "compressao pura" (refs sem custo de marcacao
  alem do separador `,`)
- TokLit com fragmentos limpos (so' letras) sao "literais
  livres" (M1.A e M1.B empatam em raw)
- TokLit com fragmentos contendo digitos sao **onde a sintaxe
  importa** — M1.A escapa, M1.B aspas, e isso decide bytes

Em D1 (emails sem digitos): **0 fragmentos com digito** → M1.A
e M1.B sao **byte-identicos** (162 bytes).

Em D2/D3/D4: alguns fragmentos com digito → M1.A vs M1.B
diferenciam por K.

## Como rodar

```bash
cd 2026-05-12-M1-marcacao-ambiguidade
python compare_tokens_vs_syntax.py
```

Output: 4 datasets × 12 strings com tokens + fragmentos + linhas
TCF em ambas as sintaxes. ~300 linhas no total.

## Para F2

Esta visualizacao e' insumo para a F2 (medir diferencas). Mostra:
- Quanto da compressao e do algoritmo (exp 16, indiscutivel)
- Quanto e' decisao da sintaxe (M1.A vs M1.B vs M1.C vs M1.D)

O algoritmo do exp 16 e' a **maior fonte de compressao**. Os
micros M1.X disputam apenas os bytes residuais.
