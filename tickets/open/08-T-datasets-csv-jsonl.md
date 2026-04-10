---
title: Derivacoes — gerar CSV, JSONL, Markdown a partir do SQLite
type: task
status: OPEN
priority: 7
parent: 01-M-datasets-setup
---

# Derivacoes a partir do SQLite

## Objetivo

Gerar as representacoes "baseline" de cada dataset:
- CSV (flat)
- JSONL (row-by-row com types)
- Markdown table

**Fonte unica:** SQLite (garante consistencia).
**NAO incluir TCF, TOON ou outros formatos ainda** — eles virao em outra fase.

## Localizacao

```
datasets/derivations/
├── tpch-sf001/
│   ├── csv/
│   │   ├── region.csv
│   │   ├── nation.csv
│   │   ├── ...
│   │   └── lineitem.csv
│   ├── jsonl/
│   │   ├── region.jsonl
│   │   └── ...
│   └── markdown/
│       ├── region.md
│       └── ...
└── adult-census/
    ├── csv/
    │   └── adult.csv
    ├── jsonl/
    │   └── adult.jsonl
    └── markdown/
        └── adult.md
```

## Implementacao

`scripts/derive_formats.py`:

```python
import sqlite3
import csv
import json
from pathlib import Path

def derive_table(con, table_name, out_dir):
    # Get schema
    cursor = con.execute(f'SELECT * FROM "{table_name}"')
    cols = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    # CSV
    csv_path = out_dir / "csv" / f"{table_name}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)

    # JSONL (com tipos preservados)
    jsonl_path = out_dir / "jsonl" / f"{table_name}.jsonl"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in rows:
            obj = dict(zip(cols, row))
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    # Markdown table (limitado a 50 rows se for grande)
    md_path = out_dir / "markdown" / f"{table_name}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with md_path.open("w", encoding="utf-8") as f:
        f.write("| " + " | ".join(cols) + " |\n")
        f.write("|" + "|".join("---" for _ in cols) + "|\n")
        for row in rows[:50]:
            vals = [str(v) if v is not None else "" for v in row]
            f.write("| " + " | ".join(vals) + " |\n")
        if len(rows) > 50:
            f.write(f"\n*... {len(rows) - 50} more rows truncated*\n")

    return len(rows)

def main():
    for db_name in ["tpch-sf001", "adult-census"]:
        db_path = Path(f"datasets/sqlite/{db_name}.db")
        out_dir = Path(f"datasets/derivations/{db_name}")

        con = sqlite3.connect(db_path)
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        print(f"\n{db_name}:")
        for table in tables:
            count = derive_table(con, table, out_dir)
            print(f"  {table}: {count} rows")

        con.close()

if __name__ == "__main__":
    main()
```

## Tarefas

- [ ] Criar `scripts/derive_formats.py`
- [ ] Rodar para tpch-sf001 (gera 8 tabelas × 3 formatos = 24 arquivos)
- [ ] Rodar para adult-census (gera 1 tabela × 3 formatos = 3 arquivos)
- [ ] Verificar tamanhos: CSV < JSONL < MD (tipicamente)
- [ ] Verificar consistencia: numero de rows bate entre formatos
- [ ] Sanity check: primeira row em CSV == primeira row em JSONL (parsed)

## Criterio

- Arquivos existem em `datasets/derivations/{name}/{format}/`
- Script e idempotente (roda multiplas vezes sem quebrar)
- Formato Markdown tem truncagem clara se > 50 rows
- .gitignore exclui os arquivos gerados (sao grandes, usuario regenera)

## O que NAO fazer aqui

- **Nao gerar TCF** (esta fase e so baseline)
- **Nao gerar TOON** (esta fase e so baseline)
- **Nao otimizar formato** (esta fase e so baseline)
- **Nao medir accuracy LLM** (esta fase e so baseline)

Isso tudo vem em fases futuras.
