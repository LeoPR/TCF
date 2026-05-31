"""Benchmark cap K + cap iter variants em lineitem 5k.

Mede:
- bytes vs baseline (byte loss)
- tempo
- RT

Saida: tabela em result.md.
"""

from __future__ import annotations

import csv
import io
import sys
import time
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
EXP_010 = ROOT / "experiments" / "lab" / "clean" / "EXP-010-tcf-delta-aware-prototype"
EXP_011 = ROOT / "experiments" / "lab" / "clean" / "EXP-011-multi-column-basic"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(EXP_010))
sys.path.insert(0, str(EXP_011))
sys.path.insert(0, str(THIS))

from dataset_reader import DatasetReader  # noqa: E402
from tcf import encode, decode  # noqa: E402
from multi_col import encode_table, decode_table  # noqa: E402
import hcc_opts_cap as cap  # noqa: E402


D1_D9 = [
    "D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
    "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
    "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta",
]


def ler_csv(path):
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def rows_to_cols(rows):
    if not rows:
        return {}
    return {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in rows[0].keys()}


def run_d1_d9():
    datasets_dir = ROOT / "datasets" / "synthetic"
    total = 0
    rt = 0
    for name in D1_D9:
        linhas = ler_csv(datasets_dir / f"{name}.csv")
        tcf = encode(linhas)
        total += len(tcf.encode("utf-8"))
        if decode(tcf) == linhas:
            rt += 1
    return {"bytes": total, "rt": rt}


def run_lineitem(volume, cached_cols=None):
    if cached_cols is None:
        reader = DatasetReader("tpch-sf001")
        rows = reader.rows("lineitem", limit=volume)
        reader.close()
        cols = rows_to_cols(rows)
    else:
        cols = cached_cols
    t0 = time.perf_counter()
    tcf, info = encode_table(cols)
    t_encode = time.perf_counter() - t0
    bytes_tcf = len(tcf.encode("utf-8"))
    decoded = decode_table(tcf)
    rt = (decoded == cols)
    return {
        "bytes": bytes_tcf,
        "t_encode": t_encode,
        "rt": rt,
    }


VARIANTS = [
    ("v0", None, None),       # baseline
    ("v3-K8", 8, None),
    ("v3-K6", 6, None),
    ("v3-K4", 4, None),
    ("v4-i50", None, 50),
    ("v4-i30", None, 30),
    ("v5-K6-i50", 6, 50),
    ("v5-K8-i50", 8, 50),
]


def main():
    print("=== HCC cap K + cap iter benchmark ===\n")

    # Cachear lineitem cols pra evitar re-read
    print("Loading lineitem 5k...")
    reader = DatasetReader("tpch-sf001")
    rows_5k = reader.rows("lineitem", limit=5000)
    reader.close()
    cols_5k = rows_to_cols(rows_5k)
    print(f"  loaded {len(rows_5k)} rows × {len(cols_5k)} cols\n")

    results = []
    for name, cK, cI in VARIANTS:
        print(f">> {name} (cap_K={cK}, cap_iter={cI})")
        if cK is None and cI is None:
            cap.unpatch()
        else:
            cap.patch(cap_K_max=cK, cap_iter_max=cI)

        d = run_d1_d9()
        li5k = run_lineitem(5000, cached_cols=cols_5k)
        results.append({
            "name": name, "cK": cK, "cI": cI,
            "d_bytes": d["bytes"], "d_rt": d["rt"],
            "li5k_bytes": li5k["bytes"], "li5k_t": li5k["t_encode"],
            "li5k_rt": li5k["rt"],
        })
        print(f"  D1-D9: {d['bytes']}B, RT={d['rt']}/9")
        print(f"  li5k: {li5k['bytes']:,}B, encode={li5k['t_encode']:.2f}s, RT={li5k['rt']}")
        cap.unpatch()

    # Tabela
    print("\n=== Resumo ===\n")
    v0 = results[0]
    print(f"{'variant':<14} {'D1-D9 bytes':>12} {'diff':>8} {'li5k bytes':>12} "
          f"{'loss %':>8} {'t (s)':>8} {'speedup':>8} {'RT':>4}")
    print("-" * 90)
    for r in results:
        d_diff = r["d_bytes"] - v0["d_bytes"]
        li_loss = (r["li5k_bytes"] - v0["li5k_bytes"]) / v0["li5k_bytes"] * 100
        speedup = v0["li5k_t"] / r["li5k_t"] if r["li5k_t"] > 0 else 0
        rt_str = "OK" if r["d_rt"] == 9 and r["li5k_rt"] else "FAIL"
        print(f"{r['name']:<14} {r['d_bytes']:>12,} {d_diff:>+8} "
              f"{r['li5k_bytes']:>12,} {li_loss:>+7.2f}% {r['li5k_t']:>7.2f}s "
              f"{speedup:>7.2f}x {rt_str:>4}")

    # Write result.md
    report = ["# Sub-exp 03 — cap K + cap iter (resultado)", ""]
    report.append("## Benchmark")
    report.append("")
    report.append("| variant | cap_K | cap_iter | D1-D9 bytes | diff | li5k bytes | loss | encode | speedup | RT |")
    report.append("|---|---|---|---:|---:|---:|---:|---:|---:|---|")
    for r in results:
        d_diff = r["d_bytes"] - v0["d_bytes"]
        li_loss = (r["li5k_bytes"] - v0["li5k_bytes"]) / v0["li5k_bytes"] * 100
        speedup = v0["li5k_t"] / r["li5k_t"] if r["li5k_t"] > 0 else 0
        rt_str = "OK" if r["d_rt"] == 9 and r["li5k_rt"] else "FAIL"
        cK_str = str(r["cK"]) if r["cK"] is not None else "-"
        cI_str = str(r["cI"]) if r["cI"] is not None else "-"
        report.append(
            f"| {r['name']} | {cK_str} | {cI_str} | "
            f"{r['d_bytes']:,} | {d_diff:+} | "
            f"{r['li5k_bytes']:,} | {li_loss:+.2f}% | "
            f"{r['li5k_t']:.2f}s | {speedup:.2f}x | {rt_str} |"
        )
    report.append("")
    report.append("## Analise")
    report.append("")
    report.append("Procurando: variante com speedup >= 2x e byte loss < 1%.")
    report.append("")
    report.append("D1-D9 deve ter byte diff = 0 (estruturas pequenas, todas iters fit).")
    report.append("li5k loss > 0 esperado quando cap_K reduz subs longas.")
    report.append("")
    report.append("*(preencher analise apos rodar)*")

    out_path = THIS / "result.md"
    out_path.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out_path}")


if __name__ == "__main__":
    main()
