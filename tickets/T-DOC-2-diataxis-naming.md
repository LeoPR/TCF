---
title: T-DOC-2 — Explicitar mapeamento docs/algorithms,theory → Diataxis (reference,explanation)
status: closed
resolution: adr-0012-created
priority: P3
created: 2026-05-22
updated: 2026-05-23
closed: 2026-05-23
blocked-by: []
related:
  - ../README.methodology.md
  - docs/adr/0005-discoverability-claude-md-root.md
  - docs/adr/0012-diataxis-naming-local.md
---

# T-DOC-2 — Explicitar mapeamento docs/algorithms,theory → Diataxis

## Contexto / motivacao

Auditoria 2026-05-22 apontou que `docs/algorithms/` e `docs/theory/`
funcionam de fato como `docs/reference/` e `docs/explanation/` (Diataxis)
mas o nome local diverge do padrao nomeado no doc-mae.

Metodologia autoriza explicitamente convencoes locais (logica FORTE/LOCAL,
§"Aprofundando Pilar 4"). Renomear seria custo alto (links, ADRs,
imports, git history). Mas a divergencia precisa estar **declarada** —
caso contrario novo contribuidor (humano ou IA) podera tentar criar
`docs/reference/` paralelo, gerando dual source.

## Plano

Opcao A — ADR explicito (recomendado): criar `docs/adr/0011-diataxis-naming-local.md`
documentando o mapeamento:

| Pasta neste projeto | Equivalente Diataxis |
|---|---|
| `docs/algorithms/` | reference |
| `docs/theory/` | explanation |
| `docs/how-to/` | how-to |
| (sem) | tutorials |

Justificar a preservacao do nome local (consolidacao + custo de
renomear + leitura ergonomica).

Opcao B — adicionar nota em `MAP.md` + `CLAUDE.md` apontando o mapeamento,
sem ADR formal. Mais barato, menos auditavel.

## Criterio de aceite

- [ ] ADR-0011 criado (Opcao A) **OU** nota declarativa em MAP.md + CLAUDE.md (Opcao B)
- [ ] Tabela de mapeamento clara
- [ ] Decisao sobre `docs/tutorials/` (criar quando primeiro tutorial existir, ou nunca)

## Riscos

- Sobre-formalizar uma nao-decisao. Mitigacao: 1 ADR curto, nao deliberar muito.

## Conexoes

- Metodologia §"Pilar 2 Diataxis" + §13.2 "Convencoes locais vencem nomes deste doc"
- ADR-0005 (estrutura discoverability)

## Updates datados

### 2026-05-23 — execucao + fechamento

Opcao A escolhida — ADR explicito criado em `docs/adr/0012-diataxis-naming-local.md`.

Tabela de mapeamento documentada:
| Pasta | Equivalente Diataxis |
|---|---|
| docs/algorithms/ | reference |
| docs/theory/ | explanation |
| docs/how-to/ | how-to |
| (sem) | tutorials |

Tutorials NAO criados agora (criterio: 1º tutorial real OR API v1.0+
estabilizada).

MAP.md atualizado com nota "mapeamento Diataxis local (ver ADR-0012)".

Resolution: adr-0012-created.
