---
title: Pipeline executor + Strategy protocol
type: task
status: OPEN
priority: 13
parent: 12-M-dataset-shaper
---

# Pipeline

Criar `scripts/shaper/pipeline.py` que executa strategies em ordem fixa:

```
1. schema_filter  2. join_resolver  3. compressibility
4. stratify       5. volume_sampler 6. orderer
```

Cada strategy implementa o Protocol:

```python
class Strategy(Protocol):
    def apply(self, reader, tables, request, trace) -> tables
```

Pipeline carrega strategies registradas, chama em sequencia,
coleta trace, retorna ShapeResult.

## Tarefas

- [ ] Criar `scripts/shaper/pipeline.py`
- [ ] Definir Strategy Protocol em `strategies/__init__.py`
- [ ] Pipeline vazio (sem strategies) retorna dataset completo
- [ ] Trace registra cada step executado
- [ ] Testes unitarios do pipeline vazio
