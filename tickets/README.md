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

## Tickets ativos

| ID | Tema | Status |
|---|---|---|
| [META-NAMING](META-NAMING.md) | Naming oficial (projeto, alg16, M8.A) | open — aguardando decisao |

## Politica

- Cada ticket "closed" referencia commit(s) que o resolveram.
- Antes de deletar/mover arquivos: garantir push ao GitHub.
- Recuperabilidade via `git log` / `git show`.
