"""Sub-exp 07 — Cadencia mensal em datetime (D11e).

Roda em D11c (day mensal), D11d (second minute), D11e (second
mensal — novo). Hipotese: D11e mostra ganho REAL de escala `1M`
em second-granularity (lower varia / higher exato).
"""

from __future__ import annotations

import csv
import json
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[6]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(THIS))

from tcf import decode as tcf_decode  # noqa: E402
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar  # noqa: E402

import stage_a_identify  # noqa: E402
import stage_b_normalize  # noqa: E402
import stage_c_optimize  # noqa: E402
import decoder  # noqa: E402


DATASETS = [
    ("D11c-datas-mensal",    22, "day  /mensal — escala 1M dia"),
    ("D11d-datetime-min",    34, "second/minute — escala 1m (B==C bytes)"),
    ("D11e-datetime-mensal", None, "second/mensal — DEMO escala 1M segundo"),
]


def encode_tcf(values: list[str]) -> str:
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())
    tokens, _ = processar(unicas, min_len=3)
    syn = M8AVirtualRefsSyntax()
    return syn.encode(values, unicas, tokens, "val")


def write_lf(path: Path, content: str) -> None:
    path.write_bytes(content.encode("utf-8"))


def rodar(ds_name: str, out_root: Path) -> dict:
    ds_path = ROOT / "datasets" / "synthetic" / f"{ds_name}.csv"
    out_dir = out_root / ds_name
    out_dir.mkdir(parents=True, exist_ok=True)

    with ds_path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        linhas = [row[0] for row in r if row]

    meta = stage_a_identify.identify(linhas)
    write_lf(out_dir / "stage-A-metadata.json",
             json.dumps(meta, indent=2) + "\n")

    stage_b = stage_b_normalize.normalize_to_unit(linhas, meta)
    stage_b_text = "\n".join(stage_b) + "\n"
    write_lf(out_dir / "stage-B.txt", stage_b_text)

    stage_c = stage_c_optimize.optimize_scales(stage_b, meta)
    stage_c_text = "\n".join(stage_c) + "\n"
    write_lf(out_dir / "stage-C.txt", stage_c_text)

    tcf_puro = encode_tcf(linhas)
    tcf_b = encode_tcf(stage_b)
    tcf_c = encode_tcf(stage_c)
    write_lf(out_dir / "tcf-puro.tcf", tcf_puro)
    write_lf(out_dir / "tcf-B.tcf", tcf_b)
    write_lf(out_dir / "tcf-C.tcf", tcf_c)

    decoded, _ = decoder.decode(tcf_decode(tcf_c))
    rt = decoded == linhas
    write_lf(out_dir / "rt.txt",
             f"RT: {'OK' if rt else 'FAIL'}\n"
             f"input: {len(linhas)} lines, decoded: {len(decoded)} lines\n")

    raw = ds_path.read_bytes()
    return {
        "dataset": ds_name,
        "meta": meta,
        "linhas": len(linhas),
        "raw": len(raw),
        "b_inter": len(stage_b_text.encode("utf-8")),
        "c_inter": len(stage_c_text.encode("utf-8")),
        "b_eq_c": stage_b == stage_c,
        "tcf_puro": len(tcf_puro.encode("utf-8")),
        "tcf_b": len(tcf_b.encode("utf-8")),
        "tcf_c": len(tcf_c.encode("utf-8")),
        "rt": rt,
    }


def main() -> None:
    out_root = THIS / "outputs"
    out_root.mkdir(parents=True, exist_ok=True)

    print("=== 07-cadencia-mensal-datetime-D11e ===\n")
    print("Hipotese: D11e (second/mensal) mostra ganho REAL de escala\n"
          "porque lower unit varia (segundos por mes diferem) mas\n"
          "higher unit (mes) e' exato.\n")

    results = []
    for ds, expected, note in DATASETS:
        print(f"--- {ds} ({note}) ---")
        r = rodar(ds, out_root)
        r["expected"] = expected
        r["match"] = (expected is None) or (r["tcf_c"] == expected)
        results.append(r)
        print(f"  A: granularity={r['meta']['granularity']}")
        print(f"  B == C: {r['b_eq_c']}")
        print(f"  TCF: puro={r['tcf_puro']}, B={r['tcf_b']}, C={r['tcf_c']}")
        if expected is not None:
            mark = "MATCH" if r['match'] else f"MISMATCH (esperado {expected})"
            print(f"  Backward compat: {mark}")
        print(f"  RT: {'OK' if r['rt'] else 'FAIL'}")
        print()

    # === Foco em D11e (a hipotese deste sub-exp)
    d11e = results[2]
    ganho_c_vs_b = (1 - d11e["tcf_c"] / d11e["tcf_b"]) * 100
    h2 = ganho_c_vs_b >= 50

    # === result.md
    rt_all = all(r["rt"] for r in results)
    backward_ok = results[0]["match"] and results[1]["match"]

    out = [
        "# Resultado — 07-cadencia-mensal-datetime-D11e",
        "",
        "## Tabela consolidada",
        "",
        "| Dataset | Granul. | Linhas | Raw | B inter | C inter | B==C? | TCF puro | TCF B | TCF C | Ganho C vs B |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|",
    ]
    for r in results:
        gain = (1 - r["tcf_c"] / r["tcf_b"]) * 100 if r["tcf_b"] else 0
        out.append(
            f"| {r['dataset']} | {r['meta']['granularity']} | "
            f"{r['linhas']} | {r['raw']} | "
            f"{r['b_inter']} | {r['c_inter']} | "
            f"{'sim' if r['b_eq_c'] else '**nao**'} | "
            f"{r['tcf_puro']} | {r['tcf_b']} | **{r['tcf_c']}** | "
            f"**{gain:+.1f}%** |"
        )
    out.append("")

    out.append("## Stage outputs (visuais)")
    out.append("")
    for r in results:
        b_path = out_root / r["dataset"] / "stage-B.txt"
        c_path = out_root / r["dataset"] / "stage-C.txt"
        b_text = b_path.read_text(encoding="utf-8").rstrip()
        c_text = c_path.read_text(encoding="utf-8").rstrip()
        out.append(f"### {r['dataset']}")
        out.append("")
        out.append("**Stage B (em unidade base):**")
        out.append("```")
        out.append(b_text)
        out.append("```")
        out.append("")
        out.append("**Stage C (com escalas):**")
        out.append("```")
        out.append(c_text)
        out.append("```")
        out.append("")

    out.append("## Hipoteses")
    out.append("")
    out.append(f"- **H1 (RT preservado)**: {'CONFIRMADA' if rt_all else 'REFUTADA'} "
               f"({sum(r['rt'] for r in results)}/{len(results)} OK).")
    out.append(f"- **H2 (escala vence em D11e)**: "
               f"{'CONFIRMADA' if h2 else 'REFUTADA / insuficiente'}.")
    out.append(f"  - D11e Stage B: {d11e['tcf_b']} bytes")
    out.append(f"  - D11e Stage C: {d11e['tcf_c']} bytes")
    out.append(f"  - Ganho: {ganho_c_vs_b:+.1f}% (negativo = C maior).")
    out.append(f"- **H3 (backward compat D11c/D11d)**: "
               f"{'CONFIRMADA' if backward_ok else 'REFUTADA'}.")
    out.append("")

    out.append("## Observacao chave")
    out.append("")
    out.append("Em **granularidade segundo**, escala traz ganho **quando**:")
    out.append("- **Lower unit varia** (segundos por mes: 28/30/31 × 86400 -> 3 valores distintos)")
    out.append("- **Higher unit e' exato** (mes = mes mesmo em durations diferentes)")
    out.append("")
    out.append("D11e satisfaz ambos -> escala vence.")
    out.append("D11d (second/minute) NAO satisfaz primeiro (lower fixo em 60s) -> empate B=C.")
    out.append("D11c (day/mensal) ja' validou padrao analogo em day-granularity.")
    out.append("")

    out.append("## Conexoes")
    out.append("")
    out.append("- [`../06-staged-granularity-second/`](../06-staged-granularity-second/) — encoder source")
    out.append("- [`../03-cadencia-mensal-D11c/`](../03-cadencia-mensal-D11c/) — caso analogo em day")
    out.append("- [`../README.md`](../README.md) — T01 macro pai")

    write_lf(THIS / "result.md", "\n".join(out) + "\n")
    print(f"result.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()
