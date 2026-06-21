"""Sub-exp 08 — Granularidades finas (ms/us/ns).

Estende pipeline pra detectar e processar fractional time.
Demonstra sufixos multi-char (`ms`, `us`, `ns`) onde aplicaveis.

Roda em 8 datasets (backward compat + 3 novos).
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
    ("D11a-datas-dia",        42,   "day; backward compat"),
    ("D11b-datas-borda",      59,   "day; bordas; backward compat"),
    ("D11c-datas-mensal",     22,   "day; mensal; backward compat"),
    ("D11d-datetime-min",     34,   "second/minute; backward compat"),
    ("D11e-datetime-mensal",  34,   "second/mensal; backward compat"),
    ("D11f-datetime-ms",      None, "ms; cadencia 1s (escala s)"),
    ("D11g-datetime-us",      None, "us; cadencia 1ms (escala ms — multi-char)"),
    ("D11h-datetime-ns",      None, "ns; cadencia 1us (escala us — multi-char)"),
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
             f"input: {len(linhas)} lines, decoded: {len(decoded)} lines\n"
             + ("" if rt else "\nDifferences:\n" + "\n".join(
                 f"  [{i}] {linhas[i]!r} != {decoded[i] if i < len(decoded) else '<missing>'!r}"
                 for i in range(max(len(linhas), len(decoded)))
                 if i >= min(len(linhas), len(decoded)) or linhas[i] != decoded[i]
             ) + "\n"))

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

    print("=== 08-granularidades-finas ===\n")
    print("Estende pipeline pra ms/us/ns com sufixos multi-char.\n")

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

    rt_all = all(r["rt"] for r in results)
    backward_ok = all(r["match"] for r in results)

    # === result.md
    out = [
        "# Resultado — 08-granularidades-finas",
        "",
        "Pipeline staged estendido pra **ms/us/ns** com sufixos multi-char",
        "(`ms`, `us`, `ns`). 8 datasets testados (5 backward compat + 3 novos).",
        "",
        "## Tabela consolidada",
        "",
        "| Dataset | Granul. | Linhas | Raw | B inter | C inter | B==C? | TCF puro | TCF B | TCF C | Esperado | RT |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|",
    ]
    for r in results:
        exp = str(r['expected']) if r['expected'] is not None else "—"
        out.append(
            f"| {r['dataset']} | {r['meta']['granularity']} | "
            f"{r['linhas']} | {r['raw']} | "
            f"{r['b_inter']} | {r['c_inter']} | "
            f"{'sim' if r['b_eq_c'] else '**nao**'} | "
            f"{r['tcf_puro']} | {r['tcf_b']} | **{r['tcf_c']}** | "
            f"{exp} | {'OK' if r['rt'] else 'FAIL'} |"
        )
    out.append("")

    out.append("## Stage C outputs (so' os 3 novos)")
    out.append("")
    for ds_name in ("D11f-datetime-ms", "D11g-datetime-us", "D11h-datetime-ns"):
        c_path = out_root / ds_name / "stage-C.txt"
        c_text = c_path.read_text(encoding="utf-8").rstrip()
        out.append(f"### {ds_name}")
        out.append("```")
        out.append(c_text)
        out.append("```")
        out.append("")

    out.append("## Linguagem das escalas (cumulativa apos sub-exps 03-08)")
    out.append("")
    out.append("| Sufixo | Significado | Valido em granularidade |")
    out.append("|---|---|---|")
    out.append("| (none) | unidade base detectada em A | sempre |")
    out.append("| `Y` | ano | sempre |")
    out.append("| `M` | mes (capital pra distinguir minuto) | sempre |")
    out.append("| `D` | dia | second, ms, us, ns |")
    out.append("| `h` | hora | second, ms, us, ns |")
    out.append("| `m` | minuto | second, ms, us, ns |")
    out.append("| `s` | segundo | ms, us, ns |")
    out.append("| `ms` | milissegundo (multi-char) | us, ns |")
    out.append("| `us` | microssegundo (multi-char) | ns |")
    out.append("| sinal `-` | negativo | sempre |")
    out.append("")

    out.append("## Hipoteses")
    out.append("")
    out.append(f"- **H1 (RT preservado em 8 datasets)**: "
               f"{'CONFIRMADA' if rt_all else 'REFUTADA'} "
               f"({sum(r['rt'] for r in results)}/{len(results)} OK).")
    out.append(f"- **H2 (backward compat byte-exato D11a-e)**: "
               f"{'CONFIRMADA' if backward_ok else 'REFUTADA'}.")
    out.append(f"- **H3 (Stage A detecta ms/us/ns)**: "
               f"D11f={results[5]['meta']['granularity']}, "
               f"D11g={results[6]['meta']['granularity']}, "
               f"D11h={results[7]['meta']['granularity']}.")
    out.append("")

    out.append("## Conexoes")
    out.append("")
    out.append("- [`../07-cadencia-mensal-datetime-D11e/`](../07-cadencia-mensal-datetime-D11e/) — base do pipeline")
    out.append("- [`../README.md`](../README.md) — T01")

    write_lf(THIS / "result.md", "\n".join(out) + "\n")
    print(f"result.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()
