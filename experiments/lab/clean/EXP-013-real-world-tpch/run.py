"""EXP-013 — real-world TPC-H 8 tables via dataset_reader.

Aplica EXP-011 pipeline (encode_table) per tabela. Mede bytes + RT.
Cap em 5000 rows pra tabelas maiores (encode O(N²) — lineitem full
seria proibitivo).
"""

from __future__ import annotations

import csv
import io
import json
import sys
import time
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[3]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
EXP_010 = THIS.parent / "EXP-010-tcf-delta-aware-prototype"
EXP_011 = THIS.parent / "EXP-011-multi-column-basic"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(EXP_010))
sys.path.insert(0, str(EXP_011))

from dataset_reader import DatasetReader  # noqa: E402
from multi_col import encode_table, decode_table  # noqa: E402


MAX_ROWS = 5000  # cap pra evitar runtime explodir em lineitem/orders


def write_lf(path, content):
    if isinstance(content, str):
        content = content.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def table_to_csv_bytes(cols):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    col_names = list(cols.keys())
    w.writerow(col_names)
    n = len(next(iter(cols.values())))
    for i in range(n):
        w.writerow([cols[c][i] for c in col_names])
    return buf.getvalue().encode("utf-8")


def rows_to_cols(rows):
    if not rows:
        return {}
    col_names = list(rows[0].keys())
    return {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in col_names}


def process_table(reader, table_name: str) -> dict:
    print(f"\n--- {table_name} ---")
    full_count = reader.query(f"SELECT COUNT(*) FROM {table_name}")[0][0]
    limit = min(MAX_ROWS, full_count)

    t0 = time.perf_counter()
    rows = reader.rows(table_name, limit=limit)
    t_read = time.perf_counter() - t0

    cols = rows_to_cols(rows)
    raw_csv = table_to_csv_bytes(cols)

    t1 = time.perf_counter()
    tcf_text, info = encode_table(cols)
    t_encode = time.perf_counter() - t1

    t2 = time.perf_counter()
    decoded = decode_table(tcf_text)
    t_decode = time.perf_counter() - t2
    rt_ok = (decoded == cols)

    bytes_raw = len(raw_csv)
    bytes_tcf = len(tcf_text.encode("utf-8"))
    n_cols = len(cols)

    out_dir = THIS / "outputs"
    write_lf(out_dir / f"{table_name}.tcf", tcf_text)

    per_col = []
    for col, ci in info["col_info"].items():
        per_col.append({
            "col": col,
            "cadence_detected": ci["cadence_detected"],
            "hint_used": ci["hint_used"],
            "n_seq_runs": ci["n_seq_runs"],
            "n_unicas": ci["n_unicas"],
        })

    print(f"  rows={len(rows)}/{full_count} cols={n_cols}")
    print(f"  raw={bytes_raw}  tcf={bytes_tcf}  ratio={bytes_tcf/bytes_raw*100:.1f}%")
    print(f"  RT={'OK' if rt_ok else 'FAIL'}  enc={t_encode*1000:.0f}ms "
          f"dec={t_decode*1000:.0f}ms read={t_read*1000:.0f}ms")
    cad = sum(1 for p in per_col if p["cadence_detected"])
    print(f"  cadence em {cad}/{n_cols} colunas, "
          f"total seq_runs={sum(p['n_seq_runs'] for p in per_col)}")

    return {
        "table": table_name,
        "rows_actual": len(rows),
        "rows_full": full_count,
        "capped": len(rows) < full_count,
        "n_cols": n_cols,
        "bytes_raw": bytes_raw,
        "bytes_tcf": bytes_tcf,
        "ratio_pct": bytes_tcf / bytes_raw * 100,
        "delta_bytes": bytes_tcf - bytes_raw,
        "rt": "OK" if rt_ok else "FAIL",
        "t_read_ms": t_read * 1000,
        "t_encode_ms": t_encode * 1000,
        "t_decode_ms": t_decode * 1000,
        "per_col": per_col,
    }


def main():
    print(f"=== EXP-013 — Real-world TPC-H 8 tabelas (cap {MAX_ROWS} rows) ===")

    reader = DatasetReader("tpch-sf001")
    print(f"tables: {reader.tables}")

    results = []
    for table in reader.tables:
        try:
            r = process_table(reader, table)
            results.append(r)
        except Exception as e:
            print(f"  ERROR {table}: {e!r}")
            results.append({"table": table, "rt": "ERROR", "error": str(e)})

    reader.close()

    total_raw = sum(r.get("bytes_raw", 0) for r in results)
    total_tcf = sum(r.get("bytes_tcf", 0) for r in results)
    rt_pass = sum(1 for r in results if r.get("rt") == "OK")

    # Report
    report = [
        "# EXP-013 — Real-world TPC-H (report)",
        "",
        f"Cap: {MAX_ROWS} rows por tabela. Tabelas com mais rows sao truncadas.",
        "",
        "## Resumo por tabela",
        "",
        "| Tabela | rows | full | cols | raw (B) | TCF (B) | TCF/raw | ratio | RT | enc ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for r in results:
        if r.get("rt") == "ERROR":
            report.append(f"| `{r['table']}` | ERROR | — | — | — | — | — | — | ERROR | — |")
            continue
        cap = "*" if r["capped"] else ""
        report.append(
            f"| `{r['table']}` | {r['rows_actual']}{cap} | {r['rows_full']} "
            f"| {r['n_cols']} | {r['bytes_raw']} | {r['bytes_tcf']} "
            f"| {r['delta_bytes']:+d} | {r['ratio_pct']:.1f}% "
            f"| {r['rt']} | {r['t_encode_ms']:.0f} |"
        )
    report.append("")
    report.append(f"`*` = capped a {MAX_ROWS} rows (tabela maior).")
    report.append("")
    report.append("## Totais (somando todas tabelas truncadas)")
    report.append("")
    report.append(f"- Raw total: {total_raw:,} B")
    report.append(f"- TCF total: {total_tcf:,} B  ({total_tcf-total_raw:+,d}, "
                  f"{total_tcf/total_raw*100:.1f}%)")
    report.append(f"- RT: {rt_pass}/{len(results)}")
    report.append("")

    report.append("## Stats per-coluna (orders se disponivel)")
    report.append("")
    r_orders = next((r for r in results if r.get("table") == "orders"), None)
    if r_orders and "per_col" in r_orders:
        report.append("| Coluna | det? | runs | uniq |")
        report.append("|---|---|---:|---:|")
        for p in r_orders["per_col"]:
            report.append(f"| `{p['col']}` | {p['cadence_detected']!s} "
                          f"| {p['n_seq_runs']} | {p['n_unicas']} |")
        report.append("")

    report.append("## Validacao")
    report.append("")
    if rt_pass == len(results):
        report.append("- ✓ RT 8/8 OK")
    else:
        report.append(f"- ⚠ RT {rt_pass}/{len(results)} OK")
    if all(r.get("ratio_pct", 100) < 100 for r in results if r.get("rt") == "OK"):
        report.append("- ✓ Todas tabelas tem TCF < raw CSV")
    report.append("")
    report.append("## Limitacoes")
    report.append("")
    report.append(f"- Tabelas maiores capadas em {MAX_ROWS} rows (encode O(N²))")
    report.append("- lineitem full (60k rows) nao testado")
    report.append("- order natural fixo")
    report.append("- shaper nao usado (DatasetReader.rows direto)")
    report.append("")
    write_lf(THIS / "report.md", "\n".join(report) + "\n")

    with (THIS / "manifest.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"\nreport.md: {THIS / 'report.md'}")
    print(f"Totais: raw={total_raw:,}  tcf={total_tcf:,}  "
          f"ratio={total_tcf/total_raw*100:.1f}%")
    print(f"RT: {rt_pass}/{len(results)}")


if __name__ == "__main__":
    main()
