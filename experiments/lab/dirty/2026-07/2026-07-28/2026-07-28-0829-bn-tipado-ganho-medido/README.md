# 2026-07-28-0829 — T-BN-TIPADO: o ganho, medido

> *"você disse que 'o ganho é bem maior do que eu tinha registrado', cadê o lab pra provar
> isso?"*

Justo. Os números que apresentei saíram de um probe no terminal — existiam só no meu
scrollback. Este lab materializa a evidência: **28 colunas, RT estrito 28/28**.

## O que eu tinha registrado × o que a medição mostra

Eu tinha anotado no `STATUS.md` apenas **`bool + null`: 546 → 92 B**. A medição mostra que
`int` e `float` de cardinalidade baixa **estavam igualmente descobertos, e ganham mais**:

| coluna (n=200) | tag | w | hoje | bN tipado | Δ |
|---|:-:|---:|---:|---:|---:|
| `int-k2` | `n` | 1 | 610 | 55 | **−555** |
| `float-integral` (`1.0`/`2.0`) | `n` | 1 | 612 | 59 | **−553** |
| `float-k3` | `n` | 2 | 612 | 93 | **−519** |
| `neg-zero` | `n` | 2 | 614 | 96 | **−518** |
| `int-k4` | `n` | 2 | 606 | 90 | **−516** |
| `misto-int-float` | `n` | 2 | 610 | 98 | **−512** |
| `bool-null-esparso` | `b` | 2 | 601 | 94 | **−507** |
| `float-k3-null` | `n` | 2 | 590 | 101 | **−489** |
| `int-k8` | `n` | 3 | 597 | 128 | **−469** |
| `float-k6` | `n` | 3 | 620 | 152 | **−468** |
| `int-k4-null` | `n` | 3 | 587 | 130 | **−457** |
| **`bool-null`** (o que eu tinha) | `b` | 2 | 546 | 94 | **−452** |
| `bool-puro` | `b` | 1 | 47 | 58 | +11 |

**Vence em 12 de 13; ganho somado −6015 B.**

## Os contra-casos — sem eles a tabela acima não significa nada

| coluna | hoje | bN | Δ | |
|---|---:|---:|---:|---|
| `float-alta-card` | 1309 | 1979 | **+670** | o domínio inteiro viaja |
| `int-ordenado` | 38 | 315 | +277 | o core acha a progressão |
| `int-k200-unicos` | 48 | 322 | +274 | idem |
| `n-pequeno-k2` (n=3) | 19 | 22 | +3 | cabeçalho não se paga |
| `bool-constante` · `int-k1` | 18 · 17 | — | — | `k≤1`: **recusa**, o RLE do core é ótimo |
| `bool-puro` | 47 | 58 | +11 | o **denso `b1` tem domínio implícito** e ganha |

**Perde ou recusa em 6 de 7** — que é o comportamento correto. O `bool-puro` é o mais
instrutivo: `false`/`true` não viajam no denso, então o bN é **mais um candidato do `min()`**,
não substituto de nada.

## Onde vira

| k | 2 | 4 | 8 | 16 | 32 | 64 | 128 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Δ | −553 | −511 | −466 | −485 | −442 | −307 | **−34** |

| n | 2 | 5 | 10 | 20 | 50 | 200 | 1000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Δ | +6 | +4 | **−10** | −36 | −115 | −516 | **−2648** |

Vira em **n ≈ 10**, e o ganho cresce linearmente com `n` (o core paga ~3 B/linha, o bN paga
`w` bits).

## Reais

| coluna | n | hoje | bN | Δ |
|---|---:|---:|---:|---:|
| `real-adult-eduint` | 100 | 294 | 126 | **−168** |
| `real-cnpj-matriz-int` | 2000 | 429 | 354 | **−75** |
| `real-pm25-Is-int` | 100 | 89 | 137 | +48 |
| `real-adult-sex-bool` | 100 | 31 | 42 | +11 |
| `real-pm25-Ir-int` · `month-int` | 100 | 16 | — | recusa (`k≤1`) |

Ganho real é mais modesto que o sintético — as colunas tipadas reais que achei têm `n` baixo
ou cardinalidade alta. **Isso está aqui de propósito**: o sintético mostra o teto, o real
mostra o que se colhe.

## A grafia — o slot já existe

```
#TCF.8 n B 3 c8
       │ │ │ └── n em hex (200)
       │ │ └──── w = 3 bits
       │ └────── modo, ÍNDICE 7   ← o slot já existe
       └──────── tag de tipo, índice 6
```

`decoder._decode_typed` já faz `resto = line1[7:]` e `modo_c = resto[:1]`, com
`_LARGURA_MODO = {"1","2","4","8"}`. Acrescentar `B` é **um ramo no dispatch existente** — o
mesmo idioma posicional do ADR-0029, não gramática nova.

O artefato mostra o domínio **comprimido pelo core**, inclusive com seq-RLE:

```
outputs/int-k4-null-bn-tipado.tcfp      outputs/int-k4-null-hoje.tcf
#TCF.8nB3c8                             #TCF.8n
\0                                      0
*3+10|\20      ← seq-RLE no domínio     *3+10|\20
\10                                     \10
=BThTgThThDhTh…                         ^1  …  (587 B)
      (130 B)
```

## Impacto nos gates: nenhum

**0 de 12** colunas dos gates passam pela rota tipada — elas carregam `list[str]` lida de CSV
e vão todas pela rota flat. **D1-D9 1545, D17a 300, real-world 89430 ficam.**

## Validação

RT compara **valor, tipo, sinal e comprimento**. O `-0.0` merece nota: em Python `-0.0 ==
0.0`, então só o `copysign` pega a troca de sinal — e a coluna `neg-zero` existe para isso.

**28/28.** O protótipo usa `dominio_bn.decode_bn` e `decoder._cast_tipo` **do `src/tcf`** —
nenhuma reimplementação. O que se mede aqui é o que a solda produziria.

## O custo de soldar

| ponto | mudança |
|---|---|
| `encoder.py` rota tipada | injetar a tag e somar aos `candidatos` do `min()` que já existe |
| `decoder.py` `_decode_typed` | ramo `modo_c == "B"` |
| conversão de tipo | **zero** — `_cast_tipo` como está |
| `dominio_bn.py` | **zero** — já soldado e testado |

É **fiação, não mecanismo**.

## Limites

- **Nada soldado**; `src/tcf` intocado. Os `.tcfp` são proposta.
- As colunas reais tipadas são **convertidas pelo lab** (o CSV dá string). É o que um
  consumidor faria, mas é uma escolha do lab, não do dado.
- **gzip e CPU não medidos.**
- O modo `C` (domínio por último) não entra aqui — mesma decisão do ADR-0036.
- `NaN`/`±Inf` continuam fora: `_tipo_single_col` os rejeita antes.

## Rodar

```
python run.py
```
`tipado_bn.py` tem o protótipo de fiação (usa `decode_bn` e `_cast_tipo` do `src/tcf`).
