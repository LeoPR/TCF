"""Sub-exp 01 — Caracterizacao baseline M10 em D-CPF.

Mede `encode()` canonical (sem pre-tx) nos 4 datasets sinteticos
D-CPF. Reporta:
- bytes raw / m10 / ratio
- bytes/CPF medio
- features pre-pass (cadence_detected, min_len, is_numeric)
- seq_rle_runs_count (HCC capturou cadencia near-identical?)
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

THIS = Path(__file__).parent
LAB = THIS.parent
ROOT = LAB.parents[3]
sys.path.insert(0, str(ROOT / "src"))

from tcf import encode, SideOutputs  # noqa: E402


DATASETS = [
    "D-CPF-uniform",
    "D-CPF-clustered",
    "D-CPF-mixed",
    "D-CPF-corrupt",
]


def load_cpfs(name: str) -> list[str]:
    path = LAB / "data" / f"{name}.csv"
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)  # skip header
        return [row[0] for row in r if row]


def measure(name: str) -> dict:
    values = load_cpfs(name)
    raw_bytes = sum(len(v.encode("utf-8")) for v in values) + len(values)  # + LFs proxy

    side = SideOutputs()
    text = encode(values, side_outputs=side)
    m10_bytes = len(text.encode("utf-8"))

    cf = side.column_features
    return {
        "dataset": name,
        "n_rows": len(values),
        "n_unicas": cf.n_unicas if cf else 0,
        "avg_len_raw": round(cf.avg_len, 2) if cf else 0,
        "raw_bytes": raw_bytes,
        "m10_bytes": m10_bytes,
        "ratio_pct": round(m10_bytes / raw_bytes * 100, 2),
        "bytes_per_cpf_raw": round(raw_bytes / len(values), 2),
        "bytes_per_cpf_m10": round(m10_bytes / len(values), 2),
        "cadence_detected": side.cadence_detected,
        "cadence_rule": (side.cadence_info or {}).get("rule_hit"),
        "min_len": side.min_len,
        "is_numeric": cf.is_numeric if cf else False,
        "seq_rle_runs": len(side.seq_rle_runs),
    }


def main():
    results = [measure(name) for name in DATASETS]

    print("=== Sub-exp 01 — Caracterizacao baseline M10 ===\n")
    print(f"{'dataset':22s} {'rows':>5} {'raw':>8} {'m10':>8} "
          f"{'ratio':>7} {'b/cpf raw':>10} {'b/cpf m10':>10} "
          f"{'cad':>5} {'minlen':>7} {'rle':>5}")
    print("-" * 110)
    for r in results:
        print(f"{r['dataset']:22s} {r['n_rows']:>5} "
              f"{r['raw_bytes']:>8} {r['m10_bytes']:>8} "
              f"{r['ratio_pct']:>6.2f}% "
              f"{r['bytes_per_cpf_raw']:>10.2f} "
              f"{r['bytes_per_cpf_m10']:>10.2f} "
              f"{str(r['cadence_detected'])[:1]:>5} "
              f"{r['min_len']:>7} {r['seq_rle_runs']:>5}")

    # Manifest
    out = THIS / "manifest.jsonl"
    out.write_text(
        "\n".join(json.dumps(r) for r in results) + "\n",
        encoding="utf-8",
    )
    print(f"\nManifest: {out}")

    # Report
    report = [
        "# Sub-exp 01 — Caracterizacao baseline M10 (report)",
        "",
        "## Resultados",
        "",
        "| dataset | rows | raw | m10 | ratio | b/CPF raw | b/CPF m10 | cadence | min_len | rle_runs |",
        "|---|---:|---:|---:|---:|---:|---:|:---:|---:|---:|",
    ]
    for r in results:
        report.append(
            f"| {r['dataset']} | {r['n_rows']} | {r['raw_bytes']} | "
            f"{r['m10_bytes']} | {r['ratio_pct']:.2f}% | "
            f"{r['bytes_per_cpf_raw']:.2f} | {r['bytes_per_cpf_m10']:.2f} | "
            f"{r['cadence_detected']} | {r['min_len']} | {r['seq_rle_runs']} |"
        )

    report.extend([
        "",
        "## Interpretacao",
        "",
        f"- **D-CPF-uniform** ({results[0]['ratio_pct']:.1f}%): "
        f"CPFs uniformes aleatorios. M10 captura pouco — sem padrao "
        f"administrativo, OBAT/HCC nao acha refs significativos.",
        f"- **D-CPF-clustered** ({results[1]['ratio_pct']:.1f}%): "
        f"3 digitos compartilhados em blocos de 100. M10 deveria capturar "
        f"prefix comum via OBAT — comparar com uniform.",
        f"- **D-CPF-mixed** ({results[2]['ratio_pct']:.1f}%): "
        f"50% formatados / 50% sem mascara. Dois 'sub-padroes' coexistindo.",
        f"- **D-CPF-corrupt** ({results[3]['ratio_pct']:.1f}%): "
        f"5% corruptos. M10 trata todos como string normal — mistura nao "
        f"prejudica nem ajuda.",
        "",
        "## Observacoes pre-pass",
        "",
    ])
    for r in results:
        report.append(
            f"- **{r['dataset']}**: cadence={r['cadence_detected']} "
            f"(rule={r['cadence_rule']}), min_len={r['min_len']}, "
            f"is_numeric={r['is_numeric']}, seq_rle_runs={r['seq_rle_runs']}"
        )
    report.append("")
    report.append("## Conclusao parcial")
    report.append("")
    report.append("Baseline M10 medido. Sub-exps 02/03/04 vao comparar:")
    report.append("- Variante A (raw, igual a 01)")
    report.append("- Variante B (base-encoded)")
    report.append("- Variante C (hibrido strip-marcadores)")
    report.append("")

    (THIS / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Report: {THIS / 'report.md'}")


if __name__ == "__main__":
    main()
