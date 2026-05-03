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

---

## FASE ATUAL: Fechamento de Paper + Decisoes de Direcao (2026-04-27 →)

**Contexto**: M-Acomm + M-schema-scope concluidos (38 findings,
2256 records, $9.46 USD). Repositorio reorganizado. Proximo bloco
de trabalho: **finalizar paper + decidir rumo do core TCF**.

### Open (10 tickets) — ordenados por prioridade

**Foco atual** (decidido 2026-04-27): TCF como nucleo
compressor/descompressor. **v0.4 = compressao repensada** (RLE/DICT/STATS,
ordem, prioridades, transport-layer). Auxiliares como pacotes irmaos
(extras). v0.3 fica como possivel espaco para split arquitetural sem
quebra de formato.

| Pri | Ticket | Tipo | Resumo | Bloqueador? |
|-----|--------|------|--------|-------------|
| 🔵 1 | [M-architecture-v03](open/M-architecture-v03.md) | meta | Split TCF nucleo + extras (estilo SQLAlchemy) | orquestra |
| 🔵 2 | [H-compression-v04-roadmap](open/H-compression-v04-roadmap.md) | hypothesis | Roadmap compressao v0.4 (repensar RLE/DICT/STATS + ordering + transport) | foco do nucleo |
| 🟠 3 | [R-tcf-core-revisit](open/R-tcf-core-revisit.md) | review | Audit critico v0.3 vs v0.2 | input usuario |
| 🟠 4 | [R-project-rename](open/R-project-rename.md) | review | Avaliar nome do projeto | antes de publicar |
| 🔴 5 | [P-paper-cap8-discussion](open/P-paper-cap8-discussion.md) | paper | Escrever Cap 8 (Discussao) | bloqueia Cap 9 |
| 🔴 6 | [P-paper-cap9-conclusion](open/P-paper-cap9-conclusion.md) | paper | Escrever Cap 9 (Conclusao) | bloqueia submissao |
| 🟡 7 | [P-paper-appendices](open/P-paper-appendices.md) | paper | Apendices A/B/C | bloqueia submissao |
| 🟡 8 | [P-paper-figures](open/P-paper-figures.md) | paper | Gerar figuras F1-F8 | melhora paper |
| 🟢 9 | [H-advanced-compression-v03](open/H-advanced-compression-v03.md) | hypothesis | Delta/FOR/scale-int (subset de #2 acima) | superseded por #2 |
| 🟢 10 | [P-phase-closure](open/P-phase-closure.md) | meta | Fechamento de fases + pip publish | meta |

### Open — issues tecnicas em standby

| Pri | Ticket | Tipo | Notas |
|-----|--------|------|-------|
| ⚪ — | [23-P-numeric-precision](open/23-P-numeric-precision.md) | research | Endereca em v0.3 ou WONTFIX |
| ⚪ — | [29-B-decoder-freetext-bug](open/29-B-decoder-freetext-bug.md) | bug | Nao afeta Linha A/B; v0.3 candidate |

Legenda:
- 🔵 foco atual (TCF nucleo + reorg arquitetural)
- 🔴 critico para entrega de paper
- 🟡 importante para entrega de paper
- 🟠 decisao de direcao (input do usuario)
- 🟢 backlog v0.3
- ⚪ backlog tecnico

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
