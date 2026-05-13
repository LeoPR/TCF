---
title: ShapeRequest dataclass + validacao
type: task
status: OPEN
priority: 12
parent: 12-M-dataset-shaper
---

# ShapeRequest

Criar `scripts/shaper/request.py` com o dataclass que define
todos os parametros do shaper.

```python
@dataclass
class ShapeRequest:
    dataset: str
    volume: int | float | None = None
    seed: int = 42
    schema: str | list[str] = "full"
    join_level: str = "normalized"  # "normalized" ou "flat"
    order: str = "natural"
    stratify_by: str | None = None
    compressibility_range: tuple[float, float] | None = None
```

Validacao: tipos, ranges (volume 0-1 se float, >0 se int),
schema valido para o dataset, etc.

Tambem criar `scripts/shaper/result.py`:

```python
@dataclass
class ShapeResult:
    tables: dict[str, list[dict]]
    metadata: dict
    request: ShapeRequest
    trace: list[str]
    stats: dict
```

## Tarefas

- [ ] Criar `scripts/shaper/__init__.py`
- [ ] Criar `scripts/shaper/request.py`
- [ ] Criar `scripts/shaper/result.py`
- [ ] Validacao de ShapeRequest (metodo `validate()`)
- [ ] Testes unitarios
