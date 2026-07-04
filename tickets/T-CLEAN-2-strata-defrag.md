---
title: T-CLEAN-2-strata-defrag — Defragmentação da biblioteca (higiene de superfície §3/§5 + índices §2)
status: closed-backlog-done-db2-owner-pending
priority: P2
created: 2026-06-18
updated: 2026-07-01
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

**EXECUTADOS 2026-06-18** (verificados na fonte; NÃO tocaram `src/tcf`; nenhum traço apagado).

- [x] **QW-1 [§3/§5]** `CLAUDE.md` L10 **"v0.6" → "v0.7"**; L299 exemplo de magic → "atual: v0.7 =
      #TCF.7; v0.6 = #TCF.6 legado". (L59/61/62 mantidas — referências **históricas** legítimas.)
- [x] **QW-2 [§5]** `README.md` L259: "425 passed" (stale) → **"379 passed, 1 xfailed" (config CI
      `not requires_data`)** + ponteiro "rode `pytest`" + `[VERIFICAR: 2026-06-18]`. Número real medido
      (`pytest`: 379 passed / 60 deselected / 1 xfailed). (L281 já apontava "pinado em testes" → não mexido.)
- [x] **QW-3 [§2/§3]** memória `project_pacote1_delta_aware_summary.md` L68: `[[links]]` quebrados →
      reapontados para `[[reference-hcc-provas-m5-m8]]` + **tombstone** com path
      `_archived_consolidated_2026_06_12/{project_macro_M8_virtual_refs,project_macro_M9_stress}.md`.
- [x] **QW-4 [§5/§3]** memória `MEMORY.md` seção "estado canônico" reescrita: aponta `STATUS.md`/
      `ROADMAP.md` (estado vivo), reframe como núcleo histórico, números removidos (vivem nos testes).
      MEMORY.md **208 → 195 linhas** (sob o limite ~200).
- [x] **QW-5 [§3]** `STATUS.md` L76 "Atualizado em: 2026-06-08" → "Snapshot 2026-06-08 … atualizações
      posteriores nos blocos SESSAO acima (até 2026-06-17)" (resolve a deriva: stamp < conteúdo).

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

## Backlog EXECUTADO 2026-07-01 (DB-1,3,4,5,6,7 feitos; DB-2 = owner)

- [x] **DB-1** `docs/theory/roadmap-hipoteses.md`: zero links de entrada → **nota de cabeçalho** apontando
      pro registry ativo (`experiments/lab/dirty/notas/roadmap-hipoteses.md`). Não deletado (traço).
- [x] **DB-2** **RESOLVIDO ANTECIPADAMENTE (2026-07-04)**: a memória estava stale — as 3 perguntas
      do `[VERIFICAR: 2026-08-18]` já tinham resposta no repo (welding = ADR-0011 welded canonical;
      real-world = 11.73% weighted testado; decorrentes = H-DA-09c/d/e fechadas + H-DA-10b→H-DA-11
      welded ADR-0010). Memória atualizada com a resolução; corpo original preservado como traço.
- [x] **DB-3** tombstones nos 2 `_archived_consolidated_*` (memória user-scope): `TOMBSTONE.md` em cada
      (o quê/quando/porquê/autoridade).
- [x] **DB-4** `MAP.md` refresh: + `docs/reference/bibliografia.md`, `arquitetura-share-header-lazy.md`,
      labs 2026-06-27/07-01; `multi.py`→`multi/`; ponteiro registry-ativo vs homônimo histórico.
- [x] **DB-5** `docs/workbench/_archive/tickets/README.md`: **tombstone no topo** (snapshot histórico v0.4;
      "open/" NÃO são vivos; vivos em `/tickets/`). Resolve a contradição §1 sem mover/deletar.
- [x] **DB-6** ADR-0017: **NOTA** "v1.0 frozen → pré-1.0 (superseded ADR-0024/0028)" + tag `magic-number`.
- [x] **DB-7** `notas/roadmap-hipoteses.md`: H-PERF-06 (aberta→REFRAMED→welded ADR-0019/0020) + H-QUERY-01
      lazy (gadget→PROMOVIDO ao core `src/tcf/view.py`). V2-D já estava descrito como refutado.

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
