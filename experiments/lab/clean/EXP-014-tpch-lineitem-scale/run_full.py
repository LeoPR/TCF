"""EXP-014 — lineitem FULL (60175 rows).

Confirma extrapolacao do run.py (~18.5min) com pipeline pos-ADR-0009.

Output: report_full.md + manifest_full.jsonl ao lado de report.md original.
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


VOLUME = 60175
ENCODE_TIME_CAP_SEC = 1800  # 30 min de margem (estimado 18.5 min)


def write_lf(path, content):
    if isinstance(content, str):
        content = content.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def rows_to_cols(rows):
    if not rows:
        return {}
    return {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in rows[0].keys()}


def table_to_csv_bytes(cols):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    cs = list(cols.keys())
    w.writerow(cs)
    n = len(next(iter(cols.values())))
    for i in range(n):
        w.writerow([cols[c][i] for c in cs])
    return buf.getvalue().encode("utf-8")


def main():
    print(f"=== EXP-014 FULL — lineitem {VOLUME} rows ===")
    print(f"Cap encode time: {ENCODE_TIME_CAP_SEC}s ({ENCODE_TIME_CAP_SEC/60:.0f} min)")
    print(f"Extrapolacao baseline (pos-ADR-0009): 18.5 min")

    reader = DatasetReader("tpch-sf001")

    t0 = time.perf_counter()
    rows = reader.rows("lineitem", limit=VOLUME)
    reader.close()
    cols = rows_to_cols(rows)
    t_read = time.perf_counter() - t0
    print(f"\nReading: {t_read:.1f}s — {len(rows)} rows × {len(cols)} cols")

    t1 = time.perf_counter()
    raw = table_to_csv_bytes(cols)
    t_csv = time.perf_counter() - t1
    print(f"CSV serialize: {t_csv:.2f}s — raw bytes: {len(raw):,}")

    print(f"\nEncoding... (esperado ~18.5 min)")
    t2 = time.perf_counter()
    tcf, info = encode_table(cols)
    t_encode = time.perf_counter() - t2
    bytes_tcf = len(tcf.encode("utf-8"))
    print(f"Encode: {t_encode:.1f}s ({t_encode/60:.1f} min)")
    print(f"  bytes_tcf: {bytes_tcf:,}  ratio: {bytes_tcf/len(raw)*100:.1f}%")

    t3 = time.perf_counter()
    decoded = decode_table(tcf)
    t_decode = time.perf_counter() - t3
    rt_ok = (decoded == cols)
    print(f"Decode: {t_decode:.2f}s  RT: {'OK' if rt_ok else 'FAIL'}")

    write_lf(THIS / "outputs" / f"lineitem-vol-{VOLUME}.tcf", tcf)

    cad = sum(1 for ci in info["col_info"].values() if ci["cadence_detected"])

    result = {
        "volume": VOLUME,
        "rows": len(rows),
        "n_cols": info["n_cols"],
        "bytes_raw": len(raw),
        "bytes_tcf": bytes_tcf,
        "ratio_pct": bytes_tcf / len(raw) * 100,
        "t_read_s": t_read,
        "t_encode_s": t_encode,
        "t_decode_s": t_decode,
        "rt": "OK" if rt_ok else "FAIL",
        "cadence_detected": cad,
    }

    # Validacao vs extrapolacao
    estimated = 18.5 * 60  # 18.5 min em segundos
    diff_pct = (t_encode - estimated) / estimated * 100

    report = [
        "# EXP-014 FULL — lineitem 60175 (report)",
        "",
        "## Resumo executivo",
        "",
        f"- **Encode**: {t_encode:.0f}s ({t_encode/60:.1f} min)",
        f"- **Estimativa pos-ADR-0009**: 1110s (18.5 min) — diff {diff_pct:+.0f}%",
        f"- **Bytes**: {bytes_tcf:,} / {len(raw):,} ({bytes_tcf/len(raw)*100:.1f}%)",
        f"- **Decode**: {t_decode:.2f}s",
        f"- **RT**: {'OK' if rt_ok else 'FAIL'}",
        f"- **Cadence detected**: {cad}/{info['n_cols']} colunas",
        "",
        "## Tabela",
        "",
        "| volume | rows | raw (B) | TCF (B) | ratio | encode (s) | encode (min) | decode (s) | RT | cad/16 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|",
        f"| {VOLUME} | {len(rows)} | {len(raw):,} | {bytes_tcf:,} | "
        f"{bytes_tcf/len(raw)*100:.1f}% | {t_encode:.1f} | {t_encode/60:.1f} | "
        f"{t_decode:.2f} | {'OK' if rt_ok else 'FAIL'} | {cad}/{info['n_cols']} |",
        "",
        "## Comparacao com volumes anteriores (do report.md original)",
        "",
        "| volume | encode (s) | tempo por 1k rows |",
        "|---:|---:|---:|",
        "| 1000 | 7.9 | 7.9ms |",
        "| 5000 | 40.5 | 8.1ms |",
        "| 10000 | 86.6 | 8.7ms |",
        "| 20000 | 232.0 | 11.6ms |",
        f"| **{VOLUME}** | **{t_encode:.1f}** | **{t_encode*1000/VOLUME:.1f}ms** |",
        "",
        "## Validacao extrapolacao",
        "",
        f"- Extrapolacao do run.py (alpha=1.42 fit em 10k+20k): 1110s (18.5 min)",
        f"- Real medido: {t_encode:.0f}s ({t_encode/60:.1f} min)",
        f"- Diff: {diff_pct:+.0f}%",
        "",
    ]
    if diff_pct < 35:
        report.append("**Aceite OK** (margem 35% sobre extrapolacao). H-RW-05 mitigada confirmada.")
    else:
        report.append(f"**Aceite NEGATIVO** ({diff_pct:+.0f}% acima da extrapolacao). Investigar.")

    write_lf(THIS / "report_full.md", "\n".join(report) + "\n")
    with (THIS / "manifest_full.jsonl").open("w", encoding="utf-8") as f:
        f.write(json.dumps(result) + "\n")

    print(f"\nreport_full.md: {THIS / 'report_full.md'}")


if __name__ == "__main__":
    main()
