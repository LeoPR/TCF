"""EXP-012 — real-world test em Adult Census via shaper.

Carrega Adult Census via shaper em multiplos volumes; aplica pipeline
EXP-011 (encode_table); mede bytes + RT.
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
from shaper import Shaper, ShapeRequest  # noqa: E402
from multi_col import encode_table, decode_table  # noqa: E402


VOLUMES = [100, 500, 1000, 5000]


def write_lf(path, content):
    if isinstance(content, str):
        content = content.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def table_to_csv_bytes(table_dict: dict[str, list[str]]) -> bytes:
    """Converte dict[col, rows] → raw CSV bytes (com header) pra comparativo."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    cols = list(table_dict.keys())
    w.writerow(cols)
    n = len(next(iter(table_dict.values())))
    for i in range(n):
        w.writerow([table_dict[c][i] for c in cols])
    return buf.getvalue().encode("utf-8")


def shape_to_table(result) -> dict[str, list[str]]:
    """Converte ShapeResult.tables['adult'] (list[dict]) -> dict[col, list[str]].

    Missing values (None) → "" (string vazia, preservada).
    Bug empty-string em HCC canonical fixado 2026-05-18 (ADR-0006).
    """
    rows = result.tables["adult"]
    if not rows:
        return {}
    cols = list(rows[0].keys())
    return {c: [str(r[c]) if r[c] is not None else "" for r in rows] for c in cols}


def run_one(volume: int) -> dict:
    print(f"\n--- volume={volume} ---")
    t0 = time.perf_counter()

    req = ShapeRequest(
        dataset="adult-census",
        volume=volume,
        order="natural",
        seed=42,
    )
    result = Shaper().apply(req)
    table = shape_to_table(result)
    t_shape = time.perf_counter() - t0

    raw_csv = table_to_csv_bytes(table)

    t1 = time.perf_counter()
    tcf_text, info = encode_table(table)
    t_encode = time.perf_counter() - t1

    t2 = time.perf_counter()
    decoded = decode_table(tcf_text)
    t_decode = time.perf_counter() - t2
    rt_ok = (decoded == table)

    bytes_raw = len(raw_csv)
    bytes_tcf = len(tcf_text.encode("utf-8"))
    actual_rows = info["n_rows"]
    n_cols = info["n_cols"]

    out_dir = THIS / "outputs"
    write_lf(out_dir / f"adult-vol-{volume}.tcf", tcf_text)

    # Stats per coluna
    per_col = []
    for col, ci in info["col_info"].items():
        per_col.append({
            "col": col,
            "cadence_detected": ci["cadence_detected"],
            "hint_used": ci["hint_used"],
            "n_seq_runs": ci["n_seq_runs"],
            "n_unicas": ci["n_unicas"],
        })

    print(f"  rows={actual_rows} cols={n_cols}")
    print(f"  raw={bytes_raw}  tcf={bytes_tcf}  ratio={bytes_tcf/bytes_raw*100:.1f}%")
    print(f"  RT={'OK' if rt_ok else 'FAIL'}  encode={t_encode*1000:.0f}ms "
          f"decode={t_decode*1000:.0f}ms shape={t_shape*1000:.0f}ms")
    cad = sum(1 for p in per_col if p["cadence_detected"])
    print(f"  cadence detected em {cad}/{n_cols} colunas")

    return {
        "volume_requested": volume,
        "rows_actual": actual_rows,
        "n_cols": n_cols,
        "bytes_raw": bytes_raw,
        "bytes_tcf": bytes_tcf,
        "ratio_pct": bytes_tcf / bytes_raw * 100,
        "delta_bytes": bytes_tcf - bytes_raw,
        "rt": "OK" if rt_ok else "FAIL",
        "t_shape_ms": t_shape * 1000,
        "t_encode_ms": t_encode * 1000,
        "t_decode_ms": t_decode * 1000,
        "per_col": per_col,
    }


def main():
    print("=== EXP-012 — Real-world test Adult Census via shaper ===")
    print(f"Volumes: {VOLUMES}")

    results = []
    for vol in VOLUMES:
        try:
            r = run_one(vol)
            results.append(r)
        except Exception as e:
            print(f"  ERROR vol={vol}: {e!r}")
            results.append({"volume_requested": vol, "rt": "ERROR", "error": str(e)})

    # Report
    report = [
        "# EXP-012 — Real-world Adult Census (report)",
        "",
        "## Resumo (variando volume)",
        "",
        "| Vol req | rows | cols | raw (B) | TCF (B) | TCF/raw | ratio | RT | enc ms | dec ms |",
        "|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|",
    ]
    for r in results:
        if r.get("rt") == "ERROR":
            report.append(f"| {r['volume_requested']} | — | — | — | — | — | — | ERROR | — | — |")
            continue
        report.append(
            f"| {r['volume_requested']} | {r['rows_actual']} | {r['n_cols']} "
            f"| {r['bytes_raw']} | {r['bytes_tcf']} "
            f"| {r['delta_bytes']:+d} | {r['ratio_pct']:.1f}% "
            f"| {r['rt']} | {r['t_encode_ms']:.0f} | {r['t_decode_ms']:.0f} |"
        )
    report.append("")
    report.append("## Stats per coluna (vol=1000)")
    report.append("")
    r1k = next((r for r in results if r.get("volume_requested") == 1000), None)
    if r1k and "per_col" in r1k:
        report.append("| Coluna | det? | hint | runs | uniq |")
        report.append("|---|---|---|---:|---:|")
        for p in r1k["per_col"]:
            report.append(f"| `{p['col']}` | {p['cadence_detected']!s} "
                          f"| {p['hint_used']!s} | {p['n_seq_runs']} "
                          f"| {p['n_unicas']} |")
        report.append("")
    report.append("## Validacao")
    report.append("")
    rt_pass = sum(1 for r in results if r.get("rt") == "OK")
    report.append(f"- RT OK: {rt_pass}/{len(results)}")
    if rt_pass == len(results):
        report.append("- ✓ Todos volumes RT byte-canonical OK")
    elif rt_pass > 0:
        report.append("- ⚠ Alguns volumes falharam RT")
    else:
        report.append("- ✗ Nenhum RT OK")
    report.append("")
    report.append("## Limitacoes")
    report.append("")
    report.append("- 1 dataset real (Adult Census). TPC-H pendente.")
    report.append("- 4 volumes amostrados. Full 48k nao testado.")
    report.append("- order=natural fixo; outras orderings nao testadas.")
    report.append("")
    write_lf(THIS / "report.md", "\n".join(report) + "\n")

    # Manifest
    manifest_path = THIS / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"\nreport.md: {THIS / 'report.md'}")
    print(f"manifest.jsonl: {manifest_path}")


if __name__ == "__main__":
    main()
