"""Sub-exp 04 — OBAT shape-consistency hint (H-DA-07).

Pipeline:
  rows -> dedupe -> processar_with_hint(prefer_shape_consistency=True)
       -> HCCForkSeqRLE.encode -> body
       -> HCCForkSeqRLE.decode -> RT check

Compara contra:
  - Baseline (canonical OBAT + HCC canonical) — sub-exp 01
  - Tentativa 02 (canonical OBAT + HCC fork) — sub-exp 02

Mede bytes em cada e RT.
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
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(HCC_FORK_DIR))
sys.path.insert(0, str(THIS))

from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar, TokLit, TokRefPref, TokRefSuf  # noqa: E402
from hcc_fork import HCCForkSeqRLE  # noqa: E402
from obat_fork import processar_with_hint  # noqa: E402


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


def fmt_token(tok) -> str:
    if isinstance(tok, TokLit):
        return f'L({tok.text!r})'
    if isinstance(tok, TokRefPref):
        return f'P({tok.string_id},{tok.length})'
    if isinstance(tok, TokRefSuf):
        return f'S({tok.string_id},{tok.length})'
    return repr(tok)


def render_tokens(unicas: list[str], tokens_por: list[list], header: str) -> str:
    out = [header, ""]
    out.append(f"strings_unicas: {len(unicas)}")
    out.append("")
    width = max(len(s) for s in unicas) + 2
    for i, (s, toks) in enumerate(zip(unicas, tokens_por)):
        out.append(f"  [{i+1:2}] {s!r:<{width}} -> {' + '.join(fmt_token(t) for t in toks)}")
    return "\n".join(out) + "\n"


def render_diff_bodies(b_canon_obat: str, b_fork_obat: str) -> str:
    cl = b_canon_obat.rstrip('\n').split('\n')
    fl = b_fork_obat.rstrip('\n').split('\n')
    out = [
        "# Diff bodies — canonical OBAT vs fork OBAT (ambos com HCC fork)",
        "",
        f"Canonical OBAT + HCC fork: {len(cl)} linhas, "
        f"{len(b_canon_obat.encode('utf-8'))} bytes",
        f"Fork OBAT + HCC fork:      {len(fl)} linhas, "
        f"{len(b_fork_obat.encode('utf-8'))} bytes",
        "",
        "## Canonical OBAT (= tentativa 02 output)",
        "```",
    ]
    out.extend(cl)
    out.append("```")
    out.append("")
    out.append("## Fork OBAT (com H-DA-07 hint)")
    out.append("```")
    out.extend(fl)
    out.append("```")
    return "\n".join(out) + "\n"


def process(ds: str) -> dict:
    rows = load_rows(ds)
    unicas = dedup_preserve_order(rows)

    # Pipeline A: OBAT canonical + HCC canonical (baseline)
    tokens_canon, _ = processar(unicas, min_len=3)
    body_canonical = M8AVirtualRefsSyntax().encode(rows, unicas, tokens_canon, "val")
    bytes_baseline = len(body_canonical.encode("utf-8"))

    # Pipeline B: OBAT canonical + HCC fork (tentativa 02)
    body_t02 = HCCForkSeqRLE().encode(rows, unicas, tokens_canon, "val")
    bytes_t02 = len(body_t02.encode("utf-8"))

    # Pipeline C: OBAT fork (H-DA-07) + HCC fork
    tokens_fork, log_fork = processar_with_hint(
        unicas, min_len=3, prefer_shape_consistency=True
    )
    syn_fork = HCCForkSeqRLE()
    body_fork = syn_fork.encode(rows, unicas, tokens_fork, "val")
    bytes_fork = len(body_fork.encode("utf-8"))

    # RT validation (Pipeline C)
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

    # Outputs
    out = THIS / "outputs" / ds
    write_lf(out / "1-tokens-canonical.txt",
             render_tokens(unicas, tokens_canon,
                           "# Tokens — OBAT canonical (greedy)"))
    write_lf(out / "2-tokens-fork.txt",
             render_tokens(unicas, tokens_fork,
                           "# Tokens — OBAT fork (H-DA-07 shape-preserve)"))
    write_lf(out / "2-tokens-fork-log.txt",
             "# Log do processar_with_hint\n\n" + log_fork + "\n")
    write_lf(out / "3-body-fork-canonical-obat.tcf", body_t02)
    write_lf(out / "4-body-fork-fork-obat.tcf", body_fork)
    write_lf(out / "5-rt-status.txt",
             f"RT (Pipeline C): {rt_status}\n"
             f"bytes_baseline (canonical OBAT + HCC canonical): {bytes_baseline}\n"
             f"bytes_tentativa02 (canonical OBAT + HCC fork):   {bytes_t02}\n"
             f"bytes_subexp04 (fork OBAT + HCC fork):           {bytes_fork}\n"
             f"delta_vs_t02:   {bytes_fork - bytes_t02:+d} bytes "
             f"({(bytes_fork - bytes_t02) / bytes_t02 * 100:+.1f}%)\n"
             f"delta_vs_baseline: {bytes_fork - bytes_baseline:+d} bytes "
             f"({(bytes_fork - bytes_baseline) / bytes_baseline * 100:+.1f}%)\n"
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


def main() -> None:
    print("=== Sub-exp 04 — OBAT shape-consistency hint (H-DA-07) ===\n")
    print("Pipeline C: OBAT fork (H-DA-07) + HCC fork (tentativa 02)\n")

    results = []
    for ds in DATASETS:
        r = process(ds)
        results.append(r)
        sign_t02 = '+' if r['delta_vs_t02'] >= 0 else ''
        sign_bl = '+' if r['delta_vs_baseline'] >= 0 else ''
        print(
            f"  {ds:24}  "
            f"bl={r['bytes_baseline']:4} "
            f"t02={r['bytes_t02']:4} "
            f"fork={r['bytes_fork']:4} "
            f"d-t02={sign_t02}{r['delta_vs_t02']:4} "
            f"d-bl={sign_bl}{r['delta_vs_baseline']:4}  RT={r['rt']}"
        )

    # Summary
    total_bl = sum(r['bytes_baseline'] for r in results)
    total_t02 = sum(r['bytes_t02'] for r in results)
    total_fork = sum(r['bytes_fork'] for r in results)
    rt_pass = sum(1 for r in results if r['rt'] == 'OK')

    out = [
        "# Resumo — Sub-exp 04 (H-DA-07: OBAT shape-consistency hint)",
        "",
        "Pipeline comparativo:",
        "- **baseline** = OBAT canonical + HCC canonical (sub-exp 01)",
        "- **t02** = OBAT canonical + HCC fork seq-RLE (sub-exp 02)",
        "- **fork** = OBAT fork shape-preserve + HCC fork seq-RLE (este)",
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
        f"- t02:      {total_t02} B  ({total_t02-total_bl:+d} vs baseline, {(total_t02-total_bl)/total_bl*100:+.1f}%)",
        f"- fork:     {total_fork} B  ({total_fork-total_t02:+d} vs t02, {(total_fork-total_t02)/total_t02*100:+.1f}%)",
        f"-           ({total_fork-total_bl:+d} vs baseline, {(total_fork-total_bl)/total_bl*100:+.1f}%)",
        "",
        f"RT: {rt_pass}/{len(results)}",
        "",
        "## Por dataset, ver `outputs/<ds>/`",
        "",
        "- `1-tokens-canonical.txt`, `2-tokens-fork.txt` — tokens emitidos",
        "- `3-body-fork-canonical-obat.tcf` — body usando OBAT canonical + HCC fork",
        "- `4-body-fork-fork-obat.tcf` — body usando OBAT fork + HCC fork",
        "- `5-rt-status.txt` — numerico",
        "- `6-diff-bodies.md` — comparativo lado-a-lado",
        "",
    ])
    write_lf(THIS / "summary.md", "\n".join(out) + "\n")
    print()
    print(f"summary.md: {THIS / 'summary.md'}")
    print()
    print(f"Totais: baseline={total_bl} t02={total_t02} fork={total_fork}")
    print(f"        delta vs t02: {total_fork-total_t02:+d} bytes "
          f"({(total_fork-total_t02)/total_t02*100:+.1f}%)")
    print(f"RT: {rt_pass}/{len(results)}")


if __name__ == "__main__":
    main()
