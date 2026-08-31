---
title: Derivacoes — gerar CSV, JSONL, Markdown a partir do SQLite
type: task
status: DONE
priority: 7
parent: 01-M-datasets-setup
completed: 2026-04-11
---

## STATUS: COMPLETO (2026-04-11)

**Arquitetura aplicada:** 3 writers modulares + 1 orquestrador.
Writers recebem `list[dict]` generico — nao sabem de SQLite nem pandas.
Isso e a mesma separacao que o TCF core vai ter: aceita estruturas
Python, nao depende de fonte especifica.

**Criado:** `scripts/writers/` (modulo)
- `__init__.py` — expoe `write_csv`, `write_jsonl`, `write_markdown`
- `csv_writer.py` (~35 linhas) — stdlib csv, `NULL → ""`
- `jsonl_writer.py` (~35 linhas) — stdlib json, preserva tipos reais
- `markdown_writer.py` (~50 linhas) — tabela pipe, truncagem >500 rows

**Criado:** `scripts/derive_formats.py` (~100 linhas)
- Usa `DatasetReader.iter_rows()` (streaming para evitar OOM em lineitem)
- Orquestra reader + writers
- CLI: `--formats csv jsonl markdown` ou subset

**Executado para ambos datasets:**
```
adult-census:
  csv      48,842 rows   5.2 MB  (1.06s)
  jsonl    48,842 rows  16.4 MB  (1.18s)  ← 3.1x CSV
  markdown    500 rows  69.2 KB  (truncado de 48,842)

tpch-sf001 (8 tables, 86,805 rows total):
  lineitem.csv     60,175 rows   7.2 MB  (1.47s)
  lineitem.jsonl   60,175 rows  23.0 MB  (1.62s)  ← 3.2x CSV
  [outras 7 tabelas todas geradas em <0.1s cada]
```

**Storage verificado:**
- 61 MB em `Z:\tcf-data\processed\` (gitignored)
- 0 arquivos derivados no git (so scripts)

**Observacoes ja visiveis sem LLM:**
- **JSONL e 3x pior que CSV** em tamanho para dados tabulares reais
  (confirma o que assumimos, agora com dados canonicos)
- **Markdown e invivel** para tabelas grandes (truncado em 500 rows)
- **TPC-H partsupp, orders, lineitem** sao os candidatos para testar
  compressao columnar (maiores, mais repeticao)

**Reproducivel:**
```
python scripts/derive_formats.py                          # tudo
python scripts/derive_formats.py tpch-sf001               # um dataset
python scripts/derive_formats.py --formats csv jsonl      # subset
```

**Nao fizemos ainda (intencional):**
- TCF derivation — e TCF vai precisar do encoder real apos definirmos
  a pergunta cientifica nuclear. Por enquanto os writers sao baseline.
- TOON — mesma razao. Ticket futuro.

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
