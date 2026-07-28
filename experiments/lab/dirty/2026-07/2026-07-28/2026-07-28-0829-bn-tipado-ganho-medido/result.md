# T-BN-TIPADO — o ganho, medido (2026-07-28-0829)

O bN de domínio está soldado (ADR-0036) **só na rota flat**. A rota tipada (`#TCF.8<tag>`) não o alcança porque o wire `#TCF.8B…` devolve **string**, e ali o tipo tem de ser preservado.

```
#TCF.8 b B 2 c8
       │ │ │ └── n em hex
       │ │ └──── w = largura em bits
       │ └────── modo, INDICE 7   <- o slot JA' existe
       └──────── tag de tipo, indice 6
```

`_decode_typed` já faz `resto = line1[7:]` e `modo_c = resto[:1]`. Acrescentar `B` é **um ramo no dispatch existente**, não gramática nova.

## A — o ganho, por coluna (n=200)

| coluna | n | tag | w | hoje | bN tipado | Δ | RT |
|---|---:|:-:|---:|---:|---:|---:|:-:|
| `bool-puro` | 200 | `b` | 1 | 47 | 58 | **+11** | OK |
| `bool-null` | 200 | `b` | 2 | 546 | 94 | **-452** | OK |
| `bool-null-esparso` | 200 | `b` | 2 | 601 | 94 | **-507** | OK |
| `int-k2` | 200 | `n` | 1 | 610 | 55 | **-555** | OK |
| `int-k4` | 200 | `n` | 2 | 606 | 90 | **-516** | OK |
| `int-k4-null` | 200 | `n` | 3 | 587 | 130 | **-457** | OK |
| `int-k8` | 200 | `n` | 3 | 597 | 128 | **-469** | OK |
| `float-k3` | 200 | `n` | 2 | 612 | 93 | **-519** | OK |
| `float-k3-null` | 200 | `n` | 2 | 590 | 101 | **-489** | OK |
| `float-k6` | 200 | `n` | 3 | 620 | 152 | **-468** | OK |
| `misto-int-float` | 200 | `n` | 2 | 610 | 98 | **-512** | OK |
| `float-integral` | 200 | `n` | 1 | 612 | 59 | **-553** | OK |
| `neg-zero` | 200 | `n` | 2 | 614 | 96 | **-518** | OK |

Vence em **12 de 13**; ganho somado nas vencedoras: **-6015 B**.

Eu tinha registrado só `bool + null` (−452 B). **`int` e `float` de cardinalidade baixa estavam igualmente descobertos** — e ganham mais.

## B — onde a proposta deve PERDER

Sem estes, a tabela A não significa nada.

| coluna | n | tag | w | hoje | bN tipado | Δ | RT |
|---|---:|:-:|---:|---:|---:|---:|:-:|
| `int-k200-unicos` | 200 | `n` | 8 | 48 | 322 | **+274** | OK |
| `int-ordenado` | 200 | `n` | 8 | 38 | 315 | **+277** | OK |
| `float-alta-card` | 200 | `n` | 8 | 1309 | 1979 | **+670** | OK |
| `bool-constante` | 200 | `b` | — | 18 | — | — | — |
| `int-k1` | 200 | `n` | — | 17 | — | — | — |
| `n-pequeno-k2` | 3 | `n` | 1 | 19 | 22 | **+3** | OK |
| `int-grande-k4` | 200 | `n` | 2 | 626 | 110 | **-516** | OK |

Perde ou recusa em **6 de 7** — que é o comportamento correto. O `bool-constante` e o `int-k1` caem no `k<=1`, onde o core já é ótimo com RLE; os de alta cardinalidade pagam o domínio inteiro.

O `bool-puro` da tabela A é o contra-caso mais instrutivo: o **denso `b1` de hoje tem domínio IMPLÍCITO** (`false`/`true` não viajam) e ganha do bN. Logo o bN é **mais um candidato do `min()`**, não substituto de nada.

## C — onde vira, varrendo `k` e `n`

| k | hoje | bN | Δ |
|---:|---:|---:|---:|
| 2 | 608 | 55 | **-553** |
| 3 | 607 | 91 | **-516** |
| 4 | 604 | 93 | **-511** |
| 6 | 607 | 135 | **-472** |
| 8 | 601 | 135 | **-466** |
| 12 | 634 | 169 | **-465** |
| 16 | 655 | 170 | **-485** |
| 32 | 645 | 203 | **-442** |
| 64 | 554 | 247 | **-307** |
| 128 | 315 | 281 | **-34** |

| n | hoje | bN | Δ |
|---:|---:|---:|---:|
| 2 | 16 | 22 | **+6** |
| 5 | 21 | 25 | **+4** |
| 10 | 36 | 26 | **-10** |
| 20 | 66 | 30 | **-36** |
| 50 | 156 | 41 | **-115** |
| 200 | 606 | 90 | **-516** |
| 1000 | 3006 | 358 | **-2648** |

## D — colunas REAIS tipadas

Os CSV do repo dão string; aqui o lab converte para `int`/`float`/`bool` — que é exatamente o que um consumidor faria antes de chamar o `encode`.

| coluna | n | tag | w | hoje | bN tipado | Δ | RT |
|---|---:|:-:|---:|---:|---:|---:|:-:|
| `real-adult-sex-bool` | 100 | `b` | 1 | 31 | 42 | **+11** | OK |
| `real-adult-class-bool` | 100 | `b` | 1 | 31 | 42 | **+11** | OK |
| `real-cnpj-matriz-int` | 2000 | `n` | 1 | 429 | 354 | **-75** | OK |
| `real-pm25-Is-int` | 100 | `n` | 5 | 89 | 137 | **+48** | OK |
| `real-pm25-Ir-int` | 100 | `n` | — | 16 | — | — | — |
| `real-pm25-month-int` | 100 | `n` | — | 16 | — | — | — |
| `real-adult-eduint` | 100 | `n` | 4 | 294 | 126 | **-168** | OK |
| `real-tpch-acctbal-float` | 20 | `n` | 5 | 161 | 222 | **+61** | OK |

## E — impacto nos gates byte-canônicos

Colunas dos gates que passam pela rota TIPADA: **0 de 12** (nenhuma).

Os gates carregam `list[str]` lida de CSV, então vão todos pela rota **flat**. **Nenhum baseline moveria** — D1-D9 1545, D17a 300, real-world 89430.

## F — round-trip

`RT` compara **valor, tipo, sinal e comprimento**. O `-0.0` merece nota: em Python `-0.0 == 0.0`, então só o `copysign` pega a troca de sinal.

- colunas com RT estrito OK: **28/28**
- o protótipo usa `dominio_bn.decode_bn` e `decoder._cast_tipo` **do `src/tcf`** — nenhuma reimplementação, então o que se mede aqui é o que a solda produziria.

## O custo de soldar

| ponto | mudança |
|---|---|
| `encoder.py` rota tipada | injetar a tag e somar aos `candidatos` do `min()` que já existe |
| `decoder.py` `_decode_typed` | ramo `modo_c == 'B'` |
| conversão de tipo | **zero** — `_cast_tipo` como está |
| `dominio_bn.py` | **zero** — já soldado e testado |

É fiação, não mecanismo.

