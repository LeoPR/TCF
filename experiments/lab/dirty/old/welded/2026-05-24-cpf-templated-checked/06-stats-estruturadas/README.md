---
title: Sub-exp 06 — NatureApplyStats estruturadas
status: stub
---

# Sub-exp 06 — Stats estruturadas (H2)

## Motivacao

Filosofia acordada (2026-05-24): filtro generico + erros especificos
do tipo. Implementar e validar.

## Design

```python
@dataclass
class NatureApplyStats:
    nature: str                       # "cpf", "ip", "cnpj"
    n_total: int
    n_compressed: int
    n_fallback: int
    apply_rate: float                 # n_compressed / n_total
    confidence_score: float           # 0-1, "isto e' CPF mesmo?"
    fallback_reasons: dict[str, int]  # especifico do tipo
```

Fallback reasons CPF:
- `format_mismatch`: nao casa regex (qualquer tipo)
- `check_invalid`: format OK mas check digit errado
- `chars_invalid`: char nao-digito em posicao de digito
- `length_wrong`: comprimento errado

## Integracao com SideOutputs

```python
@dataclass
class SideOutputs:
    ...
    nature_stats: list[NatureApplyStats] | None = None
```

Populado apenas quando encoder aplica pre-tx por natureza
(sub-exp 05 ja' implementado).

## Criterio de aceite

- Stats refletem realidade (validar contra contagem manual)
- Custo desprezivel sem `side_outputs=`
- Multiplos NatureApplyStats por coluna se varias naturezas aplicadas
