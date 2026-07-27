# A escada bN — densidade por cardinalidade (2026-07-27-1608)

Você olhou `binario-01-depois.tcf` — 200 valores `"0"`/`"1"` custando **609 B** — e perguntou por que não fica compacto. O motivo é de **rota**, não de conteúdo:

| entrada | rota | bytes |
|---|---|---:|
| `['0','1'] * 100` | `_lista_flat` → core | **609** |
| `[False,True] * 100` | `_tipo_single_col` → denso `b1` | **47** |
| `[False,True,None] …` | denso é bool-**sem-null** → core | **546** |

A oportunidade é da **cardinalidade da coluna**, não do tipo Python da entrada. Com `k` distintos bastam `w = ceil(log2(k))` bits por linha.

## A — a escada, varrendo `k` (n=200, valor curto)

| k | w (bits) | hoje | bN | Δ | RT |
|---:|---:|---:|---:|---:|:-:|
| 1 | 0 | 16 | — | — | — |
| 2 | 1 | 609 | 53 | **-556** | OK |
| 3 | 2 | 607 | 88 | **-519** | OK |
| 4 | 2 | 604 | 91 | **-513** | OK |
| 5 | 3 | 601 | 126 | **-475** | OK |
| 8 | 3 | 592 | 135 | **-457** | OK |
| 9 | 4 | 589 | 174 | **-415** | OK |
| 16 | 4 | 656 | 201 | **-455** | OK |
| 17 | 5 | 660 | 237 | **-423** | OK |
| 32 | 5 | 647 | 297 | **-350** | OK |
| 64 | 6 | 546 | 457 | **-89** | OK |
| 100 | 7 | 420 | 637 | **+217** | OK |
| 150 | 8 | 230 | 919 | **+689** | OK |

`k=1` é o caso que **não precisa de nada**: o core já resolve com RLE (`*200|v0` = 16 B). A escada começa em `k=2`.

## B — onde ela para de ganhar

O domínio **viaja**. Valor longo mata a proposta, mesmo com `k` pequeno:

| len(valor) | k=2 | k=4 | k=16 | k=64 |
|---:|---|---|---|---|
| 1 | -555 | -515 | -468 | -150 |
| 2 | -556 | -513 | -451 | -132 |
| 5 | -555 | -510 | -428 | +39 |
| 10 | -550 | -495 | -353 | +349 |
| 20 | -540 | -465 | -203 | +979 |
| 40 | -520 | -405 | +97 | +2239 |

Negativo = a escada ganha. O cruzamento é onde `k × len(valor)` (o domínio) passa a pesar mais do que os `^N` que o core gastaria.

## Varrendo `n` (k=2, valor curto)

| n | hoje | bN | Δ | Δ/linha |
|---:|---:|---:|---:|---:|
| 2 | 15 | 20 | **+5** | +2.50 |
| 5 | 24 | 20 | **-4** | -0.80 |
| 10 | 39 | 20 | **-19** | -1.90 |
| 20 | 69 | 21 | **-48** | -2.40 |
| 50 | 159 | 29 | **-130** | -2.60 |
| 100 | 309 | 37 | **-272** | -2.72 |
| 500 | 1509 | 102 | **-1407** | -2.81 |
| 2000 | 6009 | 354 | **-5655** | -2.83 |

**`n` pequeno anula a proposta** — abaixo de ~10 linhas o cabeçalho e o domínio não se pagam. É o mesmo achado que o estudo de `bN-dense` multi-col já tinha registrado no `STATUS.md`.

## C — `null` não é caso especial

Hoje o `null` **desliga** o denso (`if tag == 'b' and not tem_nulo`). Na escada ele é só mais um valor do domínio — e o formato **já reserva o slot 0** pra ele, então a grafia do domínio usa o mesmo `0` cru que o core usa pro `^0`.

| coluna | k (c/ null) | w | hoje | bN | Δ | RT |
|---|---:|---:|---:|---:|---:|:-:|
| `bool-sem-null` | 2 | 1 | 47 | 58 | **+11** | OK |
| `bool-com-null` | 3 | 2 | 546 | 92 | **-454** | OK |
| `str01-sem-null` | 2 | 1 | 607 | 52 | **-555** | OK |
| `str01-com-null` | 3 | 2 | 540 | 86 | **-454** | OK |
| `status-4-com-null` | 5 | 3 | 587 | 137 | **-450** | OK |

O `bool-com-null` é o caso que mais expõe a lacuna de hoje: o `null` sozinho faz o wire pular de 47 B para 546 B.

## D — colunas reais de cardinalidade baixa

| coluna | n | k | w | hoje | bN | Δ | RT |
|---|---:|---:|---:|---:|---:|---:|:-:|
| **`adult-sex`** | 100 | 2 | 1 | 205 | 43 | **-162** | OK |
| **`adult-class`** | 100 | 2 | 1 | 199 | 42 | **-157** | OK |
| **`adult-race`** | 100 | 5 | 3 | 157 | 119 | **-38** | OK |
| **`adult-relationship`** | 100 | 5 | 3 | 303 | 110 | **-193** | OK |
| **`adult-workclass`** | 93 | 6 | 3 | 234 | 129 | **-105** | OK |
| **`cnpj-uf`** | 2000 | 28 | 5 | 6378 | 1764 | **-4614** | OK |
| **`cnpj-situacao`** | 2000 | 2 | 1 | 425 | 354 | **-71** | OK |
| **`cnpj-matriz`** | 2000 | 2 | 1 | 428 | 352 | **-76** | OK |
| **`pm25-cbwd`** | 100 | 4 | 2 | 61 | 59 | **-2** | OK |
| **`ibge-uf`** | 100 | 3 | 2 | 28 | 56 | **+28** | OK |

## E — a decisão é `[stream]`?

Pelo guia do `.9`, isto cai em **A (FLOOR de bytes)** com um **gate C** de cardinalidade. A pergunta é se dá pra decidir **sem materializar**.

O custo do bN é uma **fórmula fechada**:

```
w      = ceil(log2(k))
custo  = cabecalho + soma_len(dominio) + k + base64(ceil(n*w/8))
```

E os dois insumos — `k` e a soma dos comprimentos — **já são computados hoje** por `analyze_column` (`n_unicas`, `avg_len`) e pelo dedupe do `_encode_column` (`unicas`). Nenhuma varredura nova.

| coluna | custo CALCULADO | bN medido | bate? |
|---|---:|---:|:-:|
| k=2, n=200 | 53 | 53 | sim |
| k=4, n=200 | 91 | 91 | sim |
| k=16, n=200 | 201 | 201 | sim |
| k=64, n=200 | 457 | 457 | sim |

Divergências entre a fórmula e a medição: **0** — a decisão é uma conta, como a da polaridade.

Ou seja: entra como candidato do `min()` **sem custo de materialização** — não repete a dívida dos outros 8 FLOORs.

## O que isto NÃO resolve

- **`k=1`**: o core já é ótimo (RLE `*N|valor`). A escada deve recusar.
- **`n` pequeno**: abaixo de ~10 linhas o cabeçalho+domínio não se pagam.
- **valor longo**: o domínio viaja; `k × len(valor)` é o teto real, não `k`.
- **ordem**: o bitpack destrói a estrutura que o OBAT/HCC explorariam — só vale onde não há composição a achar, que é exatamente o regime de cardinalidade baixa.
- **gzip**: não medido aqui. O estudo multi-col registrou que o gzip encolhe muito o ganho do bN (`STATUS.md`).

