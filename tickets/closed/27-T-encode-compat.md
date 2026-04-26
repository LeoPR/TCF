---
title: Manter encode() original como wrapper (backwards compat)
type: task
status: OPEN
priority: 26
parent: 24-M-phase2-tcf-refactor
---

# Backwards Compatibility

## Objetivo

O `encode(meta_path, data_dir, config)` original continua existindo
como **conveniencia**. Internamente usa `encode_columns()`.

Nenhum teste existente, CLI, ou experiment runner deve quebrar.

## Como funciona apos refactoring

```python
def encode(meta_path, data_dir, config=None):
    """Convenience: read CSVs + join + encode_columns."""
    # 1. Read schema
    schema = load_schema(meta_path, data_dir)
    # 2. Read CSVs
    all_data = _read_csvs(schema)
    # 3. Join tables (resolve FKs)
    fact_name, col_names, columns = _join_tables(schema, all_data)
    # 4. Delegate to core
    return encode_columns(fact_name, columns, config=config)
```

O IO (passos 1-3) fica no wrapper. O core (passo 4) e puro.

## Tarefas

- [ ] Refatorar encode() para chamar encode_columns() internamente
- [ ] Verificar: CLI `python -m tcf encode` continua funcionando
- [ ] Verificar: `from tcf import encode` continua funcionando
- [ ] Todos os 112 testes de core passam SEM MODIFICACAO
- [ ] __init__.py exporta encode, encode_columns, encode_rows
