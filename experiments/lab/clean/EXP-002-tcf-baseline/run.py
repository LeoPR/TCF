"""EXP-002 — TCF v0.2 baseline. Roda TCF L0, L2, L3 em 4 datasets × 3 compressoes.

Plus: gera relatorio comparativo com EXP-001 (CSV).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB.parent.parent))

from framework import simulate, load_dataset, describe


HERE = Path(__file__).resolve().parent
EXP001 = HERE.parent / "EXP-001-csv-baseline"
MANIFEST = HERE / "manifest.jsonl"
REPORT = HERE / "report.md"

DATASETS = ["micro", "small", "categorical_heavy", "wide_random"]
COMPRESSIONS = ["none", "gzip", "brotli"]
TCF_LEVELS = [0, 2, 3]


def main() -> None:
    if MANIFEST.exists():
        MANIFEST.unlink()

    results = []

    print("=== EXP-002 — TCF v0.2 baseline ===\n")
    for ds_name in DATASETS:
        rows = load_dataset(ds_name)
        meta = describe(ds_name)
        print(f"Dataset: {ds_name} — {meta['n_rows']} rows × {meta['n_cols']} cols")

        for level in TCF_LEVELS:
            for comp in COMPRESSIONS:
                # TCF L3 e schema-only (lossy); roundtrip nao se aplica
                tolerant = True
                # Para L3, esperar roundtrip falhar — ainda registramos
                r = simulate(
                    rows,
                    encoder="tcf",
                    encoder_kwargs={"level": level, "include_stats": True},
                    compression=comp,
                    n_iterations=10,
                    tolerant_types=tolerant,
                )
                record = r.to_dict()
                record["dataset"] = ds_name
                record["tcf_level"] = level
                results.append(record)

                with open(MANIFEST, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")

                rt = "OK" if r.roundtrip_ok else "FAIL"
                if level == 3:
                    rt = "(L3=schema-only)"
                print(f"  tcf-L{level}+{comp:<6} "
                      f"raw={r.bytes_uncompressed:>5}B "
                      f"comp={r.bytes_compressed:>5}B "
                      f"ratio={r.compression_ratio*100:>5.1f}% "
                      f"enc={r.encode_ms:.2f}ms "
                      f"dec={r.decode_ms:.2f}ms "
                      f"roundtrip={rt}")
        print()

    write_report(results)
    print(f"\nManifest: {MANIFEST}")
    print(f"Report:   {REPORT}")


def write_report(results: list[dict]) -> None:
    """Gera report.md com tabela TCF + comparacao com EXP-001 CSV."""

    # Carregar CSV results se EXP-001 ja foi rodado
    csv_results = []
    csv_manifest = EXP001 / "manifest.jsonl"
    if csv_manifest.exists():
        with open(csv_manifest, encoding="utf-8") as fh:
            csv_results = [json.loads(line) for line in fh if line.strip()]

    lines = [
        "# EXP-002 — TCF v0.2 Baseline (Resultados)",
        "",
        f"Total: {len(results)} execucoes (4 datasets × 3 niveis TCF × 3 compressoes)",
        "",
        "## TCF — tabela mestra",
        "",
        "| Dataset | Rows × Cols | TCF Level | Compressao | Bytes raw | Bytes comp | Ratio | Encode (ms) | Decode (ms) | Roundtrip |",
        "|---------|-------------|-----------|------------|-----------|------------|-------|-------------|-------------|-----------|",
    ]

    for r in results:
        ratio_str = f"{r['compression_ratio']*100:.1f}%"
        rt = "✓" if r["roundtrip_ok"] else ("L3" if r["tcf_level"] == 3 else "✗")
        lines.append(
            f"| {r['dataset']} | {r['n_rows']}×{r['n_cols']} | L{r['tcf_level']} | "
            f"{r['compression']} | {r['bytes_uncompressed']} | "
            f"{r['bytes_compressed']} | {ratio_str} | "
            f"{r['encode_ms']:.2f} | {r['decode_ms']:.2f} | {rt} |"
        )

    # Tabela comparativa TCF vs CSV (so se EXP-001 disponivel)
    if csv_results:
        lines.extend([
            "",
            "## Comparativo TCF L2 vs CSV (mesma compressao)",
            "",
            "Bytes comprimidos (menor e melhor):",
            "",
            "| Dataset | CSV none | TCF L2 none | CSV gzip | TCF L2 gzip | CSV brotli | TCF L2 brotli |",
            "|---------|----------|-------------|----------|-------------|------------|----------------|",
        ])
        for ds in DATASETS:
            csv_by_comp = {r["compression"]: r["bytes_compressed"]
                           for r in csv_results if r["dataset"] == ds}
            tcf_by_comp = {r["compression"]: r["bytes_compressed"]
                           for r in results if r["dataset"] == ds and r["tcf_level"] == 2}
            lines.append(
                f"| {ds} | "
                f"{csv_by_comp.get('none', '-'):>5} | {tcf_by_comp.get('none', '-'):>5} | "
                f"{csv_by_comp.get('gzip', '-'):>5} | {tcf_by_comp.get('gzip', '-'):>5} | "
                f"{csv_by_comp.get('brotli', '-'):>5} | {tcf_by_comp.get('brotli', '-'):>5} |"
            )

        # Win/loss summary
        lines.extend([
            "",
            "## Win/loss vs CSV (mesmo compressor)",
            "",
            "| Dataset | TCF L2 vence CSV em? |",
            "|---------|---------------------|",
        ])
        for ds in DATASETS:
            csv_by = {r["compression"]: r["bytes_compressed"]
                      for r in csv_results if r["dataset"] == ds}
            tcf_by = {r["compression"]: r["bytes_compressed"]
                      for r in results if r["dataset"] == ds and r["tcf_level"] == 2}
            wins = []
            for c in ["none", "gzip", "brotli"]:
                if c in csv_by and c in tcf_by:
                    delta = csv_by[c] - tcf_by[c]
                    if delta > 0:
                        wins.append(f"{c}(-{delta}B)")
                    elif delta < 0:
                        wins.append(f"{c}(+{abs(delta)}B perde)")
            lines.append(f"| {ds} | {' / '.join(wins) if wins else '(sem dados)'} |")

    lines.extend([
        "",
        "## Observacoes",
        "",
        "- **TCF L0** e raw columnar — base sem compressao algoritmica.",
        "- **TCF L2** ativa RLE+STATS. Ganho real depende de repeticao.",
        "- **TCF L3** e schema-only (lossy). Roundtrip nao se aplica;",
        "  bytes sao minimos (uso: enviar so o schema para LLM).",
        "- **Encoder TCF v0.2** e o atual. v0.4 (futuro) deve melhorar:",
        "  DICT, stratified STATS, auto-sort, type-preserving decode.",
        "",
        "## Proximos experimentos",
        "",
        "- EXP-003: TCF L2 com `sort_by` manual (ver impacto RLE)",
        "- EXP-004: TCF v0.4 com DICT por coluna",
        "- EXP-005: TCF v0.4 com cross-column DICT",
        "- EXP-006: comparativo direto TCF vs CSV vs JSON em todos cenarios",
    ])

    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
