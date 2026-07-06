# Conclusão — técnica de ligação pai/filho no cabeçalho [probatório]

Peça 3 do [grupo](../notas/estudo-tcf-hierarquico-mapa.md). Artefatos: `artifacts/` (`python run.py`).
Análise apoiada em survey de prior-art (workflow `linking-pai-filho-techniques`, 3 lentes).

## O que foi implementado (e decoda)

Hint `#TCF.8 N` (nested, irmão do flag `M`) + **adjacência lado-do-pai**: cada bloco `@bK <kind>` lista
seus campos; campo escalar = `nome:tipo`, campo filho = `nome>J`. Prova em **S4** (1 filho) e **S6**
(multi-filho + multi-nível: `geo` sob `endereco`, pai ≠ raiz) — **RT OK nos dois** (`04-decode-*`).

## Prior-art — as técnicas de expressar pai/filho (survey)

Convergência das 3 lentes: pra "**hint + apontamento pai/filho simples, blocos empilháveis**", a família
vencedora é a **lista de adjacência / parent-pointer**.

| técnica | veredito p/ o nosso caso |
|---|---|
| **Adjacency list (parent-pointer)** | **melhor casamento** — é literal "1 ponteiro de pai por bloco não-raiz". Multi-filho/nível triviais. (Lente 1 best-fit; = Protobuf back-pointer, Lente 2 best-fit) |
| **Edge-list centralizada** (`0.telefones*>1`) | a aresta **É** a tupla que o owner pediu (pai, campo, cardinalidade, filho); topologia num lugar só (Lente 3 best-fit) |
| Materialized path (`$.endereco.geo`) | seek excelente (o caminho localiza sozinho), mas cresce com a profundidade |
| Dremel repetition/definition levels | é a peça do **array-dentro-de-array / N raízes** (link posicional) — nosso caso ainda não precisa |
| Nested set / Closure table / Succinct trees | poderosos p/ consultas de subárvore/escala; overhead alto p/ 2 blocos — over-engineering aqui |

## O refinamento (parent-side vs child-side)

Implementei **lado-do-pai** (o pai lista os filhos: `endereco>1`). O prior-art favorece o **lado-do-filho**
(cada bloco aponta pro pai: `@1 0.telefones*`) por ser **append-only / empilhável** — adicionar um bloco
**não mexe** na linha de ninguém, casando com "buscados como dois TCF empilhados". São **duais** (mesma
árvore, direção oposta), ambos reconstroem. → a **compactação (peça 4)** deve usar o **lado-do-filho**.

**Proposta compacta (peça 4, a validar):**
```
#TCF.8 N                 ← hint
@0                       ← raiz (sem pai)
@1 0.endereco            ← bloco 1: pai=0, campo 'endereco' (objeto, card 1:1)
@2 1.geo                 ← bloco 2: pai=1, campo 'geo'
@3 0.telefones*          ← bloco 3: pai=0, campo 'telefones', '*' = array (1:N)
<blocos TCF empilhados, na ordem>
```
Cada aresta = `<pai>.<campo>[*]`. Tipos das colunas ficam no meta de cada bloco TCF (já existe). Um bloco
não-raiz = 1 linha de ~poucos bytes.

**A compactação (peça 4) NÃO é trocar de modelo** (o survey é enfático): adjacency já é o começo *mais
simples E mais compacto*, e é isomorfo à filosofia atual (flag `M` + meta inline). A "compactação" é só:
(i) mover `campo+cardinalidade` pra **inline** de cada bloco (a aresta viaja junto do bloco → autocontido,
append-only); (ii) somar uma **tabela de OFFSETS** no topo — a única coisa que a adjacência não dá de
graça — para **seek O(1)** aos bytes do bloco K. Camadas tipo subárvore/path só entram se surgir a necessidade.

## Escopo / limite (peça 5 = futuro)

Cobre **raiz única + contenção 1:1 (objetos) + arrays-folha** — onde "quem é pai/filho" **basta** (sem
número). **Array-dentro-de-array** e **N raízes** precisam de **link POSICIONAL** (repetition level do
Dremel) — não é esta peça. `linklib` levanta `NotImplementedError` nesses casos (honesto).

## Open questions (pro redesenho do owner)

Campo com caractere especial (`.`/`>`/espaço) no nome → escape. Ordem das chaves (aqui preservada pela
lista de campos). `null` vs ausente. Leaf multi-col hoje é TCF.7 (peça 6). Bloco só-estrutura (sem escalar).
Onde por os offsets p/ **seek** O(1) (um TOC no topo, estilo HDF5) sem perder a empilhabilidade.
