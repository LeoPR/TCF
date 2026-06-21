"""Orquestrador 06 — staged pipeline estendido pra granularidade SEGUNDO.

Roda em:
- D11a (day) — backward compat
- D11b (day, bordas) — backward compat
- D11c (day, mensal) — backward compat
- D11d (second, minute cadence) — NEW

Verifica:
1. Stage A identifica corretamente em todos
2. Stage B normaliza em unidade detectada (day ou second)
3. Stage C otimiza onde encaixa
4. RT preserva todos
5. Bytes batem com sub-exps anteriores (D11a/b/c) e novo (D11d)
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
    # (name, expected_tcf_c_bytes_from_prior_subexp, comentario)
    ("D11a-datas-dia",        42,  "day; sem pattern; backward compat"),
    ("D11b-datas-borda",      59,  "day; bordas; backward compat"),
    ("D11c-datas-mensal",     22,  "day; mensal; backward compat"),
    ("D11d-datetime-min",     None, "second; minuto; primeiro dataset granularity=second"),
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
             f"RT full: {'OK' if rt else 'FAIL'}\n"
             f"input lines: {len(linhas)}\n"
             f"decoded lines: {len(decoded)}\n")

    raw = ds_path.read_bytes()
    return {
        "dataset": ds_name,
        "meta": meta,
        "linhas": len(linhas),
        "raw_bytes": len(raw),
        "stage_b_inter": len(stage_b_text.encode("utf-8")),
        "stage_c_inter": len(stage_c_text.encode("utf-8")),
        "stage_b_eq_c": stage_b == stage_c,
        "tcf_puro": len(tcf_puro.encode("utf-8")),
        "tcf_b": len(tcf_b.encode("utf-8")),
        "tcf_c": len(tcf_c.encode("utf-8")),
        "rt": rt,
    }


def main() -> None:
    out_root = THIS / "outputs"
    out_root.mkdir(parents=True, exist_ok=True)

    print("=== 06-staged-granularity-second ===\n")

    results = []
    for ds_name, expected, note in DATASETS:
        print(f"--- {ds_name} ({note}) ---")
        r = rodar_dataset(ds_name, out_root)
        r["expected"] = expected
        r["match"] = (expected is None) or (r["tcf_c"] == expected)
        results.append(r)
        print(f"  A: type={r['meta']['type']}, "
              f"granularity={r['meta']['granularity']}, "
              f"format={r['meta']['format']}")
        print(f"  B == C: {r['stage_b_eq_c']}")
        print(f"  TCF puro={r['tcf_puro']}, B={r['tcf_b']}, C={r['tcf_c']}")
        if expected is not None:
            print(f"  Esperado: {expected} — {'MATCH' if r['match'] else 'MISMATCH'}")
        print(f"  RT: {'OK' if r['rt'] else 'FAIL'}\n")

    # result.md
    h_rt = all(r["rt"] for r in results)
    h_match = all(r["match"] for r in results)
    h_new_gran = results[3]["meta"]["granularity"] == "second"

    lines = [
        "# Resultado — 06-staged-granularity-second",
        "",
        "Pipeline staged estendido pra suportar **granularidade segundo**",
        "alem de dia. Validado em 4 datasets (3 day backward compat + 1",
        "second novo).",
        "",
        "## Tabela consolidada",
        "",
        "| Dataset | Granul. | Linhas | Raw | B inter | C inter | B==C? | TCF puro | TCF B | TCF C | Esperado | RT |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|",
    ]
    for r in results:
        exp = str(r['expected']) if r['expected'] is not None else "—"
        lines.append(
            f"| {r['dataset']} | {r['meta']['granularity']} | "
            f"{r['linhas']} | {r['raw_bytes']} | "
            f"{r['stage_b_inter']} | {r['stage_c_inter']} | "
            f"{'sim' if r['stage_b_eq_c'] else '**nao**'} | "
            f"{r['tcf_puro']} | {r['tcf_b']} | **{r['tcf_c']}** | "
            f"{exp} | {'OK' if r['rt'] else 'FAIL'} |"
        )
    lines.append("")

    lines.append("## Hipoteses")
    lines.append("")
    lines.append(f"- **H1 (RT preservado em todos os 4 datasets)**: "
                 f"{'CONFIRMADA' if h_rt else 'REFUTADA'}.")
    lines.append(f"- **H2 (backward compat: D11a/b/c batem byte-exato com sub-exps anteriores)**: "
                 f"{'CONFIRMADA' if h_match else 'REFUTADA'}.")
    lines.append(f"- **H3 (Stage A identifica granularity=second em D11d)**: "
                 f"{'CONFIRMADA' if h_new_gran else 'REFUTADA'}.")
    lines.append("")

    lines.append("## Observacoes")
    lines.append("")
    r_d11d = results[3]
    lines.append(f"- **D11d** (minute cadence em second granularity): "
                 f"Stage C aplica escala `1m`? "
                 f"{'sim' if not r_d11d['stage_b_eq_c'] else 'nao'}.")
    lines.append(f"- TCF de B (em segundos `60` repetido) e TCF de C "
                 f"(em `1m` repetido) tem tamanhos similares — ambos compactam "
                 f"via repeticao no HCC. Ver `outputs/D11d-datetime-min/`.")
    lines.append("")
    lines.append("## Linguagem das escalas (cumulativo apos sub-exps 03-06)")
    lines.append("")
    lines.append("- Sem letra = unidade base detectada em A (dia ou segundo).")
    lines.append("- `Y` = ano, `M` = mes (capital pra distinguir de minuto).")
    lines.append("- `D` = dia (so' quando granularity=second).")
    lines.append("- `h` = hora, `m` = minuto (so' quando granularity=second).")
    lines.append("- Sinal `-` explicito pra negativos.")
    lines.append("")
    lines.append("## Proximos passos pendentes (escopo NAO deste sub-exp)")
    lines.append("")
    lines.append("- Granularidade milissegundo / microssegundo / nanossegundo (sufixos multi-char `ms`/`us`/`ns`)")
    lines.append("- Timezone handling")
    lines.append("- Mixed-granularity (logs com timestamps + IDs em mesma coluna — improvavel pela diretriz dados-realistas)")
    lines.append("")
    lines.append("## Conexoes")
    lines.append("")
    lines.append("- [`../05-staged-multi-dataset/`](../05-staged-multi-dataset/) — generalizacao day-only")
    lines.append("- [`../04-staged-pipeline-D11c/`](../04-staged-pipeline-D11c/) — staged inicial")

    write_lf(THIS / "result.md", "\n".join(lines) + "\n")
    print(f"result.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()
