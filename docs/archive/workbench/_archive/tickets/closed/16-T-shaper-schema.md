---
title: Schema strategy (niveis nomeados)
type: task
status: OPEN
priority: 15
parent: 12-M-dataset-shaper
---

# Schema

`scripts/shaper/strategies/schema.py`

Niveis pre-definidos por dataset:

**Adult:**
- `minimal` → so `adult` (unica tabela)
- `full` → `adult`
(Adult e flat, entao minimal == full)

**TPC-H:**
- `minimal` → so `customer` (1 tabela)
- `core` → `customer` + `orders` (2 tabelas, 1 FK)
- `chain` → `customer` + `orders` + `lineitem` (3 tabelas, cadeia)
- `full` → todas 8 tabelas
- `custom=["nation", "supplier"]` → lista explicita

Precisa de um mapeamento `{dataset: {level: [tables]}}` em config ou metadata.

## Tarefas

- [ ] Implementar SchemaStrategy
- [ ] Definir mapeamento por dataset (pode ser em metadata.json ou hardcoded)
- [ ] Registrar no pipeline
- [ ] Testes: cada nivel para Adult e TPC-H
- [ ] Teste: `custom=["nation"]` retorna so nation
