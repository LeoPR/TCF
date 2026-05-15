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
| [META-TYPE-ENCODERS](META-TYPE-ENCODERS.md) | Grande plano: pre-tx por natureza + estudos camada algoritmo (2 tracks, 4 ondas, multi-semana) | **OPEN 2026-05-15** |

## Politica

- Cada ticket "closed" referencia commit(s) que o resolveram.
- Antes de deletar/mover arquivos: garantir push ao GitHub.
- Recuperabilidade via `git log` / `git show`.
