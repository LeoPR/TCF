---
title: Download e setup TPC-H SF=0.01
type: task
status: OPEN
priority: 3
parent: 01-M-datasets-setup
---

# TPC-H SF=0.01

## O que e

TPC-H e o benchmark padrao da industria para decision support desde 1999.
Schema de 8 tabelas relacional normalizado, dominio: wholesale retail.

## Por que SF=0.01

Scale factor 0.01 = ~10MB total:
- `region`: 5 rows
- `nation`: 25 rows
- `supplier`: 100 rows
- `customer`: 1.500 rows
- `part`: 2.000 rows
- `partsupp`: 8.000 rows
- `orders`: 15.000 rows
- `lineitem`: ~60.000 rows

Grande o suficiente para testar compressao (lineitem tem 60K), pequeno
o suficiente para caber num LLM amostrado.

## Como gerar (DuckDB)

```python
# scripts/setup_tpch.py
import duckdb
from pathlib import Path

OUTPUT = Path("datasets/canonical/tpch-sf001")
OUTPUT.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(":memory:")
con.execute("INSTALL tpch; LOAD tpch;")
con.execute("CALL dbgen(sf=0.01)")

tables = ["region", "nation", "supplier", "customer",
          "part", "partsupp", "orders", "lineitem"]

for table in tables:
    path = OUTPUT / f"{table}.csv"
    con.execute(f"""
        COPY (SELECT * FROM {table})
        TO '{path}'
        (HEADER, DELIMITER ',')
    """)
    row_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table}: {row_count} rows -> {path}")

con.close()
print("Done.")
```

## Metadata

Criar `datasets/canonical/tpch-sf001/metadata.json`:

```json
{
  "name": "tpch-sf001",
  "source": "TPC-H Benchmark v3.0.1 (via DuckDB)",
  "scale_factor": 0.01,
  "origin": "https://www.tpc.org/tpch/",
  "license": "TPC Fair Use Agreement",
  "downloaded": "2026-04-10",
  "tables": {
    "region": {
      "pk": ["r_regionkey"],
      "columns": {
        "r_regionkey": {"type": "int", "nullable": false},
        "r_name": {"type": "string", "nullable": false},
        "r_comment": {"type": "string", "nullable": true}
      }
    },
    "nation": {
      "pk": ["n_nationkey"],
      "fk": {"n_regionkey": "region.r_regionkey"},
      "columns": { ... }
    },
    ...
  }
}
```

Schema completo esta no spec oficial TPC-H. Vamos popular manualmente
a partir do spec (ou via DuckDB information_schema).

## Tarefas

- [ ] Criar `scripts/setup_tpch.py`
- [ ] Rodar e verificar que 8 CSVs foram gerados
- [ ] Criar `metadata.json` com schema completo (PK/FK/tipos)
- [ ] Criar `README.md` no dataset com descricao
- [ ] Verificar que o TPC-H license permite uso academico (sim, permite)
- [ ] Commit das estruturas (metadata + README) mas NAO dos CSVs
  (ficam no .gitignore — usuario regenera)

## Verificacao

- 8 CSVs em `datasets/canonical/tpch-sf001/`
- Cada CSV tem header + rows
- `lineitem.csv` tem ~60K rows
- `metadata.json` valido
- Comando reproducivel: `python scripts/setup_tpch.py`
