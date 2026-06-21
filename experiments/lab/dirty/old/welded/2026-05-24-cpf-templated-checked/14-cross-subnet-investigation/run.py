"""Sub-exp 14 — Investigacao empirica: por que M10 detecta poucos seq-RLE
runs em D-IP-subnet 1000?

Sub-exp 08 reportou seq_rle_runs=2 em D-IP-subnet 1000 vals (M10 puro,
ratio 117%). Mas estrutura sugere ate' 20 runs possiveis (10 subnets x
2 runs cada por length-break em octet 9->10).

Hipoteses pra investigar:
H1: HCC M8A transforma body de forma que seq-RLE nao acha pares
H2: Compare_for_seq fica confuso com HCC refs vs literais
H3: Algum outro mecanismo no pipeline impede detection

Plan:
1. Carregar D-IP-subnet, varios tamanhos (50, 100, 200, 500, 1000)
2. Encode via M8A SEM seq-RLE (super-class de HCCSeqRLE)
3. Inspecionar body lines apos M8A
4. Aplicar seq-RLE compact_body manualmente, contar runs
5. Comparar com HCCSeqRLE end-to-end (M10 standard)
6. Dump tudo pra inspecionar visualmente
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

from tcf.auto_cadence import detect_cadence_from_features  # noqa: E402
from tcf.auto_min_len import detect_min_len_from_features  # noqa: E402
from tcf.column_features import analyze_column  # noqa: E402
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.composicional.hcc_seqrle import (  # noqa: E402
    HCCSeqRLE, compact_body, detect_seq_runs, find_escape_digit_runs,
)
from tcf.core.online import processar  # noqa: E402
from tcf.obat_shape import processar_with_hint  # noqa: E402


def load_ips(n: int) -> list[str]:
    path = LAB / "data" / "D-IP-subnet.csv"
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] if row else '' for row in r][:n]


def get_m8a_body(values: list[str]) -> str:
    """Pipeline M10 ate' M8A (sem seq-RLE)."""
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())
    features = analyze_column(values)
    cadence_detected, _ = detect_cadence_from_features(features, unicas)
    min_len = detect_min_len_from_features(features)
    if cadence_detected:
        tokens, _ = processar_with_hint(unicas, min_len=min_len,
                                         prefer_shape_consistency=True)
    else:
        tokens, _ = processar(unicas, min_len=min_len)
    m8a = M8AVirtualRefsSyntax()
    return m8a.encode(values, unicas, tokens, "val")


def investigate_n(n: int) -> dict:
    values = load_ips(n)
    raw_bytes = sum(len(v.encode("utf-8")) for v in values) + len(values)

    # Step 1: M8A body (sem seq-RLE)
    body_m8a = get_m8a_body(values)
    body_lines = body_m8a.rstrip('\n').split('\n')

    # Step 2: aplicar detect_seq_runs em body_m8a
    runs = detect_seq_runs(body_lines)

    # Step 3: aplicar compact_body
    compacted_lines, info = compact_body(body_lines)
    compacted_text = '\n'.join(compacted_lines) + '\n'
    compacted_bytes = len(compacted_text.encode("utf-8"))

    # Step 4: M10 standard via HCCSeqRLE pra comparacao
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())
    features = analyze_column(values)
    cadence_detected, _ = detect_cadence_from_features(features, unicas)
    min_len = detect_min_len_from_features(features)
    if cadence_detected:
        tokens, _ = processar_with_hint(unicas, min_len=min_len,
                                         prefer_shape_consistency=True)
    else:
        tokens, _ = processar(unicas, min_len=min_len)
    syn = HCCSeqRLE()
    m10_text = syn.encode(values, unicas, tokens, "val")
    m10_bytes = len(m10_text.encode("utf-8"))

    # Step 5: salvar tudo pra inspecao
    out_dir = THIS / f"n{n}"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "input.txt").write_text(
        "\n".join(values[:30]) + "\n... (truncado)\n" if len(values) > 30
        else "\n".join(values) + "\n",
        encoding="utf-8"
    )
    (out_dir / "body-pos-M8A.txt").write_text(
        "# Body apos M8A (sem seq-RLE):\n" + body_m8a,
        encoding="utf-8"
    )
    (out_dir / "body-pos-M10.txt").write_text(
        "# Body apos M10 completo (M8A + seq-RLE):\n" + m10_text,
        encoding="utf-8"
    )
    (out_dir / "seq_runs.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8"
    )

    # Step 6: analise estrutural do body
    n_body_lines = len(body_lines)
    body_line_lengths = [len(l) for l in body_lines]
    unique_lengths = len(set(body_line_lengths))
    lines_with_escape_runs = sum(1 for l in body_lines
                                  if find_escape_digit_runs(l))

    return {
        "n_input": n,
        "raw_bytes": raw_bytes,
        "n_body_lines_m8a": n_body_lines,
        "n_unique_lengths": unique_lengths,
        "n_lines_with_escape_runs": lines_with_escape_runs,
        "n_seq_runs_detected": len(runs),
        "m10_bytes": m10_bytes,
        "m10_ratio_pct": round(m10_bytes / raw_bytes * 100, 2),
        "ratio_body_vs_input": round(n_body_lines / n, 3),
    }


def main():
    print("=== Sub-exp 14 — Cross-subnet investigation ===\n")
    print(f"{'n_input':>8} {'body_lines':>10} {'uniq_len':>9} "
          f"{'esc_runs':>9} {'seq_runs':>9} {'m10_B':>8} {'ratio':>7}")
    print("-" * 75)
    all_results = []
    for n in [50, 100, 200, 500, 1000]:
        r = investigate_n(n)
        all_results.append(r)
        print(f"{r['n_input']:>8} {r['n_body_lines_m8a']:>10} "
              f"{r['n_unique_lengths']:>9} {r['n_lines_with_escape_runs']:>9} "
              f"{r['n_seq_runs_detected']:>9} {r['m10_bytes']:>8} "
              f"{r['m10_ratio_pct']:>6.2f}%")

    # Inspecionar body samples pra entender estrutura
    print("\n=== Inspecao body M8A (n=200, primeiras 30 linhas) ===\n")
    body_path = THIS / "n200" / "body-pos-M8A.txt"
    if body_path.exists():
        text = body_path.read_text(encoding="utf-8")
        lines = text.split("\n")
        for line in lines[:35]:
            print(f"  {line}")

    out = THIS / "manifest.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in all_results) + "\n",
                   encoding="utf-8")
    print(f"\nManifest: {out}")
    print(f"Bodies + outputs em: {THIS}/n*/")


if __name__ == "__main__":
    main()
