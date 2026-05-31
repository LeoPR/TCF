---
title: Sub-exp 02 — Heuristica refinada
type: sub-experiment
status: active
tags: [tcf, heuristic, detect-cadence, refinement]
created: 2026-05-19
updated: 2026-05-19
parent: 2026-05-19-h-da-09b-refino-real-world
---

# Sub-exp 02 — Heuristica refinada

## Analise do sub-exp 01

Pattern HELP (12 cols):
- HELP numeric com cardinalidade alta: 8 cases (fnlwgt, c_acctbal,
  ps_supplycost, o_totalprice, ps_availqty, o_custkey, l_partkey,
  l_extendedprice)
- HELP wrapper+counter (uniform_length + LCP+LCS alto): 4 cases
  (c_name, s_name, p_brand, o_clerk)

Pattern HURT (22 cols):
- **0% numeric**
- Comments (text livre), phones (uniform mas LCP+LCS baixo),
  dates (uniform mas conteudo varia), descritivas

Pattern NO-OP (42 cols):
- Maioria com cardinalidade baixa (categoricals) — line-refs ja' cobre

## Heuristica atual

```python
if uniform_length AND LCP+LCS >= 0.7:
    return True
return False
```

Captura: 4/12 HELP. Perde 8 HELP numericos.

## Heuristica refinada proposta

```python
def detect_cadence(strings, ...):
    # Regra 1 (existente): wrapper+counter pattern
    if uniform_length AND LCP+LCS >= 0.7:
        return True

    # Regra 2 (NOVA): numeric high-cardinality
    if is_numeric AND cardinality > 0.5:
        return True

    return False
```

`is_numeric` deve aceitar floats (decimals) e negativos:
```python
def is_numeric_string(v):
    if not v:
        return False
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False
```

## Predicao (sem rodar)

- Captura todos 12 HELP (8 via regra 2 + 4 via regra 1)
- HURT: 0 false positives (HURT tem 0% numeric → regra 2 nao dispara;
  HURT tem LCP+LCS baixo ou uniform_length False → regra 1 nao dispara)

## Validacao

`run.py` aplica nova heuristica em todas 76 cols do audit. Mede:
- Cases corretos (HELP enabled, HURT/NO-OP nao enabled)
- False positives (HURT enabled → HEN)
- False negatives (HELP nao enabled)
- Bytes salvos esperados
