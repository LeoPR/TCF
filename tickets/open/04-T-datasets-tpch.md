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

Download vai direto para o disco externo configurado em
`config/storage.json` (via `scripts/_paths.py`). Nao polui git
nem OneDrive.

```python
# scripts/setup_tpch.py
import duckdb
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import external_dir, ensure_dirs

SF = 0.01
ensure_dirs()
output = external_dir("tpch-sf001")
output.mkdir(parents=True, exist_ok=True)
print(f"Downloading TPC-H SF={SF} to {output}")

con = duckdb.connect(":memory:")
con.execute("INSTALL tpch; LOAD tpch;")
con.execute(f"CALL dbgen(sf={SF})")

tables = ["region", "nation", "supplier", "customer",
          "part", "partsupp", "orders", "lineitem"]

for table in tables:
    path = output / f"{table}.csv"
    con.execute(f"""
        COPY (SELECT * FROM {table})
        TO '{path}'
        (HEADER, DELIMITER ',')
    """)
    row_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"  {table}: {row_count} rows -> {path}")

con.close()
print("Done.")

# Criar amostra pequena para git (lineitem com 100 rows)
sample_src = output / "lineitem.csv"
sample_dst = Path("datasets/samples/tpch-sf001/lineitem-sample.csv")
sample_dst.parent.mkdir(parents=True, exist_ok=True)
with open(sample_src, encoding="utf-8") as f:
    lines = [next(f) for _ in range(101)]  # header + 100 rows
sample_dst.write_text("".join(lines), encoding="utf-8")
print(f"Sample saved: {sample_dst}")
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

- [ ] Criar `scripts/setup_tpch.py` (usa `scripts/_paths.py`)
- [ ] Rodar e verificar que 8 CSVs foram gerados em `Z:\tcf-data\external\tpch-sf001\`
- [ ] Criar `datasets/canonical/tpch-sf001/metadata.json` com schema completo (PK/FK/tipos)
- [ ] Criar `datasets/canonical/tpch-sf001/README.md` (origem, licenca, como usar)
- [ ] Criar `datasets/samples/tpch-sf001/` com amostras pequenas:
  - `region.csv` (5 rows, ~400B)
  - `nation.csv` (25 rows, ~2KB)
  - `lineitem-sample.csv` (100 rows, ~30KB)
- [ ] Verificar que TPC-H license permite uso academico (sim, TPC Fair Use)
- [ ] Commit de metadata + README + samples — NAO dos CSVs completos

## Verificacao

- 8 CSVs em `Z:\tcf-data\external\tpch-sf001\`
- Cada CSV tem header + rows
- `lineitem.csv` tem ~60K rows
- `metadata.json` valido em `datasets/canonical/tpch-sf001/`
- Amostras em `datasets/samples/tpch-sf001/` (em git)
- Comando reproducivel: `python scripts/setup_tpch.py`
- Git nao tem os CSVs grandes (so samples e metadata)
