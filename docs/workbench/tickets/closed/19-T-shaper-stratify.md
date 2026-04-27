---
title: Stratification strategy — amostragem por grupo
type: task
status: OPEN
priority: 18
parent: 12-M-dataset-shaper
---

# Stratification

`scripts/shaper/strategies/stratify.py`

Garante representatividade por coluna categorica.

## Modos

- `stratify_by="workclass"` → ao menos 1 row por valor distinto de workclass
- Combina com `volume`: se volume=100 e 8 grupos, ~12-13 rows por grupo
- Se um grupo tem menos rows que o quociente, retorna o que tem + aviso

## Logica

```python
def _apply(reader, tables, request, trace):
    if request.stratify_by is None:
        return tables  # passthrough

    col = request.stratify_by
    for name, rows in tables.items():
        if not rows or col not in rows[0]:
            continue
        # Group rows by col value
        groups = defaultdict(list)
        for row in rows:
            groups[row[col]].append(row)
        # Sample proportionally from each group
        ...
```

## Tarefas

- [ ] Implementar StratifyStrategy
- [ ] Registrar no pipeline (apos compressibility, antes de volume)
- [ ] Testes: Adult por workclass, por sex, por education
- [ ] Testes: grupo com 0 rows gera warning
- [ ] Testes: combina com volume (proportional sampling)
