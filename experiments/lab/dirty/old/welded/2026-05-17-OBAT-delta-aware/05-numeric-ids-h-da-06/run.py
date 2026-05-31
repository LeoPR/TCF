"""Sub-exp 05 — H-DA-06: testar fork em datasets numericos (D16a-c).

Pipeline igual ao sub-exp 04, mas em datasets numericos (IDs
sequenciais) em vez de datetime. Valida generalizacao da hipotese
H-DA-07 (shape-preserve hint) pra outros tipos de delta.
"""

from __future__ import annotations

import csv
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SRC = ROOT / "src"
HCC_FORK_DIR = THIS.parent / "02-hcc-sozinho-rle-near-identical"
OBAT_FORK_DIR = THIS.parent / "04-obat-shape-consistency-hint"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(HCC_FORK_DIR))
sys.path.insert(0, str(OBAT_FORK_DIR))
sys.path.insert(0, str(THIS))

from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar, TokLit, TokRefPref, TokRefSuf  # noqa: E402
from hcc_fork import HCCForkSeqRLE  # noqa: E402
from obat_fork import processar_with_hint  # noqa: E402


DATASETS = [
    "D16a-ids-3digits",
    "D16b-ids-4digits",
    "D16c-ids-prefixados",
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


def fmt_token(tok) -> str:
    if isinstance(tok, TokLit):
        return f'L({tok.text!r})'
    if isinstance(tok, TokRefPref):
        return f'P({tok.string_id},{tok.length})'
    if isinstance(tok, TokRefSuf):
        return f'S({tok.string_id},{tok.length})'
    return repr(tok)


def render_tokens(unicas, tokens_por, header):
    out = [header, ""]
    out.append(f"strings_unicas: {len(unicas)}")
    out.append("")
    width = max(len(s) for s in unicas) + 2
    for i, (s, toks) in enumerate(zip(unicas, tokens_por)):
        out.append(f"  [{i+1:2}] {s!r:<{width}} -> "
                   f"{' + '.join(fmt_token(t) for t in toks)}")
    return "\n".join(out) + "\n"


def render_diff_bodies(b_t02, b_fork):
    cl = b_t02.rstrip('\n').split('\n')
    fl = b_fork.rstrip('\n').split('\n')
    out = [
        "# Diff bodies — t02 (canonical OBAT + HCC fork) vs sub-exp 04+05 (fork OBAT + HCC fork)",
        "",
        f"t02:    {len(cl)} linhas, {len(b_t02.encode('utf-8'))} bytes",
        f"fork:   {len(fl)} linhas, {len(b_fork.encode('utf-8'))} bytes",
        "",
        "## t02",
        "```",
    ]
    out.extend(cl)
    out.append("```")
    out.append("")
    out.append("## sub-exp 04+05 (fork)")
    out.append("```")
    out.extend(fl)
    out.append("```")
    return "\n".join(out) + "\n"


def process(ds: str) -> dict:
    rows = load_rows(ds)
    unicas = dedup_preserve_order(rows)

    tokens_canon, _ = processar(unicas, min_len=3)
    body_baseline = M8AVirtualRefsSyntax().encode(rows, unicas, tokens_canon, "val")
    bytes_baseline = len(body_baseline.encode("utf-8"))

    body_t02 = HCCForkSeqRLE().encode(rows, unicas, tokens_canon, "val")
    bytes_t02 = len(body_t02.encode("utf-8"))

    tokens_fork, log_fork = processar_with_hint(
        unicas, min_len=3, prefer_shape_consistency=True
    )
    syn_fork = HCCForkSeqRLE()
    body_fork = syn_fork.encode(rows, unicas, tokens_fork, "val")
    bytes_fork = len(body_fork.encode("utf-8"))

    decoded = syn_fork.decode(body_fork)
    rt_ok = (decoded == rows)
    rt_status = "OK" if rt_ok else "FAIL"
    rt_details = ""
    if not rt_ok:
        rt_details = (
            f"\nEsperado ({len(rows)}):\n  " +
            "\n  ".join(repr(r) for r in rows[:5]) +
            f"\n\nObtido ({len(decoded)}):\n  " +
            "\n  ".join(repr(r) for r in decoded[:5])
        )

    out = THIS / "outputs" / ds
    write_lf(out / "1-tokens-canonical.txt",
             render_tokens(unicas, tokens_canon, "# Tokens — OBAT canonical (greedy)"))
    write_lf(out / "2-tokens-fork.txt",
             render_tokens(unicas, tokens_fork, "# Tokens — OBAT fork (shape-preserve)"))
    write_lf(out / "2-tokens-fork-log.txt", "# Log\n\n" + log_fork + "\n")
    write_lf(out / "3-body-fork-canonical-obat.tcf", body_t02)
    write_lf(out / "4-body-fork-fork-obat.tcf", body_fork)
    write_lf(out / "5-rt-status.txt",
             f"RT: {rt_status}\n"
             f"bytes_baseline (canonical OBAT + HCC canonical): {bytes_baseline}\n"
             f"bytes_t02 (canonical OBAT + HCC fork):           {bytes_t02}\n"
             f"bytes_fork (fork OBAT + HCC fork):               {bytes_fork}\n"
             f"delta_vs_t02:    {bytes_fork - bytes_t02:+d}\n"
             f"delta_vs_baseline: {bytes_fork - bytes_baseline:+d}\n"
             f"{rt_details}\n")
    write_lf(out / "6-diff-bodies.md", render_diff_bodies(body_t02, body_fork))

    return {
        "dataset": ds,
        "rows": len(rows),
        "unicas": len(unicas),
        "bytes_baseline": bytes_baseline,
        "bytes_t02": bytes_t02,
        "bytes_fork": bytes_fork,
        "delta_vs_t02": bytes_fork - bytes_t02,
        "delta_vs_baseline": bytes_fork - bytes_baseline,
        "rt": rt_status,
    }


def main():
    print("=== Sub-exp 05 — H-DA-06 (numeric IDs) ===\n")
    print("Pipeline: igual sub-exp 04, datasets D16a-c (IDs sequenciais)\n")

    results = []
    for ds in DATASETS:
        r = process(ds)
        results.append(r)
        s_t02 = '+' if r['delta_vs_t02'] >= 0 else ''
        s_bl = '+' if r['delta_vs_baseline'] >= 0 else ''
        print(
            f"  {ds:24}  "
            f"bl={r['bytes_baseline']:4} "
            f"t02={r['bytes_t02']:4} "
            f"fork={r['bytes_fork']:4} "
            f"d-t02={s_t02}{r['delta_vs_t02']:4} "
            f"d-bl={s_bl}{r['delta_vs_baseline']:4}  RT={r['rt']}"
        )

    total_bl = sum(r['bytes_baseline'] for r in results)
    total_t02 = sum(r['bytes_t02'] for r in results)
    total_fork = sum(r['bytes_fork'] for r in results)
    rt_pass = sum(1 for r in results if r['rt'] == 'OK')

    out = [
        "# Resumo — Sub-exp 05 (H-DA-06 numeric IDs)",
        "",
        "Pipeline comparativo (igual sub-exp 04):",
        "- baseline = OBAT canonical + HCC canonical",
        "- t02 = OBAT canonical + HCC fork seq-RLE",
        "- fork = OBAT fork shape-preserve + HCC fork seq-RLE",
        "",
        "## Tabela",
        "",
        "| Dataset | rows | uniq | baseline | t02 | fork | Δ vs t02 | Δ vs baseline | RT |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in results:
        s_t02 = '+' if r['delta_vs_t02'] >= 0 else ''
        s_bl = '+' if r['delta_vs_baseline'] >= 0 else ''
        out.append(
            f"| [{r['dataset']}]({r['dataset']}/6-diff-bodies.md) "
            f"| {r['rows']} | {r['unicas']} "
            f"| {r['bytes_baseline']} | {r['bytes_t02']} | {r['bytes_fork']} "
            f"| {s_t02}{r['delta_vs_t02']} | {s_bl}{r['delta_vs_baseline']} "
            f"| {r['rt']} |"
        )
    out.extend([
        "",
        "## Totais",
        "",
        f"- baseline: {total_bl} B",
        f"- t02:      {total_t02} B  ({total_t02-total_bl:+d} vs baseline)",
        f"- fork:     {total_fork} B  ({total_fork-total_t02:+d} vs t02, "
        f"{total_fork-total_bl:+d} vs baseline)",
        "",
        f"RT: {rt_pass}/{len(results)}",
        "",
    ])
    write_lf(THIS / "summary.md", "\n".join(out) + "\n")
    print()
    print(f"Totais: baseline={total_bl} t02={total_t02} fork={total_fork}")
    print(f"RT: {rt_pass}/{len(results)}")


if __name__ == "__main__":
    main()
