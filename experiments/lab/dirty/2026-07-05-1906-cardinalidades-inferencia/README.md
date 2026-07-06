# 2026-07-05 19:06 — Inferência de cardinalidade (1×1/1×N/N×1/N×N) [probatório]

**Peça 7** do grupo [estudo-tcf-hierárquico](../notas/estudo-tcf-hierarquico-mapa.md) ·
[T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md). Auto-contido: `cardlib.py`
(nem usa `tcf`). `python run.py` regenera. É **normalização de banco** (dependência funcional) aplicada ao TCF.

## A ideia (do owner)

TCF é nativamente **1×1** (colunas de mesmo tamanho, retangular). Pensando na entrada, uma coluna pode
estar numa relação **1×N**: se ficasse plana, o pai **repete** (viraria RLE `*N|pai`). Declarar 1×N no
header deixa o pai virar **"elemento" guardado 1×** + ligado à coluna N. E dá pra **deduzir** isso — até
de um CSV — pela repetição. É uma **camada declarativa** de cardinalidade, independente do encoding (como
OBAT/HCC são camadas).

## Dedução (teste por contagem de distintos = descoberta de FD)

`nA=|A|`, `nB=|B|`, `nAB=|pares (A,B)|`. FD `A→B` sse `nAB==nA`; `B→A` sse `nAB==nB`.

| exemplo (tabela plana) | \|A\| \|B\| \|AB\| | dedução | **mecânica TCF** |
|---|---|---|---|
| cpf–nome | 3 3 3 | **1:1** (ambas FDs) | **nativo** (retangular) |
| pessoa–telefone | 2 3 3 | **1:N** (pessoa repete → pai) | **hierarquia** (pai 1× + link) |
| produto–categoria | 4 2 4 | **N:1** (categoria repete → dict) | **@dict** (o TCF já faz) |
| pessoa–curso | 2 2 3 | **N:N** (nenhuma FD) | **tabela-ponte** (2 dicts + pares) |

## O mapa cardinalidade → mecânica (o que une as peças)

- **1:1** → TCF nativo. Nada a fatorar.
- **1:N** → **hierarquia** (peças 3/4/5): o pai vira elemento 1× + coluna-filho ligada. **É o dual do RLE**
  (peça 1): `*N|pai` (plano) ↔ `pai 1× + link` (normalizado). Declarar 1:N no header **escolhe** o lado.
- **N:1** → **@dict low-card**: valor 1× + índice por linha. **O TCF JÁ emite isso** — a cardinalidade N:1
  é a EXPLICAÇÃO do `@dict`. (`01-Nx1-...`: dict `[eletronico,alimento]` + índice `[0,0,1,1]`.)
- **N:N** → **tabela-ponte** (junction): dict(A) + dict(B) + lista de pares. Não vira hierarquia simples.

## Deduzir (CSV) vs Definir (JSON)

- **CSV plano** → **deduz** a cardinalidade (contagem/FD) → monta o header → normaliza. (o que `run.py` faz)
- **JSON** → a árvore **já define** a hierarquia (1:N explícito). Mesma camada de cardinalidade, origem
  diferente. Depois de ter essa lógica, "fica fácil construir um JSON por indução/dedução ou por definição".

## Aberto

- **FD aproximada / com ruído**: dados reais têm exceções (uma linha viola a FD) → precisa de tolerância
  (g3-error) pra decidir 1:N vs N:N. Não coberto aqui (fixtures limpas).
- **Múltiplas colunas** (chave composta A,B→C): só fiz pares. FD com chave composta é o passo seguinte.
- **Qual normalizar**: nem toda FD compensa (overhead do link/junction). Liga com a peça 1 (bytes).
- Prior-art (FD discovery: TANE/HyFD; normalização p/ compressão) — ver `result.md` (survey).

## Estado

- **É**: dedutor de cardinalidade dos dados + mapa pra mecânica TCF, **rodando** nos 4 casos.
- **Será**: FD aproximada + chave composta; ligar com bytes (peça 1) pra decidir QUANDO normalizar.

Convenções: [dirty-lab-convencoes](../notas/dirty-lab-convencoes.md).
