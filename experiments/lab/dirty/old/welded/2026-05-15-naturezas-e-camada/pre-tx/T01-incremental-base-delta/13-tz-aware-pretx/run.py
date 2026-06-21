"""Sub-exp 13 — tz-aware pre-tx (POC).

Aplica detect-tz + template-marker em 3 datasets:
- D11j (tz constante Z)
- D11k (tz constante -03:00)
- D11m (tz variavel — fallback no-extract)

Compara bytes v1 (canonical) / v2 (escape dedutivel) / v3 (tz-aware).
RT byte-canonical via decoder local (engenhoca).
"""

from __future__ import annotations

import csv
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
LIB = THIS / "lib"
ROOT = THIS.parents[6]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(LIB))

# Sub-exp 11 lib pra smart_escape (gerar v2)
SUBEXP11_LIB = THIS.parents[0] / "11-escape-dedutivel" / "lib"
sys.path.insert(0, str(SUBEXP11_LIB))

from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar  # noqa: E402

from smart_escape import smart_encode  # noqa: E402
from tz_aware_pretx import auto_encode, auto_decode, detect_mode  # noqa: E402


DATASETS = [
    "D11j-datetime-tz-Z",
    "D11k-datetime-tz-offset",
    "D11m-datetime-tz-variavel",
]


def encode_tcf_canonical(values: list[str]) -> str:
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())
    tokens, _ = processar(unicas, min_len=3)
    syn = M8AVirtualRefsSyntax()
    return syn.encode(values, unicas, tokens, "val")


def write_lf(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def process(ds: str) -> dict:
    ds_path = ROOT / "datasets" / "synthetic" / f"{ds}.csv"
    with ds_path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)  # header
        rows = [row[0] for row in r if row]

    # v1: canonical
    v1_text = encode_tcf_canonical(rows)
    v1_bytes = len(v1_text.encode("utf-8"))

    # v2: smart escape
    v2_text = smart_encode(v1_text)
    v2_bytes = len(v2_text.encode("utf-8"))

    # v3: tz-aware pre-tx + canonical + smart escape
    mode, v3_lines = auto_encode(rows)
    v3_text = smart_encode(encode_tcf_canonical(v3_lines))
    v3_bytes = len(v3_text.encode("utf-8"))

    # RT validation via decoder local
    rows_decoded = auto_decode(mode, v3_lines)
    rt_ok = rows_decoded == rows

    # Outputs per dataset
    out = THIS / "outputs" / ds
    write_lf(out / "v1.tcf", v1_text)
    write_lf(out / "v2.tcf", v2_text)
    write_lf(out / "v3.tcf", v3_text)
    write_lf(out / "v3-pretx.txt", "\n".join(v3_lines) + "\n")
    write_lf(out / "decoded-from-v3.txt", "\n".join(rows_decoded) + "\n")

    val = [
        f"# Validacao — {ds}",
        "",
        f"Mode detectado: **{mode}**",
        f"RT byte-canonical: **{'OK' if rt_ok else 'FAIL'}**",
        f"Input rows: {len(rows)}",
        f"Decoded rows: {len(rows_decoded)}",
        "",
        "## Bytes",
        f"- v1 (canonical):           {v1_bytes}",
        f"- v2 (escape dedutivel):    {v2_bytes}",
        f"- **v3 (tz-aware pre-tx)**: **{v3_bytes}**",
        "",
        f"v3 vs v1: {v3_bytes/v1_bytes*100:.1f}% ({v3_bytes-v1_bytes:+d} bytes)",
        f"v3 vs v2: {v3_bytes/v2_bytes*100:.1f}% ({v3_bytes-v2_bytes:+d} bytes)",
        "",
        "## Pre-tx output (antes do TCF)",
        "",
        "```",
        *v3_lines,
        "```",
        "",
        "## v3.tcf (TCF aplicado sobre o pre-tx + smart escape)",
        "",
        "```",
        v3_text.rstrip(),
        "```",
    ]
    if not rt_ok:
        val.append("")
        val.append("## Diferencas")
        for i in range(max(len(rows), len(rows_decoded))):
            a = rows[i] if i < len(rows) else "<missing>"
            b = rows_decoded[i] if i < len(rows_decoded) else "<missing>"
            if a != b:
                val.append(f"  [{i}] input={a!r} decoded={b!r}")
    write_lf(out / "validation.txt", "\n".join(val) + "\n")

    summary = [
        f"# _SUMMARY — {ds}",
        "",
        f"Mode: **{mode}**",
        "",
        "## Bytes",
        "",
        "| Versao | Bytes | vs v1 | vs v2 |",
        "|---|---:|---:|---:|",
        f"| v1 canonical | {v1_bytes} | 100.0% | — |",
        f"| v2 escape dedutivel | {v2_bytes} | {v2_bytes/v1_bytes*100:.1f}% | 100.0% |",
        f"| **v3 tz-aware pretx** | **{v3_bytes}** | "
        f"**{v3_bytes/v1_bytes*100:.1f}%** | "
        f"**{v3_bytes/v2_bytes*100:.1f}%** |",
        "",
        f"## RT byte-canonical: **{'OK' if rt_ok else 'FAIL'}**",
        "",
        "## v3.tcf",
        "```",
        v3_text.rstrip(),
        "```",
    ]
    write_lf(out / "_SUMMARY.md", "\n".join(summary) + "\n")

    return {
        "dataset": ds,
        "mode": mode,
        "v1": v1_bytes,
        "v2": v2_bytes,
        "v3": v3_bytes,
        "rt_ok": rt_ok,
    }


def main() -> None:
    print("=== 13-tz-aware-pretx ===\n")
    print("Engenhoca: detect tz constante -> extrai template; tz variavel -> no-op.\n")

    results = []
    for ds in DATASETS:
        r = process(ds)
        results.append(r)
        print(
            f"  {ds:32}  mode={r['mode']:13}  "
            f"v1={r['v1']:3} v2={r['v2']:3} v3={r['v3']:3}  "
            f"v3/v2={r['v3']/r['v2']*100:.1f}%  "
            f"RT={'OK' if r['rt_ok'] else 'FAIL'}"
        )

    # result.md
    all_ok = all(r["rt_ok"] for r in results)
    out = [
        "# Resultado — 13-tz-aware-pretx",
        "",
        f"**Status**: {'**TODOS RT OK**' if all_ok else '**FALHAS**'} "
        f"({sum(r['rt_ok'] for r in results)}/{len(results)})",
        "",
        "## Tabela",
        "",
        "| Dataset | mode | v1 | v2 | v3 | v3/v1 | v3/v2 | RT |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in results:
        out.append(
            f"| [{r['dataset']}]({r['dataset']}/_SUMMARY.md) | "
            f"`{r['mode']}` | "
            f"{r['v1']} | {r['v2']} | **{r['v3']}** | "
            f"{r['v3']/r['v1']*100:.1f}% | "
            f"{r['v3']/r['v2']*100:.1f}% | "
            f"{'OK' if r['rt_ok'] else '**FAIL**'} |"
        )
    out.append("")
    out.append("## Discussao")
    out.append("")
    out.append("Comportamento observado por mode:")
    out.append("")
    out.append("- **constant_tz (D11j Z, D11k -03:00)**: tz e' parte estatica do template. "
               "Resto do template usa marker `??` em minuto + deltas (cadence 1 min). "
               "tz se mistura ao template sem custo extra de syntax.")
    out.append("")
    out.append("- **variable_tz (D11m, 3 zonas)**: tz nao e' constante, sem extracao. "
               "Fallback: pre-tx == rows (sem template). v3 acaba igual a v2 nesse caso "
               "porque TCF canonical encoder ainda aplica HCC + smart escape.")
    out.append("")
    out.append("## Limitacoes / aspectos engenhoca")
    out.append("")
    out.append("- Encoder/decoder POC: minute-cadence single-hour (sem carry pra hora/dia)")
    out.append("- Initial minute assumido = 00 (MIN), igual convencao sub-exp 12")
    out.append("- tz suffix detectado por regex simples (`Z` ou `±HH:MM`); zonas nomeadas (UTC, EST) nao cobertas")
    out.append("- D11m fallback nao tenta UTC-normalization (uma alternativa: normalizar e tracker tz separadamente)")
    out.append("")
    out.append("## Conexoes")
    out.append("")
    out.append("- [`../12-templated-marker/`](../12-templated-marker/) — antecedente do template `??`")
    out.append("- [`../11-escape-dedutivel/`](../11-escape-dedutivel/) — smart_escape v2")
    out.append("- Sintaxe `??` aqui e' ilustrativa (engenhoca); preserva semantica de format hint "
               "(`??` = 2-char zero-padded, espelhando minute format `00`-`59`)")
    out.append("- [META-TYPE-ENCODERS](../../../../../../tickets/META-TYPE-ENCODERS.md) — plano-mestre")

    write_lf(THIS / "result.md", "\n".join(out) + "\n")
    print()
    print(f"result.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()
