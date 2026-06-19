---
title: META-STRATA-GOVERNANCE — atividades recorrentes de governança do método Strata
status: open
priority: P3
created: 2026-06-18
updated: 2026-06-18
blocked-by: []
related:
  - tickets/T-CLEAN-2-strata-defrag.md
  - C:/Users/leona/OneDrive/Documents/Projects/Acadêmicos/Methodologies/recipe/knowledge-architecture.md
  - C:/Users/leona/.claude/projects/c--Users-leona-OneDrive-Documents-Projects-Acad-micos-TCF/memory/reference_strata_knowledge_architecture_review.md
  - C:/Users/leona/.claude/projects/c--Users-leona-OneDrive-Documents-Projects-Acad-micos-TCF/memory/feedback_strata_l0_check_before_big_changes.md
---

# META-STRATA-GOVERNANCE — governança do método Strata (TCF)

**[dispositivo]** Agrupa as atividades **recorrentes / de cadência** do método Strata que valem
atenção mas não são defrag de superfície (essa vive em [T-CLEAN-2](T-CLEAN-2-strata-defrag.md)).
Registrado a pedido do owner (2026-06-18) "pra não esquecer". Proporcional ao §9: é um lembrete
de cadência, **não** um aparato formal de aderência (isso seria excesso — ver NÃO-FAZER).

## Sub-tarefas

- [ ] **G-1 [§7 maturação] — itens presos entre níveis.** *(decisão do owner num ponto)*
  - **Pacote 1** (`project_pacote1_delta_aware_summary`): "confirmada-empirica" nunca welded,
    hipóteses decorrentes (H-DA-09c/d/e, H-DA-10b) não recorreram. `[VERIFICAR: 2026-08-18]` (data
    **ainda não venceu**). Na data: manter aguardando, fechar `CLOSED-INSUFFICIENT-RECURRENCE`, ou
    promover. **Detalhe/execução em [T-CLEAN-2](T-CLEAN-2-strata-defrag.md) DB-2.**
  - Reconciliar status no `roadmap-hipoteses.md`: lazy-query → `confirmada-conceitual` (PoC+27
    testes); h-perf-06 → apontar ADR-0020; V2-D → tombstone. **T-CLEAN-2 DB-7.**

- [ ] **G-2 [§3-bis] — pass de rótulo "força do artefato".** Marcar ADRs / tickets / resultados de
  forma consistente como **dispositivo** (constitui: ADR accepted, código, decisão) vs **probatório**
  (registra fato alhures: resultado, métrica). Hoje é parcial. Pass leve, baixo risco; melhora a
  leitura por humano e agente (não ler diretiva e registro no mesmo plano).

- [ ] **G-3 [§ L2 / Parte III] — re-verificação da camada de ferramentas (`re-verify-by: 2026-09-01`).**
  A Parte III do Strata é semi-viva. Reconferir perto da data: CLAUDE.md no papel de AGENTS.md;
  camadas de memória (a 4ª, filesystem, gera drift opaco — auditar); convenções MCP. Se um item
  virar falso, corrigir **só** na camada L2 (L0/L1 não mudam).

- [ ] **G-4 [protocolo] — revisão periódica completa de aderência (cada ~60-90 dias).** A auditoria
  de 2026-06-18 cobriu o eixo **defrag** (→ T-CLEAN-2). No próximo ciclo, rodar a **matriz completa
  §1-§10** (estado 0-4 por princípio) como saúde geral. Protocolo em
  `reference_strata_knowledge_architecture_review.md` (memória). Próxima janela: ~2026-08 a 2026-09
  (alinhar com G-3).

## Gatilho event-driven (sempre ativo, fora do checklist)

Antes de **mudança grande** (format change / weld em `src/tcf` / ADR accepted / weldar hipótese /
reorg grande / release), reconferir aderência ao núcleo L0 — diretiva do owner registrada em
`feedback_strata_l0_check_before_big_changes.md` (memória). Não é uma sub-tarefa a fechar; é uma
regra permanente.

## NÃO-FAZER (§9 — gênero: biblioteca + compêndio pré-1.0 solo)

Não criar `docs/strata-aderencia.md` formal, lint-bot de referências, registries auto-gerados, nem
AGENTS.md por gadget. A aderência é **proporcional**, verificada em ciclos leves — não um aparato.

## Critérios de aceite

Ticket de cadência (não "fecha" cedo): cada G-* é executado/decidido na sua janela. G-1 depende de
decisão do owner em 2026-08-18; G-3/G-4 na janela ago-set/2026. Manter `open` como lembrete vivo.
