# 2026-07-27-1608 — A escada bN: densidade por CARDINALIDADE

Você olhou `binario-01-depois.tcf` — 200 valores `"0"`/`"1"` custando **609 B** — e perguntou
por que não fica compacto. O motivo é de **rota**, não de conteúdo:

| entrada | rota | bytes |
|---|---|---:|
| `['0','1'] * 100` | `_lista_flat` → core | **609** |
| `[False,True] * 100` | `_tipo_single_col` → denso `b1` | **47** |
| `[False,True,None] …` | denso é bool-**sem-null** → core | **546** |

A mesma informação, 13× de diferença. E o `null` sozinho desliga o denso
(`encoder.py`: `if tag == "b" and not tem_nulo`).

**Sua leitura está certa: a oportunidade é da cardinalidade da coluna, não do tipo Python da
entrada.** Com `k` distintos bastam `w = ceil(log2(k))` bits por linha.

## A escada mede assim (n=200, valor curto)

| k | w | hoje | bN | Δ |
|---:|---:|---:|---:|---:|
| **1** | 0 | **16** | — | o core já é ótimo: RLE `*200\|v0`. **Não mexer** |
| 2 | 1 | 609 | 53 | **−556** |
| 4 | 2 | 604 | 91 | **−513** |
| 8 | 3 | 592 | 135 | **−457** |
| 16 | 4 | 656 | 201 | **−455** |
| 32 | 5 | 647 | 297 | **−350** |
| 64 | 6 | 546 | 457 | **−89** |
| **100** | 7 | 420 | 637 | **+217** ← vira |
| 150 | 8 | 230 | 919 | +689 |

`k=1` é o caso que **não precisa de nada**. Sua intuição de "com 1 já lança binário" na
verdade não se aplica: o RLE do core resolve em 16 B, e qualquer domínio + b64 seria pior.
A escada começa em `k=2`.

## O teto real não é `k`, é `k × len(valor)`

O domínio **viaja**. Valor longo mata a proposta mesmo com `k` pequeno:

| len(valor) | k=2 | k=4 | k=16 | k=64 |
|---:|---:|---:|---:|---:|
| 1 | −556 | −516 | −469 | −151 |
| 5 | −555 | −510 | −428 | **+39** |
| 20 | −540 | −465 | **−203** | +979 |
| 40 | −520 | −405 | **+97** | +2239 |

E `n` pequeno anula: com `n=2` a proposta **perde 5 B**; passa a ganhar a partir de ~5 linhas,
e satura em ≈ −2,8 B/linha.

## `null` não é caso especial — e o slot 0 já é dele

| coluna | k | hoje | bN | Δ |
|---|---:|---:|---:|---:|
| `bool-sem-null` | 2 | **47** | 58 | **+11** |
| `bool-com-null` | 3 | 546 | 92 | **−454** |
| `str01-sem-null` | 2 | 607 | 52 | **−555** |
| `str01-com-null` | 3 | 540 | 86 | **−454** |
| `status-4-com-null` | 5 | 587 | 137 | **−450** |

Duas coisas aqui:

1. **`bool-com-null` é a lacuna mais gritante**: o `null` sozinho faz o wire pular de 47 para
   546 B.
2. **`bool-sem-null` a escada PERDE (+11 B)** — e isso é correto. O `b1` de hoje tem domínio
   **implícito** (`false`/`true` não viajam); a escada genérica paga o domínio. Ou seja, a
   escada é **mais um candidato do `min()`**, não substituta do `b1`.

## Reais

| coluna | n | k | hoje | bN | Δ |
|---|---:|---:|---:|---:|---:|
| **`cnpj-uf`** | 2000 | 28 | 6378 | 1764 | **−4614** |
| `adult-relationship` | 100 | 5 | 303 | 110 | **−193** |
| `adult-sex` | 100 | 2 | 205 | 43 | **−162** |
| `adult-class` | 100 | 2 | 199 | 42 | **−157** |
| `adult-workclass` | 93 | 6 | 234 | 129 | **−105** |
| `cnpj-matriz` | 2000 | 2 | 428 | 352 | **−76** |
| `ibge-uf` | 100 | 3 | 28 | 56 | **+28** |

`ibge-uf` perde porque o core achou composição e resolveu em 28 B. É o lembrete de que a
escada só vale onde **não há estrutura a explorar** — que é justamente o regime de
cardinalidade baixa com valores curtos.

## A decisão é uma CONTA — não repete a dívida dos outros FLOORs

Pelo guia do `.9` isto cai em **A (FLOOR de bytes)** + **gate C (cardinalidade)**. O custo é
fórmula fechada:

```
w     = ceil(log2(k))
custo = cabeçalho + soma_len(domínio) + k + base64(ceil(n*w/8))
```

**0 divergências** entre a fórmula e a medição em 4 pontos. E os insumos (`k`, comprimentos do
domínio) **já são computados hoje** — `analyze_column.n_unicas` e o `unicas` do dedupe. Então
entra como candidato **sem custo de materialização**, ao contrário dos 8 FLOORs que hoje
encodam os dois lados.

## Um bug achado no caminho — terceira aparição da mesma colisão

O leitor independente pegou: se o domínio grafa o null como `0` cru e um valor de **dado**
também é `"0"`, os dois ficam indistinguíveis e a coluna volta com `None` no lugar da string.
Falhou em `str01-sem-null` e `str01-com-null`.

A saída não é regra nova — é **a mesma do core**: `0` cru = slot nulo, `\0` = o literal.

É a terceira vez que essa colisão aparece (weld do slot nulo, lab `2026-07-26-2126`, e aqui).
Vale registrar como invariante: **toda estrutura que grafa valores ao lado do slot nulo tem de
usar a grafia do core, não inventar a sua.**

## O que isto NÃO resolve

- **`k=1`**: o core já é ótimo. A escada deve recusar.
- **`n` pequeno**: abaixo de ~5 linhas não se paga.
- **valor longo**: o teto é `k × len(valor)`.
- **ordem**: o bitpack destrói a estrutura que OBAT/HCC explorariam.
- **gzip**: não medido. O estudo multi-col registrou que o gzip encolhe muito o ganho do bN.
- **relação com a decisão pendente do `STATUS.md`**: aquela é de escopo **multi-col `.8M`**;
  esta é o lado single-col. São irmãs, não a mesma.

## Se for soldar — onde encaixa (pelo guia)

| | |
|---|---|
| categoria | **A** (candidato do FLOOR) + **C** (gate de cardinalidade) |
| `[quando]` | **`[stream]`** — a decisão é conta, os insumos já existem |
| rota | 1 (`_lista_flat`) e 3 (`_tipo_single_col`) — hoje só a 3 alcança o denso |
| namespace | `b2`/`b4`/`b8` já estão **reservados** (fail-loud no decoder) |
| nunca-pior | sim, se entrar como candidato do `min()` |
| re-pina | os gates byte-canônicos que tiverem coluna de cardinalidade baixa |

**Nada soldado.** `src/tcf` intocado.

## Rodar

```
python run.py
```
`escada.py` tem a transformação, a fórmula do custo e o **leitor independente**.
