"""Tentativa 02 — HCC sozinho com seq-RLE near-identical.

Roda OBAT canonical (src/tcf intocado) + HCC_Fork (este sub-exp)
sobre D11a-h. Compara com baseline (sub-exp 01). Valida RT.
"""

from __future__ import annotations

import csv
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(THIS))

from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar  # noqa: E402
from hcc_fork import HCCForkSeqRLE  # noqa: E402


DATASETS = [
    "D11a-datas-dia",
    "D11b-datas-borda",
    "D11c-datas-mensal",
    "D11d-datetime-min",
    "D11e-datetime-mensal",
    "D11f-datetime-ms",
    "D11g-datetime-us",
    "D11h-datetime-ns",
]


def write_lf(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def load_rows(ds: str) -> list[str]:
    p = ROOT / "datasets" / "synthetic" / f"{ds}.csv"
    with p.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def dedup_preserve_order(values: list[str]) -> list[str]:
    seen: OrderedDict[str, bool] = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def diff_bodies(canonical: str, fork: str) -> str:
    can_lines = canonical.rstrip('\n').split('\n')
    fork_lines = fork.rstrip('\n').split('\n')
    out = [
        "# Diff body canonical vs fork (tentativa 02)",
        "",
        f"Canonical: {len(can_lines)} linhas, {len(canonical.encode('utf-8'))} bytes",
        f"Fork:      {len(fork_lines)} linhas, {len(fork.encode('utf-8'))} bytes",
        "",
        "## Canonical (baseline)",
        "```",
    ]
    out.extend(can_lines)
    out.append("```")
    out.append("")
    out.append("## Fork (com seq-RLE)")
    out.append("```")
    out.extend(fork_lines)
    out.append("```")
    out.append("")
    return "\n".join(out) + "\n"


def render_seq_info(info: list[dict]) -> str:
    if not info:
        return "# Seq-RLE runs detectados\n\n(nenhum)\n"
    out = [
        "# Seq-RLE runs detectados",
        "",
        f"Total de runs: {len(info)}",
        "",
        "| Linhas (1-based) | Count | Delta | Template | Savings (bytes) |",
        "|---|---:|---:|---|---:|",
    ]
    for r in info:
        out.append(
            f"| {r['start_line']}..{r['end_line']} | {r['count']} | "
            f"{r['delta']:+d} | `{r['template']}` | {r['savings']} |"
        )
    out.append("")
    return "\n".join(out) + "\n"


def process(ds: str) -> dict:
    rows = load_rows(ds)
    unicas = dedup_preserve_order(rows)
    tokens_por, _ = processar(unicas, min_len=3)

    # Baseline (canonical)
    syn_canonical = M8AVirtualRefsSyntax()
    body_canonical = syn_canonical.encode(rows, unicas, tokens_por, "val")
    bytes_canonical = len(body_canonical.encode("utf-8"))

    # Fork
    syn_fork = HCCForkSeqRLE()
    body_fork = syn_fork.encode(rows, unicas, tokens_por, "val")
    bytes_fork = len(body_fork.encode("utf-8"))

    # RT
    decoded = syn_fork.decode(body_fork)
    rt_ok = (decoded == rows)
    rt_status = "OK" if rt_ok else "FAIL"
    rt_details = ""
    if not rt_ok:
        rt_details = (
            f"\nEsperado ({len(rows)}):\n  " +
            "\n  ".join(repr(r) for r in rows) +
            f"\n\nObtido ({len(decoded)}):\n  " +
            "\n  ".join(repr(r) for r in decoded)
        )

    # Outputs
    out = THIS / "outputs" / ds
    write_lf(out / "1-body-canonical.tcf", body_canonical)
    write_lf(out / "2-body-fork.tcf", body_fork)
    write_lf(out / "3-diff-canonical-vs-fork.md",
             diff_bodies(body_canonical, body_fork))
    write_lf(out / "4-seq-runs.md", render_seq_info(syn_fork.get_seq_info()))
    write_lf(out / "5-rt-status.txt",
             f"RT: {rt_status}\n"
             f"bytes_canonical: {bytes_canonical}\n"
             f"bytes_fork:      {bytes_fork}\n"
             f"delta_bytes:     {bytes_fork - bytes_canonical:+d}\n"
             f"delta_pct:       {(bytes_fork - bytes_canonical) / bytes_canonical * 100:+.1f}%\n"
             f"{rt_details}\n")

    return {
        "dataset": ds,
        "rows": len(rows),
        "unicas": len(unicas),
        "bytes_canonical": bytes_canonical,
        "bytes_fork": bytes_fork,
        "delta_bytes": bytes_fork - bytes_canonical,
        "delta_pct": (bytes_fork - bytes_canonical) / bytes_canonical * 100,
        "n_runs": len(syn_fork.get_seq_info()),
        "rt": rt_status,
    }


def main() -> None:
    print("=== Tentativa 02 — HCC sozinho seq-RLE ===\n")

    results = []
    for ds in DATASETS:
        r = process(ds)
        results.append(r)
        sign = '+' if r['delta_bytes'] >= 0 else ''
        print(
            f"  {ds:24}  canon={r['bytes_canonical']:4} "
            f"fork={r['bytes_fork']:4} "
            f"delta={sign}{r['delta_bytes']:4} ({r['delta_pct']:+.1f}%) "
            f"runs={r['n_runs']}  RT={r['rt']}"
        )

    # Summary
    total_can = sum(r['bytes_canonical'] for r in results)
    total_fork = sum(r['bytes_fork'] for r in results)
    total_delta = total_fork - total_can
    rt_pass = sum(1 for r in results if r['rt'] == 'OK')

    out = [
        "# Resultado — Tentativa 02 (HCC sozinho seq-RLE)",
        "",
        "## Tabela",
        "",
        "| Dataset | rows | unicas | canon (B) | fork (B) | Δ (B) | Δ (%) | runs | RT |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in results:
        sign = '+' if r['delta_bytes'] >= 0 else ''
        out.append(
            f"| [{r['dataset']}]({r['dataset']}/3-diff-canonical-vs-fork.md) "
            f"| {r['rows']} | {r['unicas']} "
            f"| {r['bytes_canonical']} | {r['bytes_fork']} "
            f"| {sign}{r['delta_bytes']} | {r['delta_pct']:+.1f}% "
            f"| {r['n_runs']} | {r['rt']} |"
        )
    out.extend([
        "",
        "## Resumo",
        "",
        f"- Total canonical: {total_can} bytes",
        f"- Total fork:      {total_fork} bytes",
        f"- Delta total:     {'+' if total_delta >= 0 else ''}{total_delta} bytes "
        f"({total_delta/total_can*100:+.1f}%)",
        f"- RT: {rt_pass}/{len(results)} OK",
        "",
        "## Para analise detalhada por dataset, ver `outputs/<ds>/`",
        "",
        "Sintese final + revisao de Q15 em `result.md` (proxima etapa).",
        "",
    ])
    write_lf(THIS / "summary.md", "\n".join(out) + "\n")
    print()
    print(f"summary.md: {THIS / 'summary.md'}")
    print()
    print(f"Totais: canonical={total_can}B fork={total_fork}B "
          f"delta={total_delta:+d}B ({total_delta/total_can*100:+.1f}%)")
    print(f"RT: {rt_pass}/{len(results)}")


if __name__ == "__main__":
    main()
