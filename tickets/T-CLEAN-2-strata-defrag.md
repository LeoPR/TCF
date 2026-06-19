---
title: T-CLEAN-2-strata-defrag — Defragmentação da biblioteca (higiene de superfície §3/§5 + índices §2)
status: open
priority: P2
created: 2026-06-18
updated: 2026-06-18
blocked-by: []
related:
  - experiments/lab/dirty/notas/hquery01-decode-dag-indices-design.md
  - docs/adr/0024-pre-1.0-versioning-git-as-compat.md
  - C:/Users/leona/OneDrive/Documents/Projects/Acadêmicos/Methodologies/recipe/knowledge-architecture.md
---

# T-CLEAN-2-strata-defrag — Defragmentação da biblioteca de conhecimento

**[probatório]** Registra os achados de uma auditoria de aderência ao método **Strata**
(read-only, 2026-06-18) e **[dispositivo]** propõe o plano de higiene decorrente. Nada foi
executado ao abrir este ticket. Fonte: auditoria via workflow `strata-defrag-audit` (5 lentes +
síntese). Verificação de guardião (§6) aplicada a cada item antes de listar.

## Diagnóstico (sóbrio)

Aderência Strata **boa** para projeto pré-1.0: separação física limpa (§1), git são + baselines
pinados (§8), traço respeitado. Problema dominante = **deriva de superfície** (§3, leitura aponta
para estado antigo) e **número-fonte copiado na prosa** (§5, apodrece em silêncio). Defrag **barata e
localizada** — sem reorganização estrutural.

## Quick wins (S, baixo risco — executar como uma passada de higiene)

Cada um verificado na fonte. NÃO toca `src/tcf` (algoritmo). Superfície decai **com tombstone**;
traço nunca se apaga (§3).

- [ ] **QW-1 [§3/§5]** `CLAUDE.md` L10 rótulo de versão **"v0.6" → "v0.7"** (real: 0.7.1 / #TCF.7).
      Na mesma passada, revisar L299 (`(v0.6 = #TCF.6)` → exemplo pode citar #TCF.7). L59/61/62 são
      referências **históricas** (labs criados na era v0.6) — avaliar, provavelmente manter.
- [ ] **QW-2 [§5]** `README.md` L259 **"425 passed, 1 xfailed"** está stale/ambíguo (real: **380**
      na config CI `not requires_data` / **440** total). Trocar por **ponteiro** ("rode `pytest`")
      ou número real **+ `[VERIFICAR: 2026-06-18]`**. (L281 já diz "pinado em testes" → **OK**, não mexer.)
- [ ] **QW-3 [§2/§3]** memória `project_pacote1_delta_aware_summary.md` L68: `[[links]]` quebrados
      (`project-macro-M8-virtual-refs`, `project-macro-M9-stress` foram consolidados/arquivados).
      Reapontar para `[[reference-hcc-provas-m5-m8]]` (ativo) + tombstone com o path em
      `_archived_consolidated_2026_06_12/`. Também atualizar "TCF v0.6" → contexto correto.
- [ ] **QW-4 [§5/§3]** memória `MEMORY.md` seção "estado canônico" (≈ L15-51): refletir
      **#TCF.7 / 0.7.1** (hoje fala #TCF.6, M1.E, M9-M14, "# v0.6"). **Apontar para STATUS.md**, não
      copiar números. MEMORY.md está em **208 linhas** (limite ~200) — esta passada deve enxugar.
- [ ] **QW-5 [§3]** `STATUS.md`: verificar e atualizar datas de "última atualização" defasadas
      (auditoria apontou ≈ L76 com data anterior ao conteúdo). **A confirmar na execução** (não verificado neste turno).

## Backlog deferido (M, decisão/gate — executar depois, alguns exigem owner)

- [ ] **DB-1 [§5/§3]** `docs/theory/roadmap-hipoteses.md` é doc **antigo** (2026-05-17, "hipóteses
      faltantes") com o **mesmo nome** do registry ativo em `experiments/lab/dirty/notas/`. **NÃO é
      cópia verbatim** → **não deletar**. Ação: `grep` por links de entrada → **superseder com nota
      de cabeçalho** apontando pro registry ativo, ou mover pra archive com tombstone.
- [ ] **DB-2 [§7] (owner decide)** Pacote 1 (`project_pacote1_delta_aware_summary.md`):
      "confirmada-empirica" com `[VERIFICAR: 2026-08-18]`. **Correção da auditoria**: a data **NÃO
      venceu** (hoje 2026-06-18 < 2026-08-18) — não está atrasado. Mas nunca foi welded em `src/tcf`
      e as hipóteses decorrentes (H-DA-09c/d/e, H-DA-10b) não recorreram (regra de 3). Decisão do
      owner na data: manter aguardando, fechar `CLOSED-INSUFFICIENT-RECURRENCE`, ou promover.
- [ ] **DB-3 [§3]** `_archived_consolidated_2026_05_16/` e `_2026_06_12/`: adicionar **tombstone**
      (o quê/quando/porquê/sob que autoridade) — a consolidação ficou pela metade sem a lápide.
- [ ] **DB-4 [§2]** `MAP.md` refresh: adicionar pontos de entrada novos (`docs/reference/` novo,
      `ROADMAP.md`, design notes recentes, labs 2026-06); marcar superseded onde aplicável.
- [ ] **DB-5 [§1/§2]** `docs/workbench/_archive/tickets/open/` tem tickets **"open" dentro de um
      archive** (contradição §1). Consolidar vivos sob `tickets/`; archive só `closed`/`frozen`.
- [ ] **DB-6 [§3-bis]** ADRs por **NOTA** (corpo imutável, não editar): ADR-0017 relabel
      "v1.0 frozen" → pré-1.0 (ADR-0024 supersede). *(ADR-0027 já tem a nota "owner escolheu (A)".)*
- [ ] **DB-7 [§7]** `roadmap-hipoteses.md` (notas): reconciliar status — h-perf-06 welded → apontar
      ADR-0020; lazy → `confirmada-conceitual`; V2-D → tombstone (refutado).

## NÃO fazer (§9 — excesso / risco §3) — guardrails do guardião

- NÃO criar `docs/strata-aderencia.md` formal, lint-bot/CI ref-checker, nem registry de baselines
  auto-gerado (gênero errado; INDEX.md já existe).
- NÃO converter `roadmap-hipoteses.md` de tabela → seções (arrisca §3/§7).
- NÃO consolidar Pacotes 7/10 (N=1 — regra de 3).
- NÃO deletar checkpoints/diários/`_archived_*` — é **traço** (§3): silenciar com tombstone, não apagar.
- NÃO editar corpo decisório de ADR imutável — usar NOTA (§3-bis).
- **NÃO "corrigir" os "D17a 322B" nos tickets FECHADOS / no índice** — é **traço** (era verdade
  antes do re-pin pra 303B via ADR-0025). Mexer reescreveria a história (§3).

## Critérios de aceite

- Quick wins QW-1..QW-5 aplicados; nenhuma deleção de traço; cada disposição com tombstone.
- Backlog DB-* triado (cada um: feito / agendado / fechado com tombstone); DB-2 decidido pelo owner.
- `src/tcf` intocado; baselines (D1-D9=1523, D17a=303) inalterados.
- README/CLAUDE/MAP/STATUS sem número-fonte copiado sem ponteiro ou `[VERIFICAR]`.

## Proveniência

Auditoria Strata 2026-06-18 (workflow `strata-defrag-audit`, read-only). Princípios L0 citados da
fonte canônica (`Methodologies/recipe/knowledge-architecture.md`, Strata v1.1.0).
