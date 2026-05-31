"""Sub-exp 06 — H-DA-09: testar "always-enable hint" em D1-D9.

Se nenhum dataset regride, hint shape-preserve pode ser sempre on.
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

from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar, TokLit, TokRefPref, TokRefSuf  # noqa: E402
from hcc_fork import HCCForkSeqRLE  # noqa: E402
from obat_fork import processar_with_hint  # noqa: E402


DATASETS = [
    "D1-emails-simples",
    "D2-emails-quote-id",
    "D3-stress-substring",
    "D4-caos-mix",
    "D5-padroes-multiplos",
    "D6-poucos-em-ruido",
    "D7-aninhamento",
    "D8-cabeca-cauda",
    "D9-frequencia-alta",
]


def write_lf(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def load_rows(ds):
    p = ROOT / "datasets" / "synthetic" / f"{ds}.csv"
    with p.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def dedup_preserve_order(values):
    seen = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def fmt_token(tok):
    if isinstance(tok, TokLit):
        return f'L({tok.text!r})'
    if isinstance(tok, TokRefPref):
        return f'P({tok.string_id},{tok.length})'
    if isinstance(tok, TokRefSuf):
        return f'S({tok.string_id},{tok.length})'
    return repr(tok)


def render_tokens(unicas, tokens_por, header):
    out = [header, "", f"strings_unicas: {len(unicas)}", ""]
    width = max(len(s) for s in unicas) + 2
    for i, (s, toks) in enumerate(zip(unicas, tokens_por)):
        out.append(f"  [{i+1:2}] {s!r:<{width}} -> "
                   f"{' + '.join(fmt_token(t) for t in toks)}")
    return "\n".join(out) + "\n"


def process(ds):
    rows = load_rows(ds)
    unicas = dedup_preserve_order(rows)

    tokens_canon, _ = processar(unicas, min_len=3)
    body_baseline = M8AVirtualRefsSyntax().encode(rows, unicas, tokens_canon, "val")
    bytes_baseline = len(body_baseline.encode("utf-8"))

    tokens_fork, _ = processar_with_hint(
        unicas, min_len=3, prefer_shape_consistency=True
    )
    syn_fork = HCCForkSeqRLE()
    body_fork = syn_fork.encode(rows, unicas, tokens_fork, "val")
    bytes_fork = len(body_fork.encode("utf-8"))

    decoded = syn_fork.decode(body_fork)
    rt_ok = (decoded == rows)
    rt_status = "OK" if rt_ok else "FAIL"

    delta = bytes_fork - bytes_baseline

    out = THIS / "outputs" / ds
    write_lf(out / "1-tokens-canonical.txt",
             render_tokens(unicas, tokens_canon, "# Tokens canonical (greedy)"))
    write_lf(out / "2-tokens-fork.txt",
             render_tokens(unicas, tokens_fork, "# Tokens fork (shape-preserve)"))
    write_lf(out / "3-body-baseline.tcf", body_baseline)
    write_lf(out / "4-body-fork.tcf", body_fork)
    write_lf(out / "5-rt-status.txt",
             f"RT: {rt_status}\n"
             f"bytes_baseline: {bytes_baseline}\n"
             f"bytes_fork:     {bytes_fork}\n"
             f"delta:          {delta:+d}\n")

    return {
        "dataset": ds,
        "rows": len(rows),
        "unicas": len(unicas),
        "bytes_baseline": bytes_baseline,
        "bytes_fork": bytes_fork,
        "delta": delta,
        "rt": rt_status,
    }


def main():
    print("=== Sub-exp 06 — Auto-hint regression D1-D9 ===\n")
    results = []
    for ds in DATASETS:
        r = process(ds)
        results.append(r)
        s = '+' if r['delta'] >= 0 else ''
        marker = "  " if r['delta'] <= 0 else "!!"
        print(f"  {marker} {ds:24}  bl={r['bytes_baseline']:4} "
              f"fork={r['bytes_fork']:4} d={s}{r['delta']:4}  RT={r['rt']}")

    total_bl = sum(r['bytes_baseline'] for r in results)
    total_fork = sum(r['bytes_fork'] for r in results)
    regressoes = [r for r in results if r['delta'] > 0]
    ganhos = [r for r in results if r['delta'] < 0]
    empates = [r for r in results if r['delta'] == 0]
    rt_pass = sum(1 for r in results if r['rt'] == 'OK')

    out = [
        "# Resumo — Sub-exp 06 (auto-hint regression D1-D9)",
        "",
        f"baseline total: {total_bl} B",
        f"fork total:     {total_fork} B  ({total_fork-total_bl:+d}, "
        f"{(total_fork-total_bl)/total_bl*100:+.1f}%)",
        "",
        f"RT: {rt_pass}/{len(results)}",
        "",
        f"Ganhos (fork < baseline): {len(ganhos)}",
        f"Empates: {len(empates)}",
        f"**Regressoes**: {len(regressoes)}",
        "",
        "## Tabela",
        "",
        "| Dataset | rows | uniq | baseline | fork | Δ | RT |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in results:
        s = '+' if r['delta'] >= 0 else ''
        flag = " [REGRESSAO]" if r['delta'] > 0 else ""
        out.append(
            f"| [{r['dataset']}]({r['dataset']}/5-rt-status.txt) "
            f"| {r['rows']} | {r['unicas']} | {r['bytes_baseline']} | "
            f"{r['bytes_fork']} | {s}{r['delta']}{flag} | {r['rt']} |"
        )
    out.append("")
    if regressoes:
        out.append("## Regressoes detalhadas")
        out.append("")
        for r in regressoes:
            out.append(f"- **{r['dataset']}**: {r['bytes_baseline']} → "
                       f"{r['bytes_fork']} (+{r['delta']} bytes)")
        out.append("")
        out.append("→ H-DA-09 (always-on) NAO e' safe — hint precisa ser opt-in.")
    else:
        out.append("## Conclusao")
        out.append("")
        out.append("Nenhuma regressao. **H-DA-09 confirmada na forma simples**: "
                   "sempre habilitar `prefer_shape_consistency=True` e' safe.")
    out.append("")
    write_lf(THIS / "summary.md", "\n".join(out) + "\n")
    print()
    print(f"Totais: bl={total_bl} fork={total_fork} d={total_fork-total_bl:+d}")
    print(f"Ganhos={len(ganhos)} Empates={len(empates)} Regressoes={len(regressoes)}")
    print(f"RT: {rt_pass}/{len(results)}")


if __name__ == "__main__":
    main()
