# Shaper — dataset sampler (ferramenta auxiliar)

> **Status (2026-05-17)**: ferramenta de suporte para experimentos
> com TCF. **NAO faz parte do TCF-CORE.** Pode virar projeto a parte
> no futuro.

## O que faz

Extrai subconjuntos controlados de um hub SQLite de datasets canonicos
(Adult Census, TPC-H, etc.) segundo dimensoes:

- `volume`: tamanho da amostra (linhas)
- `schema`: complexidade de schema (1-table, multi-table, etc.)
- `join`: nivel de join (none, single, multi)
- `order`: ordenacao (random, sorted, stratified)
- `stratify`: distribuicao de classes
- `compressibility`: nivel de redundancia controlada

Cada dimensao em `strategies/`.

## Uso

```python
from shaper import Shaper, ShapeRequest

req = ShapeRequest(
    dataset="adult-census",
    volume=100,
    order="random",
    seed=42,
)
result = Shaper().apply(req)

for name, rows in result.tables.items():
    print(f"{name}: {len(rows)} rows")
```

## Onde se encaixa no projeto

- **Datasets v0.5** (LLM benchmark Phase 1, Q01-Q38) usavam shaper
  para preparar amostras estratificadas.
- **Datasets do dirty lab v0.6** (D1-D9) sao manuais (CSV diretos);
  shaper nao e' usado.
- **Futuro**: se Phase 2 (LLM Phase 2) reusar a infraestrutura,
  shaper continua util. Se o projeto bifurcar, shaper provavelmente
  acompanha o ramo LLM.

## Componentes

```
scripts/shaper/
  __init__.py         API publica (Shaper, ShapeRequest, ShapeResult)
  pipeline.py         orquestrador
  request.py          dataclass ShapeRequest
  result.py           dataclass ShapeResult
  _stratify_metrics.py    helpers de metricas
  strategies/             estrategias por dimensao
    compressibility.py
    fk_preserving.py
    join.py
    ordering.py
    schema.py
    stratify.py
    volume.py
```

## Dependencias

Nenhuma dependencia em `tcf` (modulo). Independente.

## Pendencias

Nada urgente. Manter atualizado se o hub SQLite mudar (raro).
