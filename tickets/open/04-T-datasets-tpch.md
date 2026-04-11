---
title: Download e setup TPC-H SF=0.01
type: task
status: DONE
priority: 3
parent: 01-M-datasets-setup
completed: 2026-04-11
---

## STATUS: COMPLETO (2026-04-11)

**Criado:** `scripts/setup_tpch.py` (~300 linhas)
- Schema hard-coded com PK, FK, tipos por tabela (TPC-H spec v3.0.1)
- Usa `_paths.ensure_dirs()` e `_paths.external_dir()` para storage
- Download via DuckDB tpch extension (~0.2s para SF=0.01)
- Gera `datasets/canonical/tpch-sf001/metadata.json` completo
- Gera samples em `datasets/samples/tpch-sf001/` para git

**Rodado:**
```
python scripts/setup_tpch.py
[tpch] SF=0.01 -> Z:\tcf-data\external\tpch-sf001
[tpch] dbgen completed in 0.2s
[tpch]   region    :        5 rows  (     0.4 KB)
[tpch]   nation    :       25 rows  (     2.2 KB)
[tpch]   supplier  :      100 rows  (    13.7 KB)
[tpch]   customer  :    1,500 rows  (   238.6 KB)
[tpch]   part      :    2,000 rows  (   237.7 KB)
[tpch]   partsupp  :    8,000 rows  ( 1,132.4 KB)
[tpch]   orders    :   15,000 rows  ( 1,640.1 KB)
[tpch]   lineitem  :   60,175 rows  ( 7,222.7 KB)
86,805 total rows, ~10.4 MB raw, 8 tables.
```

**Storage 3-camadas verificado:**
- Camada B (disco): 10MB em Z:\tcf-data\external\tpch-sf001\
- Camada A (git): metadata.json + 6 samples (~23KB total)
- Nenhum CSV grande no git

**Samples gerados (em git):**
- region.csv (inteiro, 5 rows, 415B)
- nation.csv (inteiro, 25 rows, 2.2KB)
- supplier-sample.csv (20 rows, 2.7KB)
- customer-sample.csv (20 rows, 3.3KB)
- orders-sample.csv (20 rows, 2.4KB)
- lineitem-sample.csv (100 rows, 11.9KB)

**Reproducivel:** `python scripts/setup_tpch.py --sf 0.01` (ou outro SF)

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
