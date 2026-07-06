# Conclusão — inferência de cardinalidade [probatório]

Peça 7 do [grupo](../notas/estudo-tcf-hierarquico-mapa.md). Números: `artifacts/` (`python run.py`).

- **Deduz as 4 cardinalidades dos dados** (teste de contagem de distintos = descoberta de FD): 1:1
  (ambas FDs), 1:N (só B→A, pai repete), N:1 (só A→B, dict repete), N:N (nenhuma FD). Rodou nos 4 casos.
- **O mapa que UNE as peças do grupo**:
  - **1:1** → TCF nativo.
  - **1:N** → **hierarquia** (peças 3/4/5). É o **dual do RLE** (peça 1): `*N|pai` ↔ `pai 1× + link`.
    Declarar 1:N no header **escolhe** o lado — exatamente a ideia do owner ("o pai vira 'elemento'").
  - **N:1** → **@dict** low-card — que o **TCF já emite**. A cardinalidade N:1 é a **explicação** do @dict.
  - **N:N** → **tabela-ponte** (2 dicts + pares). O único que não vira hierarquia simples.
- **Camada declarativa**: a cardinalidade é uma linguagem independente do encoding (como OBAT/HCC). Vem
  **deduzida** (CSV, contagem/FD) ou **definida** (JSON, a árvore já força). Com isso, "construir um JSON
  por indução/dedução ou por definição" fica direto.

## Prior-art (survey — dependência funcional + normalização p/ compressão)

Workflow `cardinalidade-inferencia` (2 lentes + síntese). Confirma e afia:

- **O teste de contagem É o primitivo canônico** (partition-cardinality do **TANE**). `A→B sse d_AB==d_A`;
  invariante `max(d_A,d_B) ≤ d_AB ≤ d_A·d_B`. Par-a-par não pega **determinante composto** (`{A,B}→C`) —
  isso exige lattice/stripped-partitions: **TANE** (Huhtala 1999), **HyFD** (Papenbrock & Naumann 2016,
  SOTA híbrido), **Pyro** (FD aproximada), plataforma **Metanome** (survey Papenbrock VLDB 2015).
- **Refinamento 1 — chave ≠ agrupamento**: se `d_A==n` (A é **chave**/UCC), `A→B` vale **trivialmente**
  (unicidade), **sem** repetição → **zero ganho** de normalização. Distinguir "chave" (d=n) de "grupo
  coarse" (d≪n) ANTES de propor fatorar. (o meu 1:1 cpf-nome são duas chaves → @dict bijetivo, não hierarquia.)
- **Refinamento 2 — onde a normalização REDUZ bytes** (o que faltava na peça 1): **não** na multiplicidade
  (×N conservada, RLE↔fk duais), e sim na **LARGURA DO VALOR** — trocar um valor **largo repetido** (w
  bytes) por um **código estreito** (r bytes). É o ganho do `@dict` (N:1): `eletronico`×N → índice×N. Para
  1:N, hoistar um pai largo. **Multiplicidade conservada; largura do valor pode encolher.**
- **Refinamento 3 — RLE vs fk é escolha sobre ORDEM** (Order Dependency, teoria-irmã da FD): se a ordem
  das linhas é **livre**, ordenar pelo pai + RLE é **estritamente melhor** que fk (paga O(d) runs, não
  O(N) refs); se a ordem é **semântica**, realizar os runs custa um **side-channel de permutação** — o
  mesmo tradeoff dos repetition/definition levels do Dremel. Descobrir a FD é necessário, **não** suficiente.
- **Meia-dedução é DE GRAÇA no TCF**: `SideOutputs.column_features.n_unicas` já é o `d_i` por coluna; só o
  `d_AB` conjunto pede 1 passada extra. E **near-FD** (g3>0) pode virar `anomaly_flag` via SideOutputs
  (near-1:N com poucas violações = provável linha suja) — "só detecta, nunca arruma".
- **FD aproximada** (ruído): métrica canônica **g3-error** (Kivinen & Mannila 1995) = fração mínima de
  tuplas a remover pra FD passar exata; aceita se `g3 ≤ ε`. **Lossless só com g3==0** — não normalizar
  near-FD em silêncio.

## Aberto (próximos)

- **FD aproximada** (dados reais têm exceções → g3-error) pra decidir 1:N vs N:N com ruído.
- **Chave composta** (A,B→C): só fiz pares → precisa TANE/HyFD.
- **Order Dependency**: o ganho de RLE precisa do pai **agrupado** (reordenar); se a ordem é semântica,
  custa permutação. Descobrir a FD ≠ poder realizá-la de graça.
- **Semântica de NULL** (null==null vs ≠) muda d_A/d_B/d_AB → a classe. Fixar convenção.
- **N:N cross-table** = **Inclusion Dependency/FK** (SPIDER/BINDER) — território do schema_gadget, não FD single-table.
- **N:N** (tabela-ponte) é o análogo do **link posicional** (peça 9) — o caso que precisa de número.

**Recomendação**: esta camada de cardinalidade é o "material" que amarra o grupo — 1:N↔hierarquia,
N:1↔@dict, 1:N↔RLE. Próximo natural: FD aproximada (real-world) OU o link posicional/N:N (peça 8).
