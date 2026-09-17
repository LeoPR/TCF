---
title: T-BN-LARGURA-VARIAVEL, a largura do índice bN arredonda para o inteiro
status: open
created: 2026-09-16
updated: 2026-09-16
target: ".9 (otimização)"
blocked-by: []
related:
  - docs/adr/0036-bn-de-dominio-cardinalidade-baixa.md
  - docs/reference/familia-bn-bits.md
  - experiments/lab/clean/EXP-016-bn-familia-bits/outputs/tabela-larguras.md
---

# T-BN-LARGURA-VARIAVEL

**[registro. Nada medido; nada em `src/tcf` sem aprovação.]**

## Por que este arquivo existe

O nome era citado sem arquivo desde 2026-07-27 (commit `35be493b`), numa tabela de pendentes do
`STATUS.md` removida em `3f9fbbe8`. As citações que não se editam são o
[ADR-0036](../docs/adr/0036-bn-de-dominio-cardinalidade-baixa.md) e a tabela de larguras do
EXP-016, gerada pelo `run.py` do lab. O inventário do bN de 2026-08-07 o pôs entre o que fica para
o `.9` (commit `44a7be47`). Este ticket registra só o que os documentos já dizem.

## O que é

A largura do índice é `w = ceil(log2(k))`, sem arredondar para potência de 2, com teto
`MAX_W = 8` (`src/tcf/composicional/dominio_bn.py:71-74`). A
[tabela de larguras](../experiments/lab/clean/EXP-016-bn-familia-bits/outputs/tabela-larguras.md)
é gerada desse código.

A perda está no arredondamento para o inteiro: `k=5` gasta 3 bits onde log2(5) ≈ 2,32. O ADR-0036
descreve o mesmo efeito como slots desperdiçados em `k` = 3, 5, 6 e 7, com `k` potência de 2 como o
caso sem desperdício.

A largura é uniforme na coluna, e larguras mistas não foram exploradas
([`familia-bn-bits.md`](../docs/reference/familia-bn-bits.md)).

## Vizinho no registry

O H-TYPE-07 do [registry](../experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md) discutiu
larguras exatas para o protótipo alinhado a byte e anotou, sem recomendar, o agrupamento de valores
à maneira do Parquet. A forma soldada já usa a largura inteira exata; este ticket trata da fração
abaixo dela.

## Critério de aceite

- [ ] o ganho possível medido, com round-trip, antes de qualquer proposta de grafia
