---
title: Shaper end-to-end test (Adult + TPC-H)
type: task
status: OPEN
priority: 17
parent: 12-M-dataset-shaper
---

# E2E test

Validar que o pipeline completo funciona com combinacoes reais.

## Cenarios de teste

### Adult (flat, 1 tabela)
```python
# 1. Tudo
shape(dataset="adult-census") → 48842 rows

# 2. 10%
shape(dataset="adult-census", volume=0.1) → ~4884 rows

# 3. 100 rows, random
shape(dataset="adult-census", volume=100, order="random", seed=42)

# 4. Sorted por age
shape(dataset="adult-census", volume=50, order="sorted:age")

# 5. Determinismo
r1 = shape(..., seed=42)
r2 = shape(..., seed=42)
assert r1.tables == r2.tables
```

### TPC-H (relacional, 8 tabelas)
```python
# 6. Schema minimal (so customer)
shape(dataset="tpch-sf001", schema="minimal") → 1 tabela, 1500 rows

# 7. Schema core (customer + orders)
shape(dataset="tpch-sf001", schema="core") → 2 tabelas

# 8. Schema chain (customer + orders + lineitem)
shape(dataset="tpch-sf001", schema="chain") → 3 tabelas

# 9. Full com volume
shape(dataset="tpch-sf001", schema="full", volume=0.01) → 8 tabelas, ~1% cada

# 10. Schema custom
shape(dataset="tpch-sf001", schema=["nation", "region"]) → 2 tabelas pequenas
```

### Invariantes a verificar em todos
- rows retornadas <= rows pedidas
- trace nao esta vazio
- metadata presente
- request preservado no resultado

## CLI de demo

```bash
python -m scripts.shaper --dataset adult-census --volume 100 --order random --seed 42
# Imprime resumo: tabelas, rows, trace
```

## Tarefas

- [ ] Criar arquivo de teste `tests/test_shaper.py` com cenarios 1-10
- [ ] Criar CLI minimo de demo/smoke test
- [ ] Todos os testes passam
- [ ] Documentar uso basico em `scripts/shaper/README.md`
