import os
import json
import argparse
from typing import Any, Dict, Iterable, Tuple, List


def flatten_record(rec: Dict[str, Any], parent: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in rec.items():
        key = f"{parent}.{k}" if parent else k
        if isinstance(v, dict):
            out.update(flatten_record(v, key))
        else:
            out[key] = v
    return out


def pick_default_table(data: Dict[str, List[Dict[str, Any]]]) -> str:
    # Prefer table that has nested objects; else first by name
    for tname, rows in data.items():
        for r in rows:
            if any(isinstance(v, dict) for v in r.values()):
                return tname
    return next(iter(data.keys())) if data else ""


def format_table(rows: List[Dict[str, Any]], max_width: int = 32, max_rows: int = 50) -> str:
    if not rows:
        return "<vazio>"
    # column order: stable based on first row keys, then the rest sorted
    all_cols: List[str] = []
    seen = set()
    for r in rows:
        for c in r.keys():
            if c not in seen:
                seen.add(c)
                all_cols.append(c)
    # compute widths
    def cell_str(v: Any) -> str:
        s = "" if v is None else str(v)
        s = s.replace("\n", " ")
        if len(s) > max_width:
            s = s[: max_width - 1] + "…"
        return s

    widths = {c: max(len(c), *(len(cell_str(r.get(c, ""))) for r in rows[:max_rows])) for c in all_cols}

    # build lines
    sep = "+" + "+".join("-" * (widths[c] + 2) for c in all_cols) + "+"
    header = "|" + "|".join(" " + c.ljust(widths[c]) + " " for c in all_cols) + "|"

    out_lines = [sep, header, sep]
    for r in rows[:max_rows]:
        line = "|" + "|".join(" " + cell_str(r.get(c, "")).ljust(widths[c]) + " " for c in all_cols) + "|"
        out_lines.append(line)
    if len(rows) > max_rows:
        more = len(rows) - max_rows
        out_lines.append(f"… ({more} linhas não exibidas)")
    out_lines.append(sep)
    return "\n".join(out_lines)


def main():
    ap = argparse.ArgumentParser(description="Imprime tabela visual a partir do consolidated.json")
    ap.add_argument("--file", default="consolidated.json", help="Caminho para consolidated.json")
    ap.add_argument("--table", default=None, help="Tabela base a imprimir (default: detecta a com objetos aninhados)")
    ap.add_argument("--max-width", type=int, default=32, help="Largura máxima por coluna")
    ap.add_argument("--max-rows", type=int, default=50, help="Número máximo de linhas a imprimir")
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        print(f"Arquivo não encontrado: {args.file}")
        raise SystemExit(1)

    with open(args.file, encoding="utf-8") as f:
        cons = json.load(f)

    data = cons.get("data", {})
    if not data:
        print("Sem dados em 'data'")
        raise SystemExit(1)

    table = args.table or pick_default_table(data)
    if not table:
        print("Não foi possível determinar tabela para impressão.")
        raise SystemExit(1)
    if table not in data:
        print(f"Tabela '{table}' não existe no consolidated")
        raise SystemExit(1)

    flat_rows = [flatten_record(r) for r in data[table]]
    print(f"Tabela: {table}  (linhas: {len(flat_rows)})")
    print(format_table(flat_rows, max_width=args.max_width, max_rows=args.max_rows))


if __name__ == "__main__":
    main()
