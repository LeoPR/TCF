# Shaper — dataset sampler (ferramenta auxiliar)

> **Status (2026-05-31)**: ferramenta de suporte para experimentos
> com TCF. **NAO faz parte do TCF-CORE.** Pode virar projeto a parte
> no futuro. **Aprovado cientificamente para uso** — ver "Validacao
> cientifica" abaixo (T-SHAPER-SCIENTIFIC-GATING).

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

## Validacao cientifica (aprovacao de uso)

Principio do owner: um tool cientifico nao pode ser usado em experimentos
TCF so' porque "corta dados" — precisa **confirmacao estatistica** de que
preserva o que claima. Gate em [`tests/test_shaper_scientific.py`](../../tests/test_shaper_scientific.py)
(requer hubs SQLite em Z:; skip se ausente). Claims **validados** (10 testes):

| Strategy | Claim validado | Como (estatistico) |
|---|---|---|
| `fk_preserving` | integridade referencial preservada | 0 FKs orfas em todas as arestas in-scope; sem amplificacao; fact <= volume; determinismo |
| `stratify` | alocacao proporcional preserva distribuicao | chi2 p>0.05 + TVD<0.02 sobre a amostra REAL (Adult sex); cobertura min-1 de todos os grupos (race) |
| `join` (flat) | LEFT JOIN preserva contagem do fact | `|flat| == |fact|`, sem perda nem multiplicacao |
| `volume` (random) | amostra random preserva marginais | TVD<0.05 por coluna categorica (sex/race/education) a 5k |
| `schema` levels | niveis coerentes com topologia FK | `core` tem >=1 FK interna; `chain` estende `core` com mais arestas |

Rigor: P2/P4 recomputam metricas das LINHAS retornadas (nao confiam no
`METRICS_JSON` do trace). `compressibility` e `order` (sorted/reverse) tem
cobertura funcional em `test_shaper.py`; `order=random` uniformidade nao e'
gated (over-engineering p/ `random.shuffle`).

## Dependencias

Nenhuma dependencia em `tcf` (modulo). Independente.

## Pendencias

- **T-SHAPER-CODE-HARDENING** (P2): escala (filter-before-load >100k linhas),
  fragilidade do lazy-load de strategies (importar 1 strategy antes do 1o
  apply silencia as outras), bug latente `lstrip("lops_")` em join.py,
  dedup de alocacao proporcional. Nao bloqueia o uso atual (<=100k linhas).
- Manter `SCHEMA_LEVELS` + gate atualizados se o hub SQLite mudar (raro).
