---
title: T-STUDY-HIERARCHY-LINK-ALGEBRA — equivalência dos portadores de vínculo
status: in-progress
priority: P1
created: 2026-07-16
updated: 2026-07-16
blocked-by: []
related:
  - tickets/T-STUDY-HIERARCHICAL-TCF.md
  - tickets/T-EXP-DATASETH-S0-S3.md
  - experiments/lab/dirty/2026-07-16-1708-dataseth-s0-s3-semantica-vinculos/
  - experiments/lab/dirty/2026-07-13-2356-rle-dual-multiplicidade-deduzida/
  - experiments/lab/dirty/2026-07-14-2043-l3-multiplicidade-independencia/
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
---

# T-STUDY-HIERARCHY-LINK-ALGEBRA — equivalência dos portadores de vínculo

**[dispositivo→pesquisa]** Este ticket trata o header, a busca no corpo e a estruturação dos dados
como planos físicos sobre um IR único, sem escolher cedo uma gramática canônica.

## Hipóteses

**H-HIER-LINK-ALGEBRA-01**: dado um domínio ordenado e explícito de pais e um payload ordenado de
arestas, os portadores abaixo preservam o mesmo vínculo e são conversíveis:

$$
counts \leftrightarrow offsets \leftrightarrow parent\_index \leftrightarrow steps
$$

**H-HIER-BOUNDARY-EMPTY-01**: um bit `first-child` sem skip/step ou bitmap de vazios é insuficiente;
pais vazios intermediários tornam duas topologias distintas indistinguíveis.

## Plano

- [x] **S2** — IR de nós, arestas ordenadas e lanes de valores.
- [x] **S3** — conversores e asserts das quatro representações.
- [ ] **S4** — wires físicos lado a lado: counts, offsets, parent-id, rep/def-level, tabelão/RLE e eventos.
- [ ] **S5** — DAG de decode, busca, lazy, sincronização, paralelismo e memória.
- [ ] **S6** — comparar árvore inline, registry de shapes e diretório de blocos no header.
- [ ] **S7** — recomendar default/fallback por perfil e só então propor weld.

## Falsificadores

- pais vazios no começo, meio e fim;
- vários arrays irmãos e arrays recursivos;
- arrays mistos e objetos ragged;
- estrutura sem folha de dados;
- reordenação de bloco que altere ordinal ou associação pai-filho;
- representação que exija materializar coluna de dado para ler somente estrutura.

## Update 2026-07-16

Lab [S0–S3](../experiments/lab/dirty/2026-07-16-1708-dataseth-s0-s3-semantica-vinculos/):
**20/20** IRs reconstruíram o mesmo vetor de pai via counts, offsets e steps. A contraprova fixou
`[0,2,2]` versus `[0,1,1]`: ambas produzem bits `[start,start,continue]`, logo a forma sem skip perde o
pai vazio. `H-HIER-LINK-ALGEBRA-01`: confirmada-conceitual no modelo; `H-HIER-BOUNDARY-EMPTY-01`:
confirmada-conceitual por contraprova construtiva. Confiança Média; faltam wires e custos de S4–S6.
