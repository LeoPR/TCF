"""scan — varre os NOSSOS datasets por colunas de domínio ≈2 (candidatas a boolean/enum-2).

Objetivo (owner): entender como boolean REALMENTE aparece nos dados antes de desenhar a spec.
Cataloga por variante de superfície (1/0, t/f, true/false, True/False, Y/N, …) vs enum-2 arbitrário
(Male/Female, O/F). Fonte: datasets/synthetic/*.csv + hubs SQLite em Z:/tcf-data/interim/.
Não toca src/tcf.
"""
from __future__ import annotations
import csv
import sqlite3
from pathlib import Path

# variantes de superfície CONHECIDAS de boolean (par de valores -> nome da variante)
BOOL_VARIANTS = [
    (frozenset({"true", "false"}), "true/false"),
    (frozenset({"True", "False"}), "True/False"),
    (frozenset({"TRUE", "FALSE"}), "TRUE/FALSE"),
    (frozenset({"t", "f"}), "t/f"),
    (frozenset({"T", "F"}), "T/F"),
    (frozenset({"1", "0"}), "1/0"),
    (frozenset({"yes", "no"}), "yes/no"),
    (frozenset({"Yes", "No"}), "Yes/No"),
    (frozenset({"YES", "NO"}), "YES/NO"),
    (frozenset({"Y", "N"}), "Y/N"),
    (frozenset({"y", "n"}), "y/n"),
    (frozenset({"sim", "nao"}), "sim/nao"),
    (frozenset({"S", "N"}), "S/N"),
]


def classify(distinct):
    """(kind, variante) — 'bool' se cabe numa variante conhecida; 'enum2' se 2 arbitrários; senão 'domN'."""
    ds = frozenset(str(x) for x in distinct)
    for pair, name in BOOL_VARIANTS:
        if ds <= pair and len(ds) >= 1:
            return "bool", name
    if len(ds) == 2:
        return "enum2", "|".join(sorted(ds))[:36]
    return f"dom{len(ds)}", "|".join(sorted(ds))[:36]


def scan_csv(path, max_d=3):
    try:
        with open(path, encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
    except Exception:
        return []
    if len(rows) < 2:
        return []
    header, data = rows[0], rows[1:]
    out = []
    for i, h in enumerate(header):
        vals = [r[i] for r in data if i < len(r)]
        d = sorted(set(vals))
        if 1 <= len(d) <= max_d:
            kind, variant = classify(d)
            out.append({"src": path.name, "col": h, "n": len(vals), "ndist": len(d),
                        "vals": d[:6], "kind": kind, "variant": variant})
    return out


def scan_db(dbpath, max_d=3, max_tables=40):
    out = []
    try:
        con = sqlite3.connect(f"file:{dbpath}?mode=ro", uri=True)
    except Exception as e:
        return [{"src": Path(dbpath).stem, "col": "(open erro)", "n": 0, "ndist": 0,
                 "vals": [str(e)[:40]], "kind": "erro", "variant": ""}]
    cur = con.cursor()
    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()][:max_tables]
    for t in tables:
        try:
            cols = [r[1] for r in cur.execute(f'PRAGMA table_info("{t}")').fetchall()]
            n = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            for c in cols:
                d = cur.execute(f'SELECT COUNT(DISTINCT "{c}") FROM "{t}"').fetchone()[0]
                if 1 <= d <= max_d:
                    vals = [str(r[0]) for r in cur.execute(
                        f'SELECT DISTINCT "{c}" FROM "{t}" LIMIT 6').fetchall()]
                    kind, variant = classify(vals)
                    out.append({"src": f"{Path(dbpath).stem}.{t}", "col": c, "n": n, "ndist": d,
                                "vals": vals, "kind": kind, "variant": variant})
        except Exception as e:
            out.append({"src": f"{Path(dbpath).stem}.{t}", "col": "(erro)", "n": 0, "ndist": 0,
                        "vals": [str(e)[:40]], "kind": "erro", "variant": ""})
    con.close()
    return out
