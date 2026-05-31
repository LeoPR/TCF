---
title: Parser robustness (FIX) — bug `,` em literais
type: dirty-lab
status: planned
tags: [tcf, bug-fix, hcc, canonical, parser, robustness]
created: 2026-05-18
updated: 2026-05-18
hypothesis: H-FIX-01..03 (em roadmap)
related:
  - docs/adr/0007-comma-in-literals-bug.md
  - docs/how-to/fluxo-hipotese-producao.md
  - experiments/lab/clean/EXP-013-real-world-tpch/
---

# 2026-05-18 — Parser robustness do HCC canonical (FIX series)

**Estado**: planejado (aguardando aprovacao do plano)
**Macro pai**: [`../README.md`](../README.md)
**Origem**: EXP-013 TPC-H revelou bug 3 (literais com `,` corrompem).
ADR-0007 documenta plano em DRAFT.

## Pergunta principal

Qual e' o fix **integrado no algoritmo** (nao surface) para bug
`,` em literais, mantendo (OU re-baselineando justificadamente)
M9 byte-canonical?

## Fluxo aplicado

Seguindo `docs/how-to/fluxo-hipotese-producao.md`:

| Estagio | Status | Onde |
|---|---|---|
| 1. Observacao | concluida | diario 2026-05-18 |
| 2. Hipoteses registradas | em andamento | roadmap (H-FIX-01..03) |
| 3. Sub-experimentos dirty | a iniciar | este lab |
| 4. Prototype clean | pendente | EXP-014 (futuro) |
| 5. ADR | DRAFT | ADR-0007 |
| 6. Integracao src/tcf | pendente | apos ADR accepted |
| 7. Producao | pendente | apos validacao multi-camada |

## Sub-experimentos planejados

### 01-reproducao-minima

**Hipotese**: identificar EXATO conjunto de strings que reproduzem
bug `,`.

**Tarefas**:
- Construir suite de strings com `,` em varias posicoes
- Combinar com strings que geram quebras especificas em HCC
- Mapear: qual sequencia exata de pieces/refs causa o bug

**Output**: doc descrevendo casos minimos + caso patologico
extraido do TPC-H.

### 02-opcao-A-escape-virgula

**Hipotese H-FIX-01/02**: escapar `,` em `_escape_lit` (e
adicionar parsing de `\,` no decoder) corrige bug.

**Subhipoteses**:
- H-FIX-01: preserva M9 baseline (se D1-D9 nao tem `,` em lits)
- H-FIX-02: muda M9 baseline (re-baseline justificado)

**Tarefas**:
- Fork de canonical com mudanca minima
- Validar reproducao minima passa
- Medir M9 em D1-D9
- Medir EXP-013 (TPC-H) RT 8/8

### 03-opcao-B-separator-heuristico

**Hipotese H-FIX-03**: adicionar separator `*` antes de literal
ambiguo no encoder, sem mexer no decoder.

**Tarefas**:
- Fork de canonical (so encoder)
- Validar mesmas suites

### 04-decisao-e-welding

**Trigger**: 02 e 03 testados.

**Tarefas**:
- Comparar bytes, complexidade, robustez
- Atualizar ADR-0007 com decisao
- Recommendar opcao
- Aguardar aprovacao do user antes de aplicar em src/tcf

## Restricoes herdadas

- src/tcf intocado neste lab dirty (fork local)
- Multi-camada validation obrigatoria antes de mover pra canonical:
  - EXP-007, EXP-010, EXP-011, EXP-012, EXP-013
- Re-baseline M9 e' OPCAO mas requer aprovacao explicita

## Aceite (do lab)

- Bug `,` em literais reproduzido minimalmente (sub-exp 01)
- Pelo menos 2 opcoes testadas em dirty (sub-exps 02, 03)
- ADR-0007 atualizado com decisao
- Plano de welding documentado (sub-exp 04)

## See also

- [ADR-0007 (DRAFT)](../../../../docs/adr/0007-comma-in-literals-bug.md)
- [Fluxo hipotese-producao](../../../../docs/how-to/fluxo-hipotese-producao.md)
- [EXP-013 onde bug apareceu](../../../clean/EXP-013-real-world-tpch/)
- [ADR-0006 fixes anteriores canonical](../../../../docs/adr/0006-empty-string-decode-fix.md)
- [Roadmap hipoteses cross-lab](../notas/roadmap-hipoteses.md)
