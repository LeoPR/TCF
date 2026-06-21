"""Sub-exp 11 — Escape dedutivel (TCF v2).

Testa otimizacao "remove escape onde digit-value > current_node_count".

Processo por dataset:
1. Lê tcf-C.tcf do sub-exp 10 (v1 canonical)
2. Aplica smart_encode → v2 sem escapes redundantes
3. Decoda v2 via smart_decode → pretx output
4. Aplica stage_c + stage_b reverses → linhas originais
5. Valida RT vs input + mede savings

Datasets: os 8 D11x do sub-exp 10.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

THIS = Path(__file__).parent
LIB = THIS / "lib"
ROOT = THIS.parents[6]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(LIB))

# Lib do sub-exp 10 (stage A/B/C + decoder)
SUBEXP10_LIB = THIS.parents[0] / "10-pacote-completo-com-validacao" / "lib"
sys.path.insert(0, str(SUBEXP10_LIB))

import stage_a_identify  # noqa: E402
import stage_b_normalize  # noqa: E402
import stage_c_optimize  # noqa: E402
from smart_escape import smart_encode, smart_decode, count_escapes  # noqa: E402


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


def process(ds: str) -> dict:
    # === Input: v1 TCF do sub-exp 10
    v1_path = (THIS.parents[0] / "10-pacote-completo-com-validacao"
               / "outputs" / ds / "5-encoded" / "output.tcf")
    v1_text = v1_path.read_text(encoding="utf-8")

    # === Input: linhas originais do csv (so' pra validacao final)
    ds_csv = ROOT / "datasets" / "synthetic" / f"{ds}.csv"
    with ds_csv.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        linhas_input = [row[0] for row in r if row]

    # === Smart encode: v1 -> v2
    v2_text = smart_encode(v1_text)

    # === Output files
    out = THIS / "outputs" / ds
    write_lf(out / "v1.tcf", v1_text)
    write_lf(out / "v2.tcf", v2_text)

    # === Smart decode v2 -> pretx output
    pretx_out = smart_decode(v2_text)
    write_lf(out / "decoded-v2-pretx.txt", "\n".join(pretx_out) + "\n")

    # === Stage C+B reverses -> linhas
    meta = stage_a_identify.identify(pretx_out[:1])
    b_form = stage_c_optimize.deoptimize_scales(pretx_out, meta)
    linhas_out = stage_b_normalize.denormalize_from_unit(b_form, meta)
    write_lf(out / "decoded-v2-final.txt", "\n".join(linhas_out) + "\n")

    # === Validation
    rt_ok = linhas_out == linhas_input
    v1_bytes = len(v1_text.encode("utf-8"))
    v2_bytes = len(v2_text.encode("utf-8"))
    saving = v1_bytes - v2_bytes
    saving_pct = (saving / v1_bytes * 100) if v1_bytes else 0
    escapes_v1 = count_escapes(v1_text)
    escapes_v2 = count_escapes(v2_text)

    validation = [
        f"# Validacao — {ds}",
        "",
        f"RT byte-canonical: **{'OK' if rt_ok else 'FAIL'}**",
        f"input lines: {len(linhas_input)}",
        f"output lines: {len(linhas_out)}",
        "",
        f"## Bytes",
        f"- v1 (canonical com escapes): **{v1_bytes}** bytes",
        f"- v2 (escape dedutivel):       **{v2_bytes}** bytes",
        f"- saving:                      **{saving}** bytes ({saving_pct:.1f}%)",
        "",
        f"## Escapes",
        f"- v1 escapes (`\\\\digits`): {escapes_v1}",
        f"- v2 escapes restantes:    {escapes_v2}",
        f"- escapes removidos:       **{escapes_v1 - escapes_v2}**",
        "",
        f"## Meta auto-detectado no decode",
        f"{json.dumps(meta, indent=2)}",
    ]
    if not rt_ok:
        validation.append("")
        validation.append("## Diferencas")
        for i in range(max(len(linhas_input), len(linhas_out))):
            a = linhas_input[i] if i < len(linhas_input) else "<missing>"
            b = linhas_out[i] if i < len(linhas_out) else "<missing>"
            if a != b:
                validation.append(f"  [{i}] input={a!r} out={b!r}")
    write_lf(out / "validation.txt", "\n".join(validation) + "\n")

    # === _SUMMARY.md
    summary = [
        f"# _SUMMARY — {ds}",
        "",
        f"## Bytes",
        "",
        "| Versao | Bytes | vs v1 |",
        "|---|---:|---:|",
        f"| v1 canonical (com escapes) | {v1_bytes} | 100.0% |",
        f"| **v2 escape dedutivel** | **{v2_bytes}** | **{v2_bytes/v1_bytes*100:.1f}%** |",
        f"| Savings | {saving} | {saving_pct:.1f}% |",
        "",
        f"## Validacao",
        f"- RT byte-canonical: **{'OK' if rt_ok else 'FAIL'}**",
        f"- Escapes removidos: {escapes_v1 - escapes_v2} (de {escapes_v1} pra {escapes_v2})",
        "",
        f"## Conteudo v1 (com escapes)",
        f"```",
        v1_text.rstrip(),
        f"```",
        "",
        f"## Conteudo v2 (escape dedutivel)",
        f"```",
        v2_text.rstrip(),
        f"```",
    ]
    write_lf(out / "_SUMMARY.md", "\n".join(summary) + "\n")

    return {
        "dataset": ds,
        "v1_bytes": v1_bytes,
        "v2_bytes": v2_bytes,
        "saving": saving,
        "saving_pct": saving_pct,
        "escapes_removed": escapes_v1 - escapes_v2,
        "rt_ok": rt_ok,
    }


def main() -> None:
    print("=== 11-escape-dedutivel ===\n")
    print("Testa otimizacao: remove escape `\\digits` onde valor > current_node_count\n")

    results = []
    for ds in DATASETS:
        r = process(ds)
        results.append(r)
        print(f"  {ds:30}  v1={r['v1_bytes']:3} -> v2={r['v2_bytes']:3} "
              f"({r['saving_pct']:+5.1f}%, -{r['saving']:2} bytes, "
              f"escapes -{r['escapes_removed']:2}) RT={'OK' if r['rt_ok'] else 'FAIL'}")

    # === result.md
    all_ok = all(r["rt_ok"] for r in results)
    total_v1 = sum(r["v1_bytes"] for r in results)
    total_v2 = sum(r["v2_bytes"] for r in results)
    total_saving = total_v1 - total_v2

    out = [
        "# Resultado — 11-escape-dedutivel",
        "",
        f"**Status global**: {'**TODOS RT OK**' if all_ok else '**FALHAS**'} "
        f"({sum(1 for r in results if r['rt_ok'])}/{len(results)})",
        "",
        "## Tabela consolidada",
        "",
        "| Dataset | v1 bytes | v2 bytes | Saving | % | Escapes removidos | RT |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in results:
        out.append(
            f"| [{r['dataset']}]({r['dataset']}/_SUMMARY.md) | "
            f"{r['v1_bytes']} | **{r['v2_bytes']}** | "
            f"{r['saving']} | **{r['saving_pct']:.1f}%** | "
            f"{r['escapes_removed']} | "
            f"{'OK' if r['rt_ok'] else '**FAIL**'} |"
        )
    out.append("| **TOTAL** | "
               f"**{total_v1}** | **{total_v2}** | "
               f"**{total_saving}** | "
               f"**{total_saving/total_v1*100:.1f}%** | "
               f"**{sum(r['escapes_removed'] for r in results)}** | "
               f"{'OK' if all_ok else '**FAIL**'} |")
    out.append("")

    out.append("## Conclusao")
    out.append("")
    out.append(f"Optimizacao 'escape dedutivel' reduz {total_v1} → {total_v2} "
               f"bytes ({total_saving/total_v1*100:.1f}%) nos 8 datasets do T01.")
    out.append(f"RT byte-canonical preservado em {sum(1 for r in results if r['rt_ok'])}/{len(results)} datasets.")
    out.append("")
    out.append("**Princípio aplicado**: `feedback-abstrato-minimal-materializacao`")
    out.append("— digit-run que nao pode ser ref (valor > nodes existentes) e' literal-")
    out.append("sem-ambiguidade, escape `\\` redundante.")
    out.append("")
    out.append("## Limitacao da implementacao (apenas T01)")
    out.append("")
    out.append("Esta implementacao assume **1 lit piece por linha** (T01 incremental).")
    out.append("Compositions complexas (multiple lits, refs intra-body) precisariam de")
    out.append("parser estrutural completo. Caso geral fica como Track 2 L06 — estudo futuro.")
    out.append("")
    out.append("## Backward compat")
    out.append("")
    out.append("**Quebra com TCF v1 atual**: decoder canonical interpretaria digits bare")
    out.append("como refs. Implementacao futura requer:")
    out.append("- Versionamento explicito do formato")
    out.append("- Decisao sobre migracao (in-band header? sentinela?)")
    out.append("- Revalidacao completa do canonical chain D1-D9 -> M14")
    out.append("")
    out.append("## Conexoes")
    out.append("")
    out.append("- [`../10-pacote-completo-com-validacao/`](../10-pacote-completo-com-validacao/) — fonte do v1 tcf-C.tcf")
    out.append("- [meta: feedback-abstrato-minimal-materializacao] — princípio aplicado")
    out.append("- [META-TYPE-ENCODERS L06](../../../../../../tickets/META-TYPE-ENCODERS.md) — estudo Track 2 registrado")

    write_lf(THIS / "result.md", "\n".join(out) + "\n")
    print()
    print(f"result.md: {THIS / 'result.md'}")
    print(f"TOTAL: v1={total_v1} bytes -> v2={total_v2} bytes "
          f"(saving {total_saving} bytes = {total_saving/total_v1*100:.1f}%)")


if __name__ == "__main__":
    main()
