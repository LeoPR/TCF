# TCF — Tickets de Pesquisa e Implementacao

Indice de tickets ordenado por prioridade da fase atual.

**Localizacao**: `docs/workbench/tickets/` (movido de `tickets/` raiz na
reorganizacao 2026-04-27).

## Estrutura

```
tickets/
  README.md   Este arquivo — indice ordenado por prioridade
  open/       Tickets ativos
  frozen/     Tickets congelados (futuro trabalho condicional)
  closed/     Tickets concluidos + findings (com sub-pasta M-series/)
```

## Prefixos de tipo

- `NN-` — numero de ordem (legacy)
- `M-` — meta-ticket (orquestra sub-tickets)
- `T-` — task (implementacao concreta)
- `H-` — hypothesis (a comprovar/refutar)
- `E-` — experiment (teste com dados/modelos)
- `P-` — paper / pesquisa documental
- `R-` — review/refactor (audit ou rework)
- `B-` — bug (issue tecnica)
- `L-` — LLM-related (cenarios, prompts, eval com modelos)

---

## FASE ATUAL: Validacao experimental do design v0.4 (2026-05-05 →)

**Contexto**: design v0.4 fase 1 fechada. 18 decisoes consolidadas
(D1-D18), 3 propostas novas validadas em lab dirty (E, H, I), sigla
redefinida (TCF = Tabular Compact Format), nomenclatura nova
(`raw/compact/smart/extreme`).

**Bancada arquivada**: `experiments/lab/archive/2026-05-design-v04-fase1/`
(8 labs dirty da fase de design). Veja recap em
[docs/workbench/research-notes/2026-05-05-v04-design-recap.md](../research-notes/2026-05-05-v04-design-recap.md).

**Em curso**: validacao experimental controlada em
`experiments/lab/clean/EXP-003a-calibration/` (ja rodado) e
`experiments/lab/clean/EXP-003b-tcf-vs-gzip/` (ja rodado).

### Documentos durables da fase

- [recap consolidado](../research-notes/2026-05-05-v04-design-recap.md) — D1-D18, propostas, escalabilidade
- [hipoteses ativas](../research-notes/2026-05-05-hipoteses-ativas.md) — 10 pendentes
- [fluxo de experimentos](../research-notes/2026-05-05-fluxo-experimentos.md) — passos com criterio de pivot
- [nomenclatura](../research-notes/2026-05-05-nomenclatura-v04.md) — modos macro + siglas tecnicas
- [sigla TCF](../research-notes/2026-05-05-sigla-tcf.md) — Tabular Compact Format
- [stream vs standalone](../research-notes/2026-05-05-stream-vs-standalone.md) — pendencias HTTP real

### Open (foco atual)

**Foco**: validar HP-T1/T2/T3 + Propostas A/B/F antes de implementar
core. Auto-bypass agressivo eh principio central.

| Pri | Ticket | Tipo | Status |
|-----|--------|------|--------|
| 🔵 1 | [M-chunks-v04](open/M-chunks-v04.md) | meta | foco atual; D1-D18 consolidadas |
| 🔵 2 | [H-compression-v04-roadmap](open/H-compression-v04-roadmap.md) | hypothesis | E/H/I registradas com poréns |
| 🔵 3 | [M-architecture-v03](open/M-architecture-v03.md) | meta | split TCF nucleo + extras |
| 🔵 4 | [T-test-harness-mvp](open/T-test-harness-mvp.md) | task | meta-programa de validacao |
| 🔵 5 | [E-compression-combinations](open/E-compression-combinations.md) | experiment | precisa harness |
| 🔵 6 | [E-format-comparison-bench](open/E-format-comparison-bench.md) | experiment | EXP-003a/b parcialmente cobre |
| 🔵 7 | [E-min-max-scenarios](open/E-min-max-scenarios.md) | experiment | precisa harness |
| 🟠 8 | [R-tcf-core-revisit](open/R-tcf-core-revisit.md) | review | decisoes em M-chunks-v04 |
| 🟠 9 | [R-project-rename](open/R-project-rename.md) | review | sigla mantida (D17) — pode fechar |
| 🔴 10 | [P-paper-cap8-discussion](open/P-paper-cap8-discussion.md) | paper | bloqueia Cap 9 |
| 🔴 11 | [P-paper-cap9-conclusion](open/P-paper-cap9-conclusion.md) | paper | bloqueia submissao |
| 🟡 12 | [P-paper-appendices](open/P-paper-appendices.md) | paper | depende v0.4 spec final |
| 🟡 13 | [P-paper-figures](open/P-paper-figures.md) | paper | melhora paper |
| 🟢 14 | [P-phase-closure](open/P-phase-closure.md) | meta | fechamento de fases |

### Experimentos clean rodados

| EXP | Status | Achado |
|-----|--------|--------|
| EXP-003a calibration | rodado 2026-05-05 | gzip(CSV) ganha 70% medio; verify-stream confirma referencia |
| EXP-003a-extension (sort) | rodado 2026-05-08 | sort sozinho da -2.31% medio; nao substitui TCF |
| EXP-003b tcf-vs-gzip | rodado 2026-05-08 | smart vs compact apos gzip: -14% medio; 2 clusters claros |

### Open — issues tecnicas em standby

| Pri | Ticket | Tipo | Notas |
|-----|--------|------|-------|
| ⚪ — | [23-P-numeric-precision](open/23-P-numeric-precision.md) | research | Endereca em v0.3 ou WONTFIX |
| ⚪ — | [29-B-decoder-freetext-bug](open/29-B-decoder-freetext-bug.md) | bug | Nao afeta Linha A/B; v0.3 candidate |

### Open — categoria LLM (separada, parada por ora)

Decisao 2026-05-05: trabalho com LLMs e categoria **separada** do
foco atual (core compression v0.4). Tickets nesta secao ficam parados
ate decisao explicita de retomar.

| Pri | Ticket | Tipo | Notas |
|-----|--------|------|-------|
| ⚫ — | [M-llm-integration-future](open/M-llm-integration-future.md) | meta | Agrupa Phase 3/4/5, eval v0.4 com modelos, schema_qualifier |

Legenda:
- 🔵 foco atual (TCF nucleo + reorg arquitetural)
- 🔴 critico para entrega de paper
- 🟡 importante para entrega de paper
- 🟠 decisao de direcao (input do usuario)
- 🟢 backlog v0.3
- ⚪ backlog tecnico
- ⚫ categoria LLM (separada, parada — reativar com decisao explicita)

---

## Como rastrear este estado no futuro

Para revisar ou auditar este momento:

1. **Snapshot do indice**: este `README.md` no commit `<ts>` (data
   acima)
2. **Snapshot dos tickets**: `git log --follow docs/workbench/tickets/`
3. **Snapshot dos findings**: catalogo em `docs/findings/` (38
   findings F-Q1..F-Q38)
4. **Snapshot do paper**: capitulos em `docs/article/`
5. **Snapshot dos resultados**: manifests JSONL em
   `experiments/results/m_*/manifest.jsonl`

Cada ticket aberto inclui secao "Notas de revisao futura" com pointers
para reabrir o contexto.

---

## Tickets fechados — biblioteca de findings

[closed/README.md](closed/README.md) — 47+ tickets concluidos cobrindo
v0.1 (G-series), v0.2 (M-series), e milestones M-natural + M-schema-scope.

**Pasta especial**: [closed/M-series/](closed/M-series/) — 18 milestones
M01-M-Acomm/M-schema-scope cada um com finding(s) associado(s).

---

## Tickets congelados — futuro trabalho condicional

[frozen/README.md](frozen/README.md) — 34 tickets congelados em 2026-04
representando pesquisa valida mas prematura (TCF advanced encodings,
HTTP protocols, code-gen experiments, etc.).

**Principio**: nao apagar, so congelar. Reactivar com justificativa.

---

## Convencoes para novos tickets

Use o frontmatter padrao:

```yaml
---
title: <titulo claro>
type: paper | meta | task | hypothesis | experiment | review | bug
status: OPEN | PARTIAL | CLOSED | FROZEN
priority: CRITICAL | HIGH | MEDIUM | LOW
created: YYYY-MM-DD
origin: <fato/conversa que originou>
see_also:
  - <links relacionados>
---
```

E inclua secao **"Notas de revisao futura"** com pointers para
reabrir o contexto do ticket sem precisar reler tudo.
