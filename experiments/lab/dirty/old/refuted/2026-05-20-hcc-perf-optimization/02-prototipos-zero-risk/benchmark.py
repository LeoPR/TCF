"""Benchmark HCC opts v0/v1/v2.

Para cada variante, roda encode_table em:
- D1-D9 (single-col via tcf.encode)
- lineitem 1k, 5k (multi-col)

Compara bytes (deve ser IDENTICOS) + tempo.
"""

from __future__ import annotations

import csv
import io
import sys
import time
from collections import OrderedDict
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
import hcc_opts  # noqa: E402


D1_D9 = [
    "D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
    "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
    "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta",
]


def ler_csv(path: Path):
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
    total_bytes = 0
    rt_count = 0
    t0 = time.perf_counter()
    for name in D1_D9:
        linhas = ler_csv(datasets_dir / f"{name}.csv")
        tcf = encode(linhas)
        bytes_n = len(tcf.encode("utf-8"))
        decoded = decode(tcf)
        if decoded == linhas:
            rt_count += 1
        total_bytes += bytes_n
    t = time.perf_counter() - t0
    return {"bytes": total_bytes, "rt": rt_count, "time": t}


def run_lineitem(volume):
    reader = DatasetReader("tpch-sf001")
    rows = reader.rows("lineitem", limit=volume)
    reader.close()
    cols = rows_to_cols(rows)
    t0 = time.perf_counter()
    tcf, info = encode_table(cols)
    t_encode = time.perf_counter() - t0
    bytes_tcf = len(tcf.encode("utf-8"))
    t1 = time.perf_counter()
    decoded = decode_table(tcf)
    t_decode = time.perf_counter() - t1
    rt = (decoded == cols)
    return {
        "volume": volume,
        "bytes": bytes_tcf,
        "t_encode": t_encode,
        "t_decode": t_decode,
        "rt": rt,
    }


def main():
    print("=== HCC opts benchmark ===\n")

    results = {}

    # Run baseline (v0)
    print(">> v0 baseline\n")
    hcc_opts.unpatch()  # garantir limpo
    results["v0"] = {
        "d1_d9": run_d1_d9(),
        "li1k": run_lineitem(1000),
        "li5k": run_lineitem(5000),
    }
    for k, v in results["v0"].items():
        print(f"  {k}: {v}")

    # Run v1 (estimate baseline counting)
    print("\n>> v1 (_estimate_baseline_chars counting direto)\n")
    hcc_opts.patch_v1()
    results["v1"] = {
        "d1_d9": run_d1_d9(),
        "li1k": run_lineitem(1000),
        "li5k": run_lineitem(5000),
    }
    for k, v in results["v1"].items():
        print(f"  {k}: {v}")
    hcc_opts.unpatch()

    # Run v2 (v1 + skip trace/rede)
    print("\n>> v2 (+ skip _build_trace/_build_rede)\n")
    hcc_opts.patch_v2()
    results["v2"] = {
        "d1_d9": run_d1_d9(),
        "li1k": run_lineitem(1000),
        "li5k": run_lineitem(5000),
    }
    for k, v in results["v2"].items():
        print(f"  {k}: {v}")
    hcc_opts.unpatch()

    # Compare
    print("\n=== Comparison ===\n")
    print(f"  D1-D9 bytes (esperado 1615):")
    for variant in ["v0", "v1", "v2"]:
        d = results[variant]["d1_d9"]
        match = "OK" if d["bytes"] == 1615 else f"DIVERGE ({d['bytes']})"
        print(f"    {variant}: {d['bytes']}B, RT={d['rt']}/9, time={d['time']*1000:.0f}ms ({match})")

    for case in ["li1k", "li5k"]:
        print(f"\n  {case} bytes + tempo:")
        for variant in ["v0", "v1", "v2"]:
            d = results[variant][case]
            print(f"    {variant}: bytes={d['bytes']:,}, encode={d['t_encode']:.2f}s, "
                  f"decode={d['t_decode']*1000:.0f}ms, RT={d['rt']}")

        # Speedup vs v0
        v0_t = results["v0"][case]["t_encode"]
        for variant in ["v1", "v2"]:
            v_t = results[variant][case]["t_encode"]
            speedup = v0_t / v_t if v_t > 0 else 0
            bytes_match = results[variant][case]["bytes"] == results["v0"][case]["bytes"]
            print(f"      {variant} speedup: {speedup:.2f}x  bytes_match: {bytes_match}")

    # Validacao final
    print("\n=== VALIDACAO ===")
    v0_d = results["v0"]["d1_d9"]["bytes"]
    fail = []
    for variant in ["v1", "v2"]:
        d_match = results[variant]["d1_d9"]["bytes"] == v0_d
        l1k_match = results[variant]["li1k"]["bytes"] == results["v0"]["li1k"]["bytes"]
        l5k_match = results[variant]["li5k"]["bytes"] == results["v0"]["li5k"]["bytes"]
        rt_d = results[variant]["d1_d9"]["rt"]
        rt_l1k = results[variant]["li1k"]["rt"]
        rt_l5k = results[variant]["li5k"]["rt"]
        ok = d_match and l1k_match and l5k_match and rt_d == 9 and rt_l1k and rt_l5k
        status = "OK" if ok else "FAIL"
        print(f"  {variant}: {status}")
        if not ok:
            fail.append(variant)

    return results, fail


if __name__ == "__main__":
    main()
