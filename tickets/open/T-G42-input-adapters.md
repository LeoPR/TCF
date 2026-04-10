---
title: Adaptadores de entrada — SQLite, Parquet, DataFrames, JSON
type: task
status: OPEN
priority: MEDIUM
---

# Input Adapters

## Estado atual

Encoder so aceita **CSV + metadata.json**. Para virar ferramenta real,
precisa aceitar outras fontes comuns.

## Adapters propostos

### SQLite
```python
from tcf.adapters import from_sqlite
tcf_text = from_sqlite("db.sqlite3", tables=["clientes", "produtos", "vendas"], level=2)
```

Le schema do SQLite (PRAGMA table_info) — se P-schema-extension for adotado,
popula automaticamente PK/FK/types/nullability.

### Parquet
```python
from tcf.adapters import from_parquet
tcf_text = from_parquet("data.parquet", level=2)
```

Parquet ja tem schema — mapeamento direto para tipos TCF.
Requer `pyarrow` como dependencia OPCIONAL (nao no core).

### Pandas DataFrame
```python
from tcf.adapters import from_dataframe
tcf_text = from_dataframe(df, level=2)
```

Mais comum que CSV em workflows de DS. Requer pandas opcional.

### JSON / JSONL
```python
from tcf.adapters import from_jsonl
tcf_text = from_jsonl("data.jsonl", level=2)
```

Flat JSONL → TCF. Infere tipos das primeiras N linhas.

### SQL query direto
```python
from tcf.adapters import from_sql
tcf_text = from_sql("postgresql://...", query="SELECT * FROM vendas WHERE ...", level=2)
```

Mais poderoso — permite filter/join no SQL e exportar direto.
Requer `sqlalchemy` opcional.

## Design: opcionais organizados

```toml
# pyproject.toml
[project.optional-dependencies]
parquet = ["pyarrow>=10"]
pandas = ["pandas>=1.5"]
sql = ["sqlalchemy>=2.0"]
all = ["tcf-format[parquet,pandas,sql]"]
```

Usuario instala so o que precisa:
```bash
pip install tcf-format          # core, zero deps
pip install tcf-format[parquet]  # + parquet
pip install tcf-format[all]      # tudo
```

## Output adapters (reverso)

Tambem suportar saida:
- `tcf decode file.tcf --to sqlite output.db`
- `tcf decode file.tcf --to parquet output.parquet`
- `tcf decode file.tcf --to jsonl output.jsonl`

## Relacao com outros tickets

- **P-schema-extension**: se TCF tem schema declarado, adapters preenchem
  automaticamente dos metadados originais (SQLite DDL, Parquet schema)
- **T-G41-cli-lib**: adapters expostos via CLI `tcf encode --from ...`

## Tarefas

- [ ] Criar modulo `src/tcf/adapters/`
- [ ] Adapter SQLite (sem dep externa)
- [ ] Adapter Parquet (dep opcional pyarrow)
- [ ] Adapter Pandas (dep opcional pandas)
- [ ] Adapter JSONL (sem dep)
- [ ] Adapter SQL query (dep opcional sqlalchemy)
- [ ] Testes para cada adapter (roundtrip)
- [ ] Documentar em docs/adapters.md
