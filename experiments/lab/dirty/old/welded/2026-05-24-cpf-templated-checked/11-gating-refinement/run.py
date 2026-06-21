"""Sub-exp 11 — Refinement do gating ADR-0010 (min_len heuristic).

Sub-exp 10 expos bug: ADR-0010 gating (n>=100 ativa heur v3) prejudica
IP subnet (M10 ratio 5.78% -> 68.17% entre 50 e 200 vals). Hipotese:
desativar gating quando cadence_detected=True com lengths variaveis.

Sub-exp 11 testa 3 variantes da heur min_len:
- M10 canonical (gating padrao): produto src/tcf atual
- A1 (bypass forcado): min_len=3 sempre
- A2 (smart gating): bypass apenas se cadence_detected + variable_length

Roda nos D-IP-subnet em N=50, 100, 200, 500, 1000 pra ver onde
transicao acontece.

Tambem roda em D-CPF-uniform pra garantir que A2 nao regrediu o caso
onde gating ATUALMENTE ajuda (controle).
"""

from __future__ import annotations

import csv
import json
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
LAB = THIS.parent
ROOT = LAB.parents[3]
sys.path.insert(0, str(ROOT / "src"))

from tcf import encode, decode, SideOutputs  # noqa: E402
from tcf.auto_cadence import detect_cadence_from_features  # noqa: E402
from tcf.auto_min_len import detect_min_len_from_features  # noqa: E402
from tcf.column_features import analyze_column  # noqa: E402
from tcf.composicional.hcc_seqrle import HCCSeqRLE  # noqa: E402
from tcf.core.online import processar  # noqa: E402
from tcf.obat_shape import processar_with_hint  # noqa: E402


def encode_with_strategy(values: list[str], strategy: str) -> tuple[str, dict]:
    """Pipeline customizado pra testar variantes do gating.

    strategy:
    - 'canonical': comportamento padrao src/tcf
    - 'no_gating': min_len=3 sempre (bypass)
    - 'smart_gating': bypass se cadence_detected + variable_length
    """
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())

    features = analyze_column(values)
    cadence_detected, cadence_info = detect_cadence_from_features(features, unicas)

    # Detect variable length nas primeiras N strings
    sample = unicas[:min(20, len(unicas))]
    lengths = set(len(s) for s in sample)
    variable_length = len(lengths) > 1

    if strategy == 'canonical':
        min_len = detect_min_len_from_features(features)
    elif strategy == 'no_gating':
        min_len = 3
    elif strategy == 'smart_gating':
        if cadence_detected and variable_length:
            min_len = 3  # bypass
        else:
            min_len = detect_min_len_from_features(features)
    else:
        raise ValueError(strategy)

    if cadence_detected:
        tokens, _ = processar_with_hint(
            unicas, min_len=min_len, prefer_shape_consistency=True
        )
        used_hint = True
    else:
        tokens, _ = processar(unicas, min_len=min_len)
        used_hint = False

    syn = HCCSeqRLE()
    text = syn.encode(values, unicas, tokens, "val")

    info = {
        "min_len": min_len,
        "cadence_detected": cadence_detected,
        "variable_length": variable_length,
        "obat_used_hint": used_hint,
        "lengths_sample": sorted(lengths),
        "seq_rle_runs": len(syn.get_seq_info()),
    }
    return text, info


def load(name: str, n: int) -> list[str]:
    path = LAB / "data" / f"{name}.csv"
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        rows = [row[0] if row else '' for row in r]
    return rows[:n]


def measure(dataset: str, n: int, strategy: str) -> dict:
    values = load(dataset, n)
    if not values:
        return {"dataset": dataset, "n": 0, "strategy": strategy}

    raw_bytes = sum(len(v.encode("utf-8")) for v in values) + len(values)
    text, info = encode_with_strategy(values, strategy)
    tcf_bytes = len(text.encode("utf-8"))

    decoded = decode(text)
    rt_ok = (decoded == values)

    out_dir = THIS / "out_tcf" / strategy
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{dataset}-n{n}.tcf").write_bytes(text.encode("utf-8"))

    return {
        "dataset": dataset,
        "n": n,
        "strategy": strategy,
        "raw_bytes": raw_bytes,
        "tcf_bytes": tcf_bytes,
        "ratio_pct": round(tcf_bytes / raw_bytes * 100, 2),
        "rt_ok": rt_ok,
        "min_len": info["min_len"],
        "cadence_detected": info["cadence_detected"],
        "variable_length": info["variable_length"],
        "lengths_sample": info["lengths_sample"],
        "seq_rle_runs": info["seq_rle_runs"],
    }


def main():
    print("=== Sub-exp 11 — ADR-0010 gating refinement ===\n")

    tasks = [
        # D-IP-subnet: dataset onde bug aparece
        ("D-IP-subnet", 50),
        ("D-IP-subnet", 100),
        ("D-IP-subnet", 200),
        ("D-IP-subnet", 500),
        ("D-IP-subnet", 1000),
        # D-CPF-uniform: dataset onde gating ATUALMENTE ajuda (controle)
        ("D-CPF-uniform", 50),
        ("D-CPF-uniform", 200),
        ("D-CPF-uniform", 1000),
        # D-IP-uniform: random sem cadence
        ("D-IP-uniform", 200),
        ("D-IP-uniform", 1000),
    ]
    strategies = ['canonical', 'no_gating', 'smart_gating']

    print(f"{'dataset':18s} {'n':>5} {'strategy':14s} "
          f"{'min':>4} {'cad':>4} {'varlen':>6} {'tcf':>9} {'ratio':>7} {'rt':>3}")
    print("-" * 95)
    all_results = []
    for dataset, n in tasks:
        for strategy in strategies:
            r = measure(dataset, n, strategy)
            all_results.append(r)
            cad = 'Y' if r['cadence_detected'] else 'n'
            vl = 'Y' if r['variable_length'] else 'n'
            rt = 'OK' if r['rt_ok'] else 'FAIL'
            print(f"{dataset:18s} {n:>5} {strategy:14s} "
                  f"{r['min_len']:>4} {cad:>4} {vl:>6} "
                  f"{r['tcf_bytes']:>9} {r['ratio_pct']:>6.2f}% {rt:>3}")
        print()

    out = THIS / "manifest.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in all_results) + "\n",
                   encoding="utf-8")

    # Comparacao por dataset/n: vencedor entre estrategias
    print("Vencedor por (dataset, n):")
    by_key = {}
    for r in all_results:
        key = (r['dataset'], r['n'])
        by_key.setdefault(key, []).append(r)
    for (ds, n), results in by_key.items():
        winner = min(results, key=lambda x: x['tcf_bytes'])
        print(f"  {ds:18s} n={n:>5}: {winner['strategy']:14s} "
              f"({winner['tcf_bytes']}B, {winner['ratio_pct']}%)")

    # Avaliacao smart_gating
    print("\nAvaliacao smart_gating:")
    for (ds, n), results in by_key.items():
        canonical = next(r for r in results if r['strategy'] == 'canonical')
        smart = next(r for r in results if r['strategy'] == 'smart_gating')
        delta = smart['tcf_bytes'] - canonical['tcf_bytes']
        delta_pct = (delta / canonical['tcf_bytes'] * 100) if canonical['tcf_bytes'] > 0 else 0
        verdict = "BETTER" if delta < 0 else ("WORSE" if delta > 0 else "EQUAL")
        print(f"  {ds:18s} n={n:>5}: smart vs canonical = {delta:+d}B "
              f"({delta_pct:+.2f}%) {verdict}")

    print(f"\nManifest: {out}")
    print(f"Outputs:  {THIS / 'out_tcf'}/")


if __name__ == "__main__":
    main()
