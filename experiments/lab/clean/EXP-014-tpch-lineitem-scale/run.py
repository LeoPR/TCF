"""EXP-014 — performance scale lineitem.

Volumes progressivos. Para de rodar se encode passar de N segundos
(cap configuravel) pra evitar travamento.
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


VOLUMES = [1000, 5000, 10000, 20000]
ENCODE_TIME_CAP_SEC = 900  # 15 min — abort se passar disso


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


def process(reader, volume):
    print(f"\n--- volume={volume} ---")
    t0 = time.perf_counter()
    rows = reader.rows("lineitem", limit=volume)
    cols = rows_to_cols(rows)
    t_read = time.perf_counter() - t0

    t1 = time.perf_counter()
    raw = table_to_csv_bytes(cols)
    t_csv = time.perf_counter() - t1

    print(f"  reading + csv: {(t_read+t_csv)*1000:.0f}ms")
    print(f"  raw bytes: {len(raw):,}")

    t2 = time.perf_counter()
    tcf, info = encode_table(cols)
    t_encode = time.perf_counter() - t2
    bytes_tcf = len(tcf.encode("utf-8"))

    print(f"  encode: {t_encode:.1f}s  bytes_tcf: {bytes_tcf:,}  "
          f"ratio: {bytes_tcf/len(raw)*100:.1f}%")

    t3 = time.perf_counter()
    decoded = decode_table(tcf)
    t_decode = time.perf_counter() - t3
    rt_ok = (decoded == cols)
    print(f"  decode: {t_decode*1000:.0f}ms  RT: {'OK' if rt_ok else 'FAIL'}")

    write_lf(THIS / "outputs" / f"lineitem-vol-{volume}.tcf", tcf)

    cad = sum(1 for ci in info["col_info"].values() if ci["cadence_detected"])

    return {
        "volume": volume,
        "rows": len(rows),
        "n_cols": info["n_cols"],
        "bytes_raw": len(raw),
        "bytes_tcf": bytes_tcf,
        "ratio_pct": bytes_tcf / len(raw) * 100,
        "t_encode_s": t_encode,
        "t_decode_s": t_decode,
        "rt": "OK" if rt_ok else "FAIL",
        "cadence_detected": cad,
    }


def main():
    print(f"=== EXP-014 — lineitem performance scale ===")
    print(f"Cap encode time: {ENCODE_TIME_CAP_SEC}s")
    print(f"Volumes: {VOLUMES}")

    reader = DatasetReader("tpch-sf001")
    results = []

    for v in VOLUMES:
        try:
            r = process(reader, v)
            results.append(r)
            if r["t_encode_s"] > ENCODE_TIME_CAP_SEC * 0.8:
                print(f"\nWARN: encode em {r['t_encode_s']:.0f}s — proximo do cap")
                print("Pulando volumes maiores. Use extrapolacao pra 60k.")
                break
        except Exception as e:
            print(f"\nERROR vol={v}: {e!r}")
            results.append({"volume": v, "rt": "ERROR", "error": str(e)})
            break

    reader.close()

    # Extrapolation pra 60175 baseado em quadratic fit
    if len(results) >= 2:
        valid = [r for r in results if "t_encode_s" in r]
        if valid:
            v1, v2 = valid[-2:] if len(valid) >= 2 else (valid[0], valid[0])
            # Fit T = k * N^alpha (log-linear regression on 2 points)
            import math
            if v1["volume"] != v2["volume"]:
                alpha = math.log(v2["t_encode_s"] / v1["t_encode_s"]) / math.log(v2["volume"] / v1["volume"])
                k = v2["t_encode_s"] / (v2["volume"] ** alpha)
                t_60k_est = k * (60175 ** alpha)
                t_60k_min = t_60k_est / 60
                print(f"\nExtrapolacao pra 60175 (lineitem full): {t_60k_est:.0f}s ({t_60k_min:.1f} min)")
                print(f"  Alpha (escala T ~ N^alpha): {alpha:.2f}")

    # Report
    report = ["# EXP-014 — lineitem scale (report)", ""]
    report.append("## Tabela")
    report.append("")
    report.append("| volume | rows | raw (B) | TCF (B) | ratio | encode (s) | decode (s) | RT | cad/16 |")
    report.append("|---:|---:|---:|---:|---:|---:|---:|---|---:|")
    for r in results:
        if r.get("rt") == "ERROR":
            report.append(f"| {r['volume']} | ERROR | — | — | — | — | — | ERROR | — |")
            continue
        report.append(
            f"| {r['volume']} | {r['rows']} | {r['bytes_raw']:,} | "
            f"{r['bytes_tcf']:,} | {r['ratio_pct']:.1f}% | "
            f"{r['t_encode_s']:.1f} | {r['t_decode_s']:.2f} | "
            f"{r['rt']} | {r['cadence_detected']}/16 |"
        )
    report.append("")
    if len(results) >= 2:
        valid = [r for r in results if "t_encode_s" in r]
        if len(valid) >= 2:
            v1, v2 = valid[-2:]
            if v1["volume"] != v2["volume"]:
                import math
                alpha = math.log(v2["t_encode_s"] / v1["t_encode_s"]) / math.log(v2["volume"] / v1["volume"])
                k = v2["t_encode_s"] / (v2["volume"] ** alpha)
                t_60k_est = k * (60175 ** alpha)
                report.append("## Extrapolacao")
                report.append("")
                report.append(f"Fit em ultimos 2 pontos: `T = k * N^{alpha:.2f}`")
                report.append(f"- alpha = {alpha:.2f}  (1.0 = linear, 2.0 = quadratic)")
                report.append(f"- estimativa lineitem full (60175): **{t_60k_est:.0f}s ({t_60k_est/60:.1f} min)**")
                report.append("")
    write_lf(THIS / "report.md", "\n".join(report) + "\n")

    with (THIS / "manifest.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"\nreport.md: {THIS / 'report.md'}")


if __name__ == "__main__":
    main()
