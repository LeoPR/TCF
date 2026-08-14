# EXP-018 — relatório

**18 casos · 0 falhas · todos os pins verdes.** Suíte do repositório: **1252 passed**,
inalterada (o lab não toca `src/tcf`).

O spec venceu em **6 de 18** — mediana **1,79×**, máximo **2,80×**.

## Onde o spec ganha

| caso | ideia | base | wire | ganho |
|---|---|---:|---:|---:|
| `real-tpch-orderkey` | chave de pedido 1..12000 | 123 | **44** | **2,80×** |
| `sint-passo7` | passo 7, largura de 1 a 4 dígitos | 49 | **27** | 1,81× |
| `real-tpch-partkey` | chave de peça 1..2000 | 50 | **28** | 1,79× |
| `real-tpch-custkey` | chave de cliente 1..1500 | 49 | **28** | 1,75× |
| `sint-progressao-largura-varia` | 1..600 (a largura quebra o marcador em 3) | 37 | **26** | 1,42× |
| `sint-com-nulos` | nulos no meio da progressão | 241 | **232** | 1,04× |

## Onde o spec recusa — e o wire fica byte-idêntico ao de hoje

| caso | por que recusa |
|---|---|
| `sint-largura-ja-fixa` | largura uniforme: o pad é no-op, `dimensiona` nem oferece |
| `sint-cardinalidade-5` | k=5 — território do bN |
| `sint-aleatorio-largura-varia` | largura varia mas **não há progressão**: o pad paga e não ativa nada |
| `sint-negativos` | o `-` cai em `format_mismatch`, vira literal |
| `sint-quase-constante` | o RLE do núcleo resolve |
| `real-tpch-lineitem-orderkey` | chave **repetida** (k=744 em 3000, 3 passos distintos) |
| `real-tpch-linenumber` · `real-wine-quality` | k=7, largura 1 |
| `real-retail-quantity` | tem negativos (−24..600) |
| `real-ibge-municipio-id` | 7 dígitos uniformes, sem progressão |
| `real-tpch-availqty` | largura varia, sem progressão |
| `real-tpch-nationkey` | k=25 |

## Leitura

O spec ganha **só onde o gatilho dispara** — progressão com largura variável — e **recusa nos
outros 12**, incluindo **6 colunas reais** escolhidas justamente para isso.

A recusa é o FLOOR trabalhando: nos 12, o wire é **byte-idêntico** ao que o encoder emite
hoje. **Nunca-pior provado caso a caso**, não por argumento.

O caso `sint-com-nulos` merece nota: ganha pouco (1,04×), mas prova que o slot nulo — que é
do **tipo**, não da grafia — atravessa o spec sem perder a progressão.

## Um pin corrigido durante a rodada

`real-tpch-lineitem-orderkey`: eu esperava `spec` e veio `core`. A expectativa era minha. A
coluna é monótona, mas tem **três passos distintos** (`1,1,1,1,1,1,2,3…`) — repetição quebra
a progressão, o marcador aritmético não ativa, e o padding só custaria. **Monotonia não
basta**; o gatilho precisa de progressão limpa. Está documentado no `casos.py`, no caso.

## O que falta para o weld

Aprovação. Os pontos de encaixe estão **localizados**, não estimados:

| ponto | arquivo |
|---|---|
| encode | `encoder.py:539` (o spec depois do `render`) |
| FLOOR | `encoder.py:549-600` (um `candidatos.append`) |
| decode | `decoder.py:410-411` (o spec antes do `_cast_tipo`) |
| registry | `natures/__init__.py` (`wire_id="ipad"`) |

A diferença entre este protótipo e o destino é de **uma linha**: aqui o spec vai out-of-band
no decode porque `ipad` ainda não está no registry; soldado, o decode o resolveria sozinho.
