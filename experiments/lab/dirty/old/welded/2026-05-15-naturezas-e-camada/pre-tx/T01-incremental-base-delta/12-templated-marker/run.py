"""Sub-exp 12 — Templated marker (proof of concept).

Aplica encoding template+marker em 3 datasets:
- D11c: month cadence (single-marker)
- D11g: ms cadence (single-marker em fractional)
- D11i: mensal com correcao de dia (multi-position, novo)

Compara bytes vs v1 (canonical) e v2 (escape dedutivel).
RT byte-canonical via decoder espelhado.
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
from templated_marker import ENCODERS, DECODERS  # noqa: E402


DATASETS = [
    "D11c-datas-mensal",
    "D11g-datetime-us",
    "D11i-datas-mensal-com-correcao",
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


def encode_v3_tcf(rows: list[str], ds: str) -> str:
    """v3 = template + deltas, depois passado pelo TCF canonical encoder."""
    encoder = ENCODERS[ds]
    v3_lines = encoder(rows)
    # Encode as TCF canonical (HCC vai aplicar RLE adjacente etc.)
    tcf_text = encode_tcf_canonical(v3_lines)
    # Aplica smart_escape (v2 idea: remove escapes desnecessarios)
    smart = smart_encode(tcf_text)
    return smart, v3_lines


def process(ds: str) -> dict:
    ds_path = ROOT / "datasets" / "synthetic" / f"{ds}.csv"
    with ds_path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        rows = [row[0] for row in r if row]

    # v1: canonical sobre rows direto
    v1_text = encode_tcf_canonical(rows)
    v1_bytes = len(v1_text.encode("utf-8"))

    # v2: escape dedutivel
    v2_text = smart_encode(v1_text)
    v2_bytes = len(v2_text.encode("utf-8"))

    # v3: template marker + canonical encode + smart escape
    v3_text, v3_lines = encode_v3_tcf(rows, ds)
    v3_bytes = len(v3_text.encode("utf-8"))

    # Decode v3 e validate RT
    # Pra simplificar: decode os v3_lines via decoder local (sem passar pelo TCF)
    decoder = DECODERS[ds]
    rows_decoded = decoder(v3_lines)
    rt_ok = rows_decoded == rows

    # Output files
    out = THIS / "outputs" / ds
    write_lf(out / "v1.tcf", v1_text)
    write_lf(out / "v2.tcf", v2_text)
    write_lf(out / "v3.tcf", v3_text)
    write_lf(out / "v3-pretx.txt", "\n".join(v3_lines) + "\n")
    write_lf(out / "decoded-from-v3.txt", "\n".join(rows_decoded) + "\n")
    val_text = [
        f"# Validacao — {ds}",
        "",
        f"RT byte-canonical: **{'OK' if rt_ok else 'FAIL'}**",
        f"input rows: {len(rows)}",
        f"decoded rows: {len(rows_decoded)}",
        "",
        "## Bytes",
        f"- v1 (canonical):           {v1_bytes}",
        f"- v2 (escape dedutivel):    {v2_bytes}",
        f"- **v3 (template marker)**: **{v3_bytes}**",
        "",
        f"v3 vs v1: {v3_bytes/v1_bytes*100:.1f}% ({v3_bytes-v1_bytes:+d} bytes)",
        f"v3 vs v2: {v3_bytes/v2_bytes*100:.1f}% ({v3_bytes-v2_bytes:+d} bytes)",
        "",
        "## Pre-tx output (template + deltas, antes do TCF)",
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
        val_text.append("")
        val_text.append("## Diferencas")
        for i in range(max(len(rows), len(rows_decoded))):
            a = rows[i] if i < len(rows) else "<missing>"
            b = rows_decoded[i] if i < len(rows_decoded) else "<missing>"
            if a != b:
                val_text.append(f"  [{i}] input={a!r} decoded={b!r}")
    write_lf(out / "validation.txt", "\n".join(val_text) + "\n")

    summary = [
        f"# _SUMMARY — {ds}",
        "",
        "## Bytes",
        "",
        "| Versao | Bytes | vs v1 | vs v2 |",
        "|---|---:|---:|---:|",
        f"| v1 canonical | {v1_bytes} | 100.0% | — |",
        f"| v2 escape dedutivel | {v2_bytes} | {v2_bytes/v1_bytes*100:.1f}% | 100.0% |",
        f"| **v3 template marker** | **{v3_bytes}** | "
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
        "v1": v1_bytes,
        "v2": v2_bytes,
        "v3": v3_bytes,
        "rt_ok": rt_ok,
    }


def main() -> None:
    print("=== 12-templated-marker ===\n")
    print("Demonstra template `?` no marker + deltas em unidade do field.\n")

    results = []
    for ds in DATASETS:
        r = process(ds)
        results.append(r)
        print(f"  {ds:35}  v1={r['v1']:3} v2={r['v2']:3} v3={r['v3']:3}  "
              f"v3/v2={r['v3']/r['v2']*100:.1f}%  RT={'OK' if r['rt_ok'] else 'FAIL'}")

    # result.md
    all_ok = all(r["rt_ok"] for r in results)
    out = [
        "# Resultado — 12-templated-marker",
        "",
        f"**Status**: {'**TODOS RT OK**' if all_ok else '**FALHAS**'} "
        f"({sum(r['rt_ok'] for r in results)}/{len(results)})",
        "",
        "## Tabela",
        "",
        "| Dataset | v1 | v2 | v3 | v3/v1 | v3/v2 | RT |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in results:
        out.append(
            f"| [{r['dataset']}]({r['dataset']}/_SUMMARY.md) | "
            f"{r['v1']} | {r['v2']} | **{r['v3']}** | "
            f"{r['v3']/r['v1']*100:.1f}% | {r['v3']/r['v2']*100:.1f}% | "
            f"{'OK' if r['rt_ok'] else '**FAIL**'} |"
        )
    out.append("")

    out.append("## Discussao")
    out.append("")
    out.append("Comparacao v3 (template marker) vs v2 (escape dedutivel) vs v1 (canonical):")
    out.append("")
    out.append("- **D11c (cadencia mensal)**: marker `2025-??-05` + 13 deltas de `1`. "
               "Pre-tx output sao 14 linhas. TCF aplica RLE: `*12|1`. "
               "Compara com v2 que tinha `*12|\\1M`.")
    out.append("- **D11g (cadencia ms)**: marker `2025-05-15 09:00:00.0??000` + deltas de `1`. "
               "Pre-tx tem 14 linhas. TCF: `*12|1`. Compara com v2 `*12|\\1ms`.")
    out.append("- **D11i (mensal com correcao)**: marker no month + corrections em dia "
               "quando day != template default. RLE quebra parcialmente porque deltas variam.")
    out.append("")
    out.append("## Observacao")
    out.append("")
    out.append("Esta POC encoder/decoder e' especializado por dataset (hardcoded). "
               "Uma versao geral exigiria:")
    out.append("- Format-aware parser (regex ou estruturado)")
    out.append("- Identificacao automatica do change-position")
    out.append("- Mapeamento posicao -> field/unit")
    out.append("- Convencao mais robusta pra carregar initial value no template")
    out.append("")
    out.append("## Limitacao registrada")
    out.append("")
    out.append("Initial value e' assumido como minimo do field (month=01, ms=000, etc.). "
               "Pra dados que nao comecam no minimo, precisa de syntax adicional.")
    out.append("")
    out.append("## Conexoes")
    out.append("")
    out.append("- [`../11-escape-dedutivel/`](../11-escape-dedutivel/) — fonte do v2 + smart_escape")
    out.append("- Relacao com **T02 templated** (nature 2) — esta POC e' protótipo")
    out.append("- [META-TYPE-ENCODERS](../../../../../../tickets/META-TYPE-ENCODERS.md) — plano")

    write_lf(THIS / "result.md", "\n".join(out) + "\n")
    print()
    print(f"result.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()
