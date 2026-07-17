---
title: T-EXP-DATASETH-S0-S3 — corpus, oráculo, IR e álgebra de vínculos
status: closed
priority: P1
created: 2026-07-16
updated: 2026-07-16
blocked-by: []
related:
  - tickets/T-STUDY-DATASETH-COMPLETE-SEMANTICS.md
  - tickets/T-STUDY-HIERARCHY-LINK-ALGEBRA.md
  - experiments/lab/dirty/2026-07-16-1708-dataseth-s0-s3-semantica-vinculos/
---

# T-EXP-DATASETH-S0-S3 — executar S0–S3

**[dispositivo→exec]** Construir evidência regenerável para capacidade semântica e equivalência de
vínculos antes de simplificar a representação do `#TCF.8H`.

## Critérios de aceite

- [x] dirty lab em `inputs/`, `intermediates/` e `outputs/`, com extensões reais;
- [x] vinte raízes cobrindo escalares, vazios, union, ragged, Unicode, newline e estrutura sem folhas;
- [x] wire `.tcf` por caso e round-trip canônico byte-idêntico;
- [x] IR explícito de nós/arestas/lanes;
- [x] counts, offsets, parent-index e steps comparados sobre o mesmo IR;
- [x] contraprovas fail-loud e perda de pais vazios sem skip;
- [x] zero mudança/import de `src/tcf`.

## Resultado 2026-07-16

Fonte: [outputs/24-resultado.txt](../experiments/lab/dirty/2026-07-16-1708-dataseth-s0-s3-semantica-vinculos/outputs/24-resultado.txt).

- RT semântico: **20/20**;
- álgebra de vínculo: **20/20**;
- fail-loud: **8/8**;
- wires reais: **20**, 801 B totais apenas como observação; magic `#PROTO.DATASETH.S1`
  (wire de PESQUISA do oráculo S1, não `#TCF.8H` canônico — declarado no README do lab);
- round-trip do corpus: **byte-idêntico** ao canônico;
- `src/tcf`: intocado.

Fechado como execução sintética. Não escolhe wire final nem sustenta conclusão de bytes, desempenho
ou generalização ecológica.
