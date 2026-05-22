# Tickets — TCF v0.6

Tickets de planejamento + acompanhamento do projeto. Cada ticket tem
status (`open` / `in-progress` / `closed`), criterios de aceite, e
referencias a commits que o resolveram.

## Convencao de IDs

- `META-X` — meta-tickets que agrupam decisoes/sub-tarefas
- `T-NAME-N` — naming (terminologia + identidade)
- `T-DOC-N` — documentacao
- `T-EXP-N` — experimentos (clean lab)
- `T-CODE-N` — codigo (src/)
- `T-CLEAN-N` — limpeza/reorganizacao

## Tickets

| ID | Tema | Status |
|---|---|---|
| [META-NAMING](META-NAMING.md) | Naming oficial (TCF/OBAT/HCC) | **CLOSED 2026-05-17** |
| [META-DOCS-V05-OBSOLETE](META-DOCS-V05-OBSOLETE.md) | Fase 2: archivar v0.5-exclusivo em docs/ | **CLOSED 2026-05-17** |
| [META-THEORY-MOVE](META-THEORY-MOVE.md) | Mover hipoteses/teoria dirty → docs/theory/ + sintese das 3 estrategias | **CLOSED 2026-05-17** |
| [META-EXP-FORMAT](META-EXP-FORMAT.md) | Template validacao vs comparativo + reorganizar EXP-008 | **CLOSED 2026-05-15** |
| [META-TYPE-ENCODERS](META-TYPE-ENCODERS.md) | Grande plano: pre-tx por natureza + estudos camada algoritmo (T01 absorvido em Pacote 1; T02-T07 + L01-L05 adiados) | **OPEN 2026-05-15** (atualizado 2026-05-19) |
| [META-PERF-PHASE2](META-PERF-PHASE2.md) | Pacote 4 fase 2: lineitem full 60175 (executado, 21min real); H-PERF-04/05/06 todos adiados com justificativa documentada | **CLOSED-PARCIAL 2026-05-20** |
| [META-ESCAPE-DEDUCTION](META-ESCAPE-DEDUCTION.md) | Pacote 2: H-ED-01..04 caracterizacao mediu 0.13%-1.13% real-world (lower bound), critério aceite 5%. Primeiro ticket YAML frontmatter validou metodologia. | **CLOSED-INSUFFICIENT-GAIN 2026-05-21** |
| [T-REVAL-H-DA-01-06-10](T-REVAL-H-DA-01-06-10.md) | Revalidacao Categoria B (revisao 2026-05-21): H-DA-06 SUBSUMIDA, H-DA-01 marginal (1.36%), H-DA-10 CONFIRMADA inesperadamente (9.92% real-world). Nova H-DA-11 decorrente. | **CLOSED-COMPLETED-WITH-SURPRISES 2026-05-21** |
| [T-EXP-H-DA-11](T-EXP-H-DA-11.md) | Auto-detect min_len por coluna: heuristica v3 captura 9.87% real-world em src/tcf canonical welded (ADR-0010). M9 baseline 1615B preservado EXATO, RT 100% (9/9 + 57/57). | **CLOSED-CANONICAL-WELDED 2026-05-22** |
| [T-CODE-H-DA-11c](T-CODE-H-DA-11c-features-unificadas.md) | ColumnFeatures unificado: novo `src/tcf/column_features.py` + refactor `auto_min_len.py` + `encoder.py`. Output IDENTICO ao pre-refactor (zero-risk). Prepara terreno pra T02-T07 e weld futuro de detect_cadence canonical. | **CLOSED-REFACTOR-COMPLETED 2026-05-22** |
| [T-DOC-1-citation-cff](T-DOC-1-citation-cff.md) | Adicionar CITATION.cff + preparar DOI (Zenodo). Gap de aderencia §3.5 metodologia. | **OPEN 2026-05-22** |
| [T-DOC-2-diataxis-naming](T-DOC-2-diataxis-naming.md) | Explicitar mapeamento docs/algorithms,theory → reference,explanation (ADR ou nota em MAP.md). | **OPEN 2026-05-22** |
| [T-CLEAN-1-pre-commit-hooks](T-CLEAN-1-pre-commit-hooks.md) | Adicionar pre-commit (detect-secrets, ruff, basicos). Gap de aderencia §"Versionamento e higiene". | **OPEN 2026-05-22** |

## Politica

- Cada ticket "closed" referencia commit(s) que o resolveram.
- Antes de deletar/mover arquivos: garantir push ao GitHub.
- Recuperabilidade via `git log` / `git show`.

## Convencao pra tickets novos (recomendacao 2026-05-21)

Tickets futuros devem usar YAML frontmatter pra serem indexaveis
por `scripts/index.py` e parseaveis por IA. Existentes (fechados)
ficam como estao — imutabilidade.

```yaml
---
title: T-EXP-N — Tema curto
status: open | in-progress | blocked | deferred | absorbed | closed | superseded
priority: P0 | P1 | P2 | P3        # opcional
created: YYYY-MM-DD
updated: YYYY-MM-DD
blocked-by: [TICKET-XYZ]            # opcional, grafo de dependencia
related:
  - docs/adr/0000-...md
  - experiments/lab/clean/EXP-NNN-...
---
```

Conteudo do ticket cubra estes movimentos (nomes livres):
contexto / motivacao → hipotese ou pergunta → plano → criterio de
aceite (KR-style mensuravel: "X% reducao", "RT 100%") → riscos →
conexoes → **updates datados inline** (lab notebook tradition;
preferivel a comments thread porque versiona em git).

Referencia da metodologia subjacente: [`../../README.methodology.md`](../../README.methodology.md) §3.8.
