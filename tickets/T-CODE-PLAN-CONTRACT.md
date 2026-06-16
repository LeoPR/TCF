---
title: T-CODE-PLAN-CONTRACT — Plan dataclass (group_by/order/batch_size)
status: deferred
priority: P3
created: 2026-05-24
updated: 2026-06-15
blocked-by: []
related:
  - docs/workbench/research-notes/_archive/2026-05-05-v04-design-recap.md
  - experiments/lab/dirty/notas/futuras-otimizacoes-formato.md
  - tickets/T-CODE-ENCODER-MANAGER.md
---

# T-CODE-PLAN-CONTRACT — Plan dataclass

> **Fechamento 0.7 (2026-06-15) — PARK v2.0**: contrato foundacional pra ordering
> reversivel (O-FMT-01..04), nao critico pro 0.7 (compressao de bytes ja' completa:
> V2-A/B/split + sort_by welded). O-FMT-02 `sort_by` (order-free) ja' cobre o caso
> simples de reordenacao. Retomar quando v2.0 abrir.

## Contexto

Plano v0.4 (D8, D11, D13) registrou conceito de `Plan`:

```python
@dataclass
class Plan:
    group_by: list[str] | None = None
    order: str = "input"           # input | lex | numeric | frequency_desc
    batch_size: int | None = None
    batch_unit: str = "groups"     # groups | rows
```

Plan eh **contrato estavel** entre otimizadores (heuristica, futuro SQL)
e encoder. Otimizadores produzem Plans; encoder consome.

Hoje encoder nao aceita Plan — defaults hard-coded. Habilitar Plan
desbloqueia O-FMT-01..04 (ordenacao reversivel) e prepara SQL->Plan (D8).

## Plano

```python
from tcf import encode, Plan

# Sem Plan (default: ordem input, sem batch)
text = encode(table)

# Com Plan
plan = Plan(
    group_by=["country"],         # agrupa por coluna
    order="frequency_desc",       # ordena grupos
    batch_size=1000,
    batch_unit="rows",
)
text = encode(table, plan=plan)
```

### Behaviors esperados

- `group_by`: reagrupa rows agrupando valores identicos da coluna chave
  (preserva mapping reverso no header pra decode)
- `order`: lex/numeric/frequency em colunas relevantes
- `batch_size` + `batch_unit`: divide em chunks (combina com streaming
  T-CODE-ENCODER-MANAGER Fase 4)

### Reversibilidade

Mapping `original_index -> new_index` salvo no header pra decode
reconstruir ordem original. Tradeoff: bytes extras no header vs ganho
no body. Vale se `body_savings > header_cost`.

## Criterio de aceite

- [ ] `Plan` dataclass em `src/tcf/plan.py`
- [ ] `encode(data, plan=Plan(...))` aceita parametro
- [ ] `group_by="country"` em TPC-H customer reduz bytes >= 5% vs sem plan
- [ ] RT preservado byte-canonical com decode reconstruindo ordem original
- [ ] Tests: 5+ scenarios (sem plan, group_by, order variants, batch)

## Riscos

1. **API publica cresce**: Plan adiciona surface area; precisa ser
   conservadora (so' campos provados)
2. **Header gross**: mapping reverso pode ser grande pra tabelas com
   muitas rows; threshold de quando vale
3. **Interage com SideOutputs**: schema builder futuro consome Plan
   produzido por heuristica?

## Conexao

- [T-CODE-ENCODER-MANAGER](T-CODE-ENCODER-MANAGER.md) — manager consome Plan
- [T-CODE-SCHEMA-BUILDER](T-CODE-SCHEMA-BUILDER.md) — pode produzir Plan auto
- [O-FMT-01..04](../experiments/lab/dirty/notas/futuras-otimizacoes-formato.md)
  — ordering reversivel
- [v04-design-recap D8/D11/D13](../docs/workbench/research-notes/_archive/2026-05-05-v04-design-recap.md)

## Updates datados

### 2026-05-24 — abertura

Ticket aberto pos-ADR-0014. Plan eh decisao adiada do v0.4; reativado
agora que fachada `encode()` esta unificada. Implementacao pendente.
