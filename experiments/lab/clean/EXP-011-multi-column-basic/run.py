"""EXP-011 — valida multi-column basico em D17a.

Compara:
- multi-encoding: cada coluna independente
- single-encoding: concat tudo em 1 coluna gigante (controle)
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[3]
SRC = ROOT / "src"
EXP_010 = THIS.parent / "EXP-010-tcf-delta-aware-prototype"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(EXP_010))
sys.path.insert(0, str(THIS))

from delta_aware import encode_column, decode_column  # noqa: E402
from multi_col import encode_table, decode_table  # noqa: E402


def write_lf(path, content):
    if isinstance(content, str):
        content = content.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def load_csv(path):
    """Le CSV com header. Retorna dict[col, [vals]]."""
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for row in r:
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


def main():
    ds_path = ROOT / "datasets" / "synthetic" / "D17a-multi-column-mixed.csv"
    table = load_csv(ds_path)
    n_rows = len(next(iter(table.values())))
    n_cols = len(table)
    raw_bytes = ds_path.read_bytes()

    print("=== EXP-011 — multi-column basic ===\n")
    print(f"Dataset: D17a ({n_rows} rows, {n_cols} cols)")
    print(f"Raw CSV bytes: {len(raw_bytes)}\n")

    # 1. Multi-encoding
    multi_text, multi_info = encode_table(table)
    multi_bytes = len(multi_text.encode("utf-8"))

    # 2. Single-encoding (concat tudo em 1 coluna)
    flat_rows = []
    for i in range(n_rows):
        row = ",".join(table[col][i] for col in table)
        flat_rows.append(row)
    single_text, single_info = encode_column(flat_rows, header="all")
    single_bytes = len(single_text.encode("utf-8"))

    # 3. RT multi
    decoded_multi = decode_table(multi_text)
    rt_multi = (decoded_multi == table)

    # 4. RT single
    decoded_single = decode_column(single_text)
    rt_single = (decoded_single == flat_rows)

    print(f"Multi-encoding:   {multi_bytes:4} bytes  RT={'OK' if rt_multi else 'FAIL'}")
    for col, info in multi_info["col_info"].items():
        print(f"  col '{col:12}': det={info['cadence_detected']!s:5} "
              f"hint={info['hint_used']!s:5} runs={info['n_seq_runs']}")
    print(f"Single-encoding:  {single_bytes:4} bytes  RT={'OK' if rt_single else 'FAIL'}")
    print(f"Raw CSV:          {len(raw_bytes):4} bytes")
    print()
    print(f"multi vs single: {multi_bytes - single_bytes:+d} bytes "
          f"({(multi_bytes - single_bytes)/single_bytes*100:+.1f}%)")
    print(f"multi vs raw:    {multi_bytes - len(raw_bytes):+d} bytes "
          f"({(multi_bytes - len(raw_bytes))/len(raw_bytes)*100:+.1f}%)")

    # Outputs
    out_dir = THIS / "outputs"
    write_lf(out_dir / "D17a-multi.tcf", multi_text)
    write_lf(out_dir / "D17a-single.tcf", single_text)

    # Per-column inspection
    per_col = []
    for col_name, vals in table.items():
        body, info = encode_column(vals, header=col_name)
        per_col.append({
            "col": col_name,
            "bytes_body": len(body.encode("utf-8")),
            "n_unicas": info["n_unicas"],
            "cadence_detected": info["cadence_detected"],
            "hint_used": info["hint_used"],
            "n_seq_runs": info["n_seq_runs"],
        })

    # Report
    report = [
        "# EXP-011 — Multi-column basic (report)",
        "",
        f"Dataset: D17a-multi-column-mixed ({n_rows} rows, {n_cols} cols)",
        f"Raw CSV: {len(raw_bytes)} bytes",
        "",
        "## Resumo",
        "",
        f"- **multi-encoding** (per-coluna): {multi_bytes} bytes, "
        f"RT={'OK' if rt_multi else 'FAIL'}",
        f"- **single-encoding** (concat 1 coluna): {single_bytes} bytes, "
        f"RT={'OK' if rt_single else 'FAIL'}",
        f"- **raw CSV** (sem compressao): {len(raw_bytes)} bytes",
        "",
        f"multi vs single: {multi_bytes - single_bytes:+d} bytes "
        f"({(multi_bytes - single_bytes)/single_bytes*100:+.1f}%)",
        f"multi vs raw: {multi_bytes - len(raw_bytes):+d} bytes "
        f"({(multi_bytes - len(raw_bytes))/len(raw_bytes)*100:+.1f}%)",
        "",
        "## Por coluna",
        "",
        "| Coluna | uniq | det? | hint | runs | bytes (body, sem header) |",
        "|---|---:|---|---|---:|---:|",
    ]
    for p in per_col:
        report.append(f"| `{p['col']}` | {p['n_unicas']} | "
                      f"{p['cadence_detected']!s} | {p['hint_used']!s} | "
                      f"{p['n_seq_runs']} | {p['bytes_body']} |")
    report.extend([
        "",
        "## Validacao",
        "",
    ])
    if rt_multi and rt_single:
        report.append("✓ **RT OK**: ambos pipelines reconstroem exatos.")
    elif rt_multi:
        report.append("⚠ multi RT OK; single RT FAIL.")
    elif rt_single:
        report.append("⚠ single RT OK; multi RT FAIL.")
    else:
        report.append("✗ **AMBOS RT FAIL**.")
    report.append("")
    report.append("## Limitacoes")
    report.append("")
    report.append("- 1 dataset sintetico (D17a). Real-world (TPC-H, "
                  "Adult Census) NAO testado neste EXP.")
    report.append("- Sem ordering/cross-column (ver `futuras-otimizacoes-formato.md`).")
    report.append("- Header verboso (`# COL=name bytes=N`); otimizacao adiada.")
    report.append("")
    write_lf(THIS / "report.md", "\n".join(report) + "\n")
    print(f"\nreport.md: {THIS / 'report.md'}")

    # Manifest
    manifest = {
        "dataset": "D17a-multi-column-mixed",
        "n_rows": n_rows,
        "n_cols": n_cols,
        "raw_bytes": len(raw_bytes),
        "multi_bytes": multi_bytes,
        "single_bytes": single_bytes,
        "rt_multi": rt_multi,
        "rt_single": rt_single,
        "per_col": per_col,
    }
    write_lf(THIS / "manifest.jsonl", json.dumps(manifest) + "\n")


if __name__ == "__main__":
    main()
