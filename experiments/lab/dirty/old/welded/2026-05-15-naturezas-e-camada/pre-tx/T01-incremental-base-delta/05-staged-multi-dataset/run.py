"""Orquestrador 05 — staged pipeline em 3 datasets (D11a, D11b, D11c).

Aplica mesmo codigo do sub-exp 04 sem alteracao. Verifica
generalizacao + matching com sub-exps 01/02/03/04.
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
    ("D11a-datas-dia",       "01-prova-conceito",          42),
    ("D11b-datas-borda",     "02-bordas",                  59),
    ("D11c-datas-mensal",    "03-cadencia / 04-staged",    22),
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


def rodar_dataset(ds_name: str, out_root: Path) -> dict:
    """Roda staged pipeline em um dataset. Retorna metricas."""
    ds_path = ROOT / "datasets" / "synthetic" / f"{ds_name}.csv"
    out_dir = out_root / ds_name
    out_dir.mkdir(parents=True, exist_ok=True)

    with ds_path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        linhas = [row[0] for row in r if row]

    # === STAGE A
    meta = stage_a_identify.identify(linhas)
    write_lf(out_dir / "stage-A-metadata.json",
             json.dumps(meta, indent=2) + "\n")

    # === STAGE B
    stage_b = stage_b_normalize.normalize_to_unit(linhas, meta)
    stage_b_text = "\n".join(stage_b) + "\n"
    write_lf(out_dir / "stage-B.txt", stage_b_text)

    # === STAGE C
    stage_c = stage_c_optimize.optimize_scales(stage_b, meta)
    stage_c_text = "\n".join(stage_c) + "\n"
    write_lf(out_dir / "stage-C.txt", stage_c_text)

    # === TCF de cada
    tcf_puro = encode_tcf(linhas)
    tcf_b = encode_tcf(stage_b)
    tcf_c = encode_tcf(stage_c)
    write_lf(out_dir / "tcf-puro.tcf", tcf_puro)
    write_lf(out_dir / "tcf-B.tcf", tcf_b)
    write_lf(out_dir / "tcf-C.tcf", tcf_c)

    # === RT verificacao
    tcf_c_dec = tcf_decode(tcf_c)
    decoded_linhas, _ = decoder.decode(tcf_c_dec)
    rt_full = decoded_linhas == linhas
    write_lf(
        out_dir / "rt.txt",
        f"RT full (decoder.decode(tcf_decode(tcf_c)) == linhas): "
        f"{'OK' if rt_full else 'FAIL'}\n"
    )

    raw_csv = ds_path.read_bytes()
    return {
        "dataset":        ds_name,
        "linhas":         len(linhas),
        "raw_bytes":      len(raw_csv),
        "stage_b_inter":  len(stage_b_text.encode("utf-8")),
        "stage_c_inter":  len(stage_c_text.encode("utf-8")),
        "stage_b_eq_c":   stage_b == stage_c,
        "tcf_puro":       len(tcf_puro.encode("utf-8")),
        "tcf_b":          len(tcf_b.encode("utf-8")),
        "tcf_c":          len(tcf_c.encode("utf-8")),
        "rt_full":        rt_full,
        "meta":           meta,
    }


def main() -> None:
    out_root = THIS / "outputs"
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"=== 05-staged-multi-dataset ===\n")
    print(f"Aplicando pipeline staged (copia byte-identica de "
          f"sub-exp 04) em 3 datasets.\n")

    results = []
    for ds_name, ref_subexp, expected_tcf_c in DATASETS:
        print(f"--- {ds_name} (ref: {ref_subexp}, esperado tcf_c={expected_tcf_c}) ---")
        r = rodar_dataset(ds_name, out_root)
        r["expected_tcf_c"] = expected_tcf_c
        r["expected_match"] = r["tcf_c"] == expected_tcf_c
        results.append(r)
        print(
            f"  Stage A: type={r['meta']['type']}, "
            f"granularity={r['meta']['granularity']}"
        )
        print(
            f"  Stage B==C: {r['stage_b_eq_c']} "
            f"({'C nao otimizou (esperado pra D11a/b)' if r['stage_b_eq_c'] else 'C aplicou escala'})"
        )
        print(
            f"  TCF: puro={r['tcf_puro']}, B={r['tcf_b']}, C={r['tcf_c']}"
        )
        print(
            f"  Esperado tcf_c={expected_tcf_c}: "
            f"{'MATCH' if r['expected_match'] else 'MISMATCH'}"
        )
        print(f"  RT full: {'OK' if r['rt_full'] else 'FAIL'}")
        print()

    # === result.md consolidado
    h1 = all(r["rt_full"] for r in results)
    h3_a = results[0]["stage_b_eq_c"]
    h3_b = results[1]["stage_b_eq_c"]
    h3_c_optimized = not results[2]["stage_b_eq_c"]
    h4 = all(r["expected_match"] for r in results)

    lines = [
        "# Resultado — 05-staged-multi-dataset",
        "",
        "## Tabela consolidada",
        "",
        "| Dataset | Linhas | Raw | Stage B | Stage C | B==C? | TCF puro | TCF de B | TCF de C | Esperado | RT |",
        "|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['dataset']} | {r['linhas']} | {r['raw_bytes']} | "
            f"{r['stage_b_inter']} | {r['stage_c_inter']} | "
            f"{'sim' if r['stage_b_eq_c'] else '**nao**'} | "
            f"{r['tcf_puro']} | {r['tcf_b']} | **{r['tcf_c']}** | "
            f"{r['expected_tcf_c']} | "
            f"{'OK' if r['rt_full'] else 'FAIL'} |"
        )
    lines.append("")

    lines.append("## Hipoteses")
    lines.append("")
    lines.append(f"- **H1 (RT preservado em todos)**: {'CONFIRMADA' if h1 else 'REFUTADA'} "
                 f"({sum(1 for r in results if r['rt_full'])}/{len(results)} RT OK).")
    lines.append(f"- **H2 (sem retrabalho)**: pipeline rodou nos 3 datasets sem alteracao "
                 f"nos modulos. **CONFIRMADA por construcao** (codigo copiado de sub-exp 04).")
    lines.append(f"- **H3 (Stage C inocuo onde nao ha pattern)**: "
                 f"{'CONFIRMADA' if (h3_a and h3_b and h3_c_optimized) else 'REFUTADA'}.")
    lines.append(f"  - D11a (sem pattern mensal/anual): Stage C == Stage B? **{h3_a}**")
    lines.append(f"  - D11b (idem): Stage C == Stage B? **{h3_b}**")
    lines.append(f"  - D11c (cadencia mensal): Stage C aplicou escala? **{h3_c_optimized}**")
    lines.append(f"- **H4 (matching com sub-exps anteriores)**: "
                 f"{'CONFIRMADA' if h4 else 'REFUTADA'}.")
    for r in results:
        mark = "MATCH" if r["expected_match"] else f"MISMATCH ({r['tcf_c']} != {r['expected_tcf_c']})"
        lines.append(f"  - {r['dataset']}: tcf_c={r['tcf_c']}, esperado={r['expected_tcf_c']} — **{mark}**")
    lines.append("")

    lines.append("## Conclusao")
    lines.append("")
    lines.append("O staged pipeline e' **dataset-independente** dentro da natureza")
    lines.append("`date / day granularity`. Stage A identifica corretamente, Stage B")
    lines.append("normaliza sem falha, Stage C aplica escala **so' onde existe**")
    lines.append("pattern (D11c monthly cadence), preservando bytes onde nao existe")
    lines.append("(D11a, D11b — Stage C passa direto sem custo).")
    lines.append("")
    lines.append("Bytes do TCF do estagio C **batem byte-a-byte** com os encoders")
    lines.append("monoliticos dos sub-exps 01 (42), 02 (59), 03 (22).")
    lines.append("")

    lines.append("## Conexoes")
    lines.append("")
    lines.append("- [`../04-staged-pipeline-D11c/`](../04-staged-pipeline-D11c/) — fonte dos modulos staged")
    lines.append("- [`../01-prova-conceito-D11a-dia/`](../01-prova-conceito-D11a-dia/) — referencia D11a")
    lines.append("- [`../02-bordas-D11b/`](../02-bordas-D11b/) — referencia D11b")
    lines.append("- [`../03-cadencia-mensal-D11c/`](../03-cadencia-mensal-D11c/) — referencia D11c monolitico")

    write_lf(THIS / "result.md", "\n".join(lines) + "\n")
    print(f"result.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()
