# Tentativa 02 — HCC sozinho (RLE de near-identical tokens)

**Data**: 2026-05-17
**Estado**: ativo
**Macro pai**: [`../README.md`](../README.md)

## Hipotese a validar

**Q15** (`../notas/perguntas-abertas.md`): OBAT ja' isola a variacao
naturalmente (Pref + Lit + Suf). HCC pode RLE-agrupar tokens
near-identical **sem alterar OBAT**.

Se confirmado: separacao Pre / OBAT / HCC e' trivial — OBAT permanece
type-agnostic, intocado. Toda a inteligencia de delta vive no HCC.

## Analise da baseline (insumo)

Body do D11d (110 bytes total, do sub-exp 01):

```
\2026-\05-\15 \09:*\0*\0*:\00      (linha 1, 30 bytes c/ LF)
1~2\1*4                             (linha 2, 8 bytes)
5\2*4                               (linha 3, 6 bytes)
5\3*4                               (linha 4, 6 bytes)
5\4*4                               (linha 5, 6 bytes)
5\5*4                               (linha 6, 6 bytes)
5\6*4                               (linha 7, 6 bytes)
5\7*4                               (linha 8, 6 bytes)
5\8*4                               (linha 9, 6 bytes)
5\9*4                               (linha 10, 6 bytes)
1\1*3,4                             (linha 11, 8 bytes)
1~15,6,4                            (linha 12, 9 bytes)
16,7,4                              (linha 13, 7 bytes)
```

**Linhas 3-10** (48 bytes) tem estrutura **identica** `5\digit*4`,
com digit variando 2..9 (Δ=+1). Esta e' a oportunidade.

Compactacao alvo: `*8+1|5\2*4` (11 bytes c/ LF).
Economia: 48 - 11 = **37 bytes (-34% no body, -16% no .tcf)**.

Body D11h (123 bytes) tem padrao identico em estrutura, so' linha 1
diferente. Mesma economia.

D11c (109 bytes) tem variante: linhas 3-9 em padrao (mais curto),
ganho menor mas analogo.

## Sintaxe proposta

```
*N+1|<template>
```

Significa: N linhas onde o ultimo literal (digit) incrementa +1 a
partir de `<template>`.

**Criterios pra emissao**:
- N >= 2 linhas consecutivas
- Linhas diferem **apenas** em chars de digit (1+ char), na mesma posicao
- Digits formam sequencia aritmetica com Δ=+1

**Compatibilidade com sintaxe canonical**:
- Nao colide com `*N|` (RLE puro): este e' `*N+1|`, distincao pelo `+1`
- Decoder distingue ao parsear o marker
- Future-proof: `*N+2|` (Δ=2), `*N+10|` (Δ=10), etc.

## Arquitetura do fork

`HCCForkSeqRLE(M8AVirtualRefsSyntax)`:

### encode (override)
1. Chama `super().encode(linhas, unicas, tokens, header)` → body canonical
2. Post-process body: scan linhas, detecta runs near-identical
3. Substitui runs por `*N+1|<template>`
4. Retorna body modificado

### decode (override)
- Para cada linha do body:
  - Se comeca com `*N+1|`: parse N, parse template, gera N strings (incrementa digit na ultima posicao varying)
  - Se comeca com `*N|` (RLE puro): comportamento canonical
  - Caso contrario: parse canonical

### Detector de runs
1. Tokeniza cada linha do body em "esqueleto" (chars sem digit) + "posicoes-digit"
2. Compara linhas consecutivas:
   - Mesmo esqueleto (chars nao-digit identicos)
   - Mesmas posicoes de digits
   - Δ=+1 entre digits correspondentes (todas as posicoes)
3. Agrupa em runs >= 2 consecutivos

## Casos esperados

| Dataset | Run esperado | Bytes baseline | Ganho previsto |
|---|---|---|---|
| D11a (12 dias) | 1 run linhas 2-5 (4) + 1 run 7-9 (3) | 87 | ~5-10 bytes |
| D11b (bordas) | nenhum run dominante | 173 | 0 |
| D11c (mensal) | 1 run linhas 3-9 (7) | 109 | ~25 bytes |
| D11d (min) | 1 run linhas 3-10 (8) | 110 | ~37 bytes |
| D11e (mensal datetime) | 1 run de 8 | 121 | ~37 bytes |
| D11f (ms) | 1 run de 8 | 115 | ~37 bytes |
| D11g (us) | 1 run de 8 | 120 | ~37 bytes |
| D11h (ns) | 1 run de 8 | 123 | ~37 bytes |

Total previsto: 7 datasets com ganho. D11b sem ganho (esperado).

## Validacao

- Bytes body antes (sub-exp 01) vs depois (esta tentativa) por dataset
- RT byte-canonical: `decode(encode(linhas)) == linhas` (8/8)
- Tabela comparativa em `result.md`

**Aceite**: 8/8 RT OK + ganho em >= 1 dataset.

## Estrutura

```
02-hcc-sozinho-rle-near-identical/
├── README.md          ← este doc (plano)
├── hcc_fork.py        ← encoder fork
├── decoder.py         ← decoder espelho
├── run.py             ← roda em D11a-h, gera outputs
├── result.md          ← analise pos-execucao
└── outputs/<dataset>/
    ├── 0-tokens-obat.txt
    ├── 1-body-canonical.tcf       (do baseline pra ref)
    ├── 2-body-fork.tcf
    ├── 3-diff-canonical-vs-fork.txt
    └── 4-rt-status.txt
```

## Restricoes (lembrete)

- `src/tcf/` intocado (fork dirty)
- Single-pass mantido (detector e' look-back em body ja' emitido)
- Memoria O(L) na detec (L = num linhas body) — aceitavel pra HCC
  que ja' processa todas as linhas em uma passada

## Hipoteses secundarias a observar

- Se HCC sozinho resolve, **Q15 confirmada** → tentativa 03/04 podem
  reduzir escopo ou cancelar
- Se HCC sozinho parcialmente resolve mas alguns casos escapam,
  identificar quais (informa o que falta pra tentativa 03)
- Se HCC sozinho nao resolve, **Q15 refutada** → OBAT precisa de
  modificacao (tentativa 03/04 ganham importancia)
