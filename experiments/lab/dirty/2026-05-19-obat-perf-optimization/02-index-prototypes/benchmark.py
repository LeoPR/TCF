"""Benchmark v0/v1/v2/v3 — correctness + perf.

Correctness: tokens IDENTICOS entre versoes em:
- D1-D9 (sinteticos)
- lineitem 1000 rows (real-world subset, por coluna)

Perf: tempo de encode em:
- lineitem 5000 rows, coluna mais cara (l_comment, normalmente)
- Subset reduzido: l_comment 5000 ja' tem encode ~10-30s no v0
"""

from __future__ import annotations

import sys
import time
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SCRIPTS = ROOT / "scripts"
DATASETS_SYN = ROOT / "datasets" / "synthetic"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(THIS))

from dataset_reader import DatasetReader  # noqa: E402

import obat_v0_baseline as v0  # noqa: E402
import obat_v1_len_elim as v1  # noqa: E402
import obat_v2_hash_pref as v2  # noqa: E402
import obat_v3_hash_pref_suf as v3  # noqa: E402


VARIANTS = [
    ("v0", v0.processar),
    ("v1", v1.processar),
    ("v2", v2.processar),
    ("v3", v3.processar),
]


def dedup_preserve_order(values):
    seen = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def read_csv_column(path: Path):
    """Le csv simples (sem ',' nos valores). Retorna lista de strings
    excluindo header."""
    import csv
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return []
    # Pega todas as colunas concatenadas pra ter mais variedade
    out = []
    for r in rows[1:]:
        out.extend(r)
    return out


def tokens_repr(toks_list):
    """Repr canonica pra comparacao."""
    out = []
    for col_toks in toks_list:
        out.append(tuple(repr(t) for t in col_toks))
    return tuple(out)


def test_correctness(name, strings):
    """Roda todas variantes, compara tokens com v0."""
    unicas = dedup_preserve_order(strings)
    print(f"  {name}: {len(strings)} rows, {len(unicas)} unicas")
    if len(unicas) <= 1:
        print(f"    skip (insuficiente)")
        return None

    results = {}
    for vname, vprocessar in VARIANTS:
        t0 = time.perf_counter()
        toks, _ = vprocessar(unicas, min_len=3)
        t = time.perf_counter() - t0
        results[vname] = {"tokens": toks, "time": t}

    ref = tokens_repr(results["v0"]["tokens"])
    out = {"name": name, "n_rows": len(strings), "n_unicas": len(unicas)}
    for vname in ["v0", "v1", "v2", "v3"]:
        toks_rep = tokens_repr(results[vname]["tokens"])
        ok = (toks_rep == ref)
        out[vname] = {"time": results[vname]["time"], "ok": ok}
        if not ok:
            # Diagnostico
            for i, (a, b) in enumerate(zip(toks_rep, ref)):
                if a != b:
                    print(f"    {vname} DIVERGENCE at string idx {i}:")
                    print(f"      v0:    {b}")
                    print(f"      {vname}: {a}")
                    break
    return out


def fmt_time(t):
    if t < 0.01:
        return f"{t*1000:.2f}ms"
    if t < 1:
        return f"{t*1000:.0f}ms"
    return f"{t:.1f}s"


def print_table(rows):
    print()
    print(f"  {'name':<30} {'n_unicas':>8}  {'v0':>10} {'v1':>10} {'v2':>10} {'v3':>10}  RT")
    print(f"  {'-'*30} {'-'*8}  {'-'*10} {'-'*10} {'-'*10} {'-'*10}  --")
    for r in rows:
        if r is None:
            continue
        rt = "OK" if all(r[v]["ok"] for v in ["v0", "v1", "v2", "v3"]) else "FAIL"
        print(
            f"  {r['name']:<30} {r['n_unicas']:>8}  "
            f"{fmt_time(r['v0']['time']):>10} "
            f"{fmt_time(r['v1']['time']):>10} "
            f"{fmt_time(r['v2']['time']):>10} "
            f"{fmt_time(r['v3']['time']):>10}  {rt}"
        )


def main():
    print("=== Benchmark correctness (D1-D9 sinteticos) ===")
    syn_results = []
    for i in range(1, 10):
        for path in DATASETS_SYN.glob(f"D{i}-*.csv"):
            strings = read_csv_column(path)
            r = test_correctness(path.stem, strings)
            syn_results.append(r)
    print_table(syn_results)

    print("\n=== Benchmark correctness (lineitem 1000 rows, per-col) ===")
    reader = DatasetReader("tpch-sf001")
    rows = reader.rows("lineitem", limit=1000)
    cols = {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in rows[0].keys()}
    li1k_results = []
    for cname, cvals in cols.items():
        r = test_correctness(f"lineitem.{cname}", cvals)
        li1k_results.append(r)
    print_table(li1k_results)

    print("\n=== Benchmark perf (lineitem 5000 rows, per-col) ===")
    rows5k = reader.rows("lineitem", limit=5000)
    cols5k = {c: [str(r[c]) if r[c] is not None else "" for r in rows5k]
              for c in rows5k[0].keys()}
    li5k_results = []
    # Pega so colunas com unicas > 100 (onde perf importa)
    for cname, cvals in cols5k.items():
        unicas = dedup_preserve_order(cvals)
        if len(unicas) < 100:
            continue
        r = test_correctness(f"lineitem5k.{cname}", cvals)
        li5k_results.append(r)
    print_table(li5k_results)
    reader.close()

    # Summary
    print("\n=== Summary ===")
    all_results = [r for r in (syn_results + li1k_results + li5k_results) if r]
    total_rt = sum(1 for r in all_results
                   if all(r[v]["ok"] for v in ["v0", "v1", "v2", "v3"]))
    print(f"RT: {total_rt}/{len(all_results)}")

    # Speedup em lineitem5k
    print("\n  Speedup vs v0 (lineitem 5k, weighted by v0 time):")
    for vname in ["v1", "v2", "v3"]:
        total_v0 = sum(r["v0"]["time"] for r in li5k_results)
        total_v = sum(r[vname]["time"] for r in li5k_results)
        if total_v > 0:
            print(f"    {vname}: v0={total_v0:.1f}s, {vname}={total_v:.1f}s, "
                  f"speedup={total_v0/total_v:.1f}x")


if __name__ == "__main__":
    main()
