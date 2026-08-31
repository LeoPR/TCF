---
title: Ordering strategy (natural, random, sorted, reverse)
type: task
status: OPEN
priority: 16
parent: 12-M-dataset-shaper
---

# Ordering

`scripts/shaper/strategies/ordering.py`

- `natural` → ordem do SQLite (insertion order)
- `random` → shuffle com `request.seed`
- `sorted:col_name` → ORDER BY col ASC
- `reverse:col_name` → ORDER BY col DESC

Importante: esta e a **ordem de apresentacao** ao consumidor.
A **ordem interna de compressao** (que o TCF faria) e outra coisa
e nao e responsabilidade do shaper.

## Tarefas

- [ ] Implementar OrderingStrategy
- [ ] Registrar no pipeline (ultimo step)
- [ ] Testes: natural preserva ordem, random+seed reproducivel,
  sorted funciona, reverse funciona
