---
title: SQLite hub — converter datasets canonicos para SQLite com tipos
type: task
status: OPEN
priority: 5
parent: 01-M-datasets-setup
---

# SQLite Hub

## Objetivo

Armazenar cada dataset canonico como **SQLite com schema tipado**.
SQLite vira a **fonte de verdade** para todas as derivacoes posteriores
(CSV, JSONL, MD, TCF, TOON).

## Por que SQLite

1. **Preserva tipos:** INT vs REAL vs TEXT vs DATE (CSV so tem strings)
2. **Preserva PK/FK:** restricoes declaradas explicitamente
3. **Queryavel:** podemos gerar ground truth via SQL
4. **Portavel:** arquivo unico, zero servidor
5. **Standard:** suportado por qualquer linguagem
6. **Reprodutivel:** schema declarativo, CREATE TABLE e documentacao

## Localizacao

```
datasets/sqlite/
├── tpch-sf001.db
└── adult-census.db
```

## Implementacao

```python
# scripts/csv_to_sqlite.py
import sqlite3
import csv
import json
from pathlib import Path

def create_tpch_sqlite():
    src = Path("datasets/canonical/tpch-sf001")
    dst = Path("datasets/sqlite/tpch-sf001.db")
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Load metadata
    meta = json.load(open(src / "metadata.json"))

    if dst.exists():
        dst.unlink()
    con = sqlite3.connect(dst)

    # For each table, create schema based on metadata + load CSV
    for table_name, table_meta in meta["tables"].items():
        # Build CREATE TABLE from metadata
        cols = []
        for col_name, col_meta in table_meta["columns"].items():
            sql_type = {
                "int": "INTEGER",
                "float": "REAL",
                "string": "TEXT",
                "date": "TEXT",  # ISO date as text (SQLite convention)
                "bool": "INTEGER",
            }[col_meta["type"]]
            nullable = "" if col_meta["nullable"] else " NOT NULL"
            cols.append(f'"{col_name}" {sql_type}{nullable}')

        # PK
        if table_meta.get("pk"):
            pk_cols = ", ".join(f'"{c}"' for c in table_meta["pk"])
            cols.append(f"PRIMARY KEY ({pk_cols})")

        # FK
        for fk_col, ref in table_meta.get("fk", {}).items():
            ref_table, ref_col = ref.split(".")
            cols.append(f'FOREIGN KEY ("{fk_col}") REFERENCES "{ref_table}"("{ref_col}")')

        create_sql = f'CREATE TABLE "{table_name}" (\n  ' + ",\n  ".join(cols) + "\n)"
        con.execute(create_sql)

        # Load CSV
        csv_path = src / f"{table_name}.csv"
        with csv_path.open() as f:
            reader = csv.reader(f)
            headers = next(reader)
            placeholders = ",".join("?" * len(headers))
            rows = list(reader)
            con.executemany(
                f'INSERT INTO "{table_name}" VALUES ({placeholders})',
                rows
            )
        print(f"  {table_name}: {len(rows)} rows")

    con.commit()
    con.close()
    print(f"Created {dst}")

# Similar function for Adult
def create_adult_sqlite():
    ...
```

## Verificacoes apos criacao

```sql
-- Verificar PK/FK
PRAGMA foreign_keys = ON;
PRAGMA foreign_key_check;  -- deve retornar vazio

-- Verificar tipos
PRAGMA table_info(lineitem);

-- Verificar contagens
SELECT COUNT(*) FROM lineitem;  -- deve bater com CSV

-- Queries que funcionam so em SQLite tipado (nao em CSV)
SELECT MIN(l_extendedprice), MAX(l_extendedprice), AVG(l_extendedprice)
FROM lineitem;
```

## Tarefas

- [ ] Criar `scripts/csv_to_sqlite.py`
- [ ] Implementar funcao para TPC-H
- [ ] Implementar funcao para Adult
- [ ] Verificar schemas via `PRAGMA table_info`
- [ ] Verificar FKs via `PRAGMA foreign_key_check`
- [ ] Rodar queries de sanidade (MIN/MAX/AVG por coluna numerica)
- [ ] Adicionar `datasets/sqlite/*.db` ao .gitignore
- [ ] Documentar comando de reconstrucao em `datasets/README.md`

## Verificacao

- `sqlite3 datasets/sqlite/tpch-sf001.db ".schema"` mostra tipos corretos
- Count em cada tabela bate com CSV
- FK valid (nenhum orfao)
- Queries SQL funcionam (agregacoes, joins)
