"""Orquestrador do sub-experimento 02-bordas-D11b.

Mesmo pipeline do 01, mas com dataset D11b focado em bordas
mes/ano e ano bissexto. Valida se encoder v0 (dia-only) preserva
RT byte-canonical em transicoes calendar.
"""

from __future__ import annotations

import csv
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

import pretx_dia  # noqa: E402
import postx_dia  # noqa: E402


DATASET_NAME = "D11b-datas-borda"


def encode_com_debug(values: list[str], header: str = "val") -> dict:
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())
    tokens, _ = processar(unicas, min_len=3)
    syn = M8AVirtualRefsSyntax()
    text = syn.encode(values, unicas, tokens, header)
    return {
        "text":   text,
        "unicas": unicas,
        "tokens": tokens,
        "trace":  syn.get_trace(),
        "rede":   syn.get_rede(),
    }


def format_obat_tokens(unicas: list[str], tokens: list) -> str:
    out = ["# OBAT tokenization (debug)\n"]
    out.append("## Strings unicas (ordem de aparicao)\n")
    for i, u in enumerate(unicas):
        out.append(f"  [{i}] {u!r}")
    out.append("")
    out.append("## Tokens por string\n")
    for i, tok_list in enumerate(tokens):
        out.append(f"  String [{i}] = {unicas[i]!r}:")
        for j, t in enumerate(tok_list):
            out.append(f"    {j}: {t!r}")
        out.append("")
    return "\n".join(out)


def write_lf(path: Path, content: str) -> None:
    path.write_bytes(content.encode("utf-8"))


def main() -> None:
    ds_path = ROOT / "datasets" / "synthetic" / f"{DATASET_NAME}.csv"
    out_dir = THIS / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== 02-bordas-{DATASET_NAME} ===")
    print(f"dataset: {ds_path}")
    print()

    with ds_path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        linhas = [row[0] for row in r if row]

    write_lf(out_dir / "00-input.txt", "\n".join(linhas) + "\n")
    print(f"00 input:      {len(linhas)} linhas")

    pretx_out = pretx_dia.encode(linhas)
    pretx_text = "\n".join(pretx_out) + "\n"
    write_lf(out_dir / "01-pretx-output.txt", pretx_text)
    print(f"01 pre-tx:     {len(pretx_out)} linhas, "
          f"{len(pretx_text.encode('utf-8'))} bytes")

    debug = encode_com_debug(pretx_out)
    tcf_text = debug["text"]
    write_lf(out_dir / "02-tcf-encoded.tcf", tcf_text)
    print(f"02 tcf encode: {len(tcf_text.encode('utf-8'))} bytes")

    write_lf(
        out_dir / "03-obat-tokens.txt",
        format_obat_tokens(debug["unicas"], debug["tokens"]),
    )
    write_lf(
        out_dir / "04-hcc-trace.txt",
        debug["trace"] + "\n" if debug["trace"] else "(trace vazio)\n",
    )
    write_lf(
        out_dir / "05-hcc-rede.txt",
        debug["rede"] + "\n" if debug["rede"] else "(rede vazia)\n",
    )

    tcf_decoded = tcf_decode(tcf_text)
    write_lf(out_dir / "06-tcf-decoded.txt", "\n".join(tcf_decoded) + "\n")
    tcf_rt = tcf_decoded == pretx_out
    print(f"06 tcf decode: {len(tcf_decoded)} linhas, "
          f"RT vs pre-tx = {'OK' if tcf_rt else 'FAIL'}")

    postx_out = postx_dia.decode(tcf_decoded)
    write_lf(out_dir / "07-postx-output.txt", "\n".join(postx_out) + "\n")

    rt_full = postx_out == linhas
    rt_text = f"RT full: {'OK' if rt_full else 'FAIL'}\n\n"
    rt_text += f"input lines:  {len(linhas)}\n"
    rt_text += f"output lines: {len(postx_out)}\n\n"
    if not rt_full:
        rt_text += "Diferencas:\n"
        for i in range(max(len(linhas), len(postx_out))):
            a = linhas[i] if i < len(linhas) else "<missing>"
            b = postx_out[i] if i < len(postx_out) else "<missing>"
            if a != b:
                rt_text += f"  linha {i}: input={a!r} != postx={b!r}\n"
    write_lf(out_dir / "08-rt-result.txt", rt_text)
    print(f"08 RT full:    {'OK' if rt_full else 'FAIL'}")

    raw_csv = ds_path.read_bytes()
    pretx_b = pretx_text.encode("utf-8")
    tcf_b = tcf_text.encode("utf-8")
    tcf_puro_text = encode_com_debug(linhas)["text"]
    tcf_puro_b = tcf_puro_text.encode("utf-8")

    cmp_md = [
        f"# Bytes — {DATASET_NAME} ({len(linhas)} linhas YYYY-MM-DD, bordas mes/ano + leap year)",
        "",
        "| Etapa | Bytes | vs raw csv | vs TCF puro |",
        "|---|---:|---:|---:|",
        f"| Raw CSV | {len(raw_csv)} | 100.0% | — |",
        f"| Pre-tx output | {len(pretx_b)} | "
        f"{len(pretx_b)/len(raw_csv)*100:.1f}% | — |",
        f"| TCF puro | {len(tcf_puro_b)} | "
        f"{len(tcf_puro_b)/len(raw_csv)*100:.1f}% | 100.0% |",
        f"| **Pre-tx + TCF** | **{len(tcf_b)}** | "
        f"**{len(tcf_b)/len(raw_csv)*100:.1f}%** | "
        f"**{len(tcf_b)/len(tcf_puro_b)*100:.1f}%** |",
        "",
        f"RT full: **{'OK' if rt_full else 'FAIL'}**",
    ]
    write_lf(out_dir / "bytes-comparison.md", "\n".join(cmp_md) + "\n")

    result_md = [
        f"# Resultado — 02-bordas-{DATASET_NAME}",
        "",
        f"Dataset com {len(linhas)} linhas YYYY-MM-DD, exercitando bordas "
        f"de mes/ano (incluindo Feb 29 em ano bissexto 2024).",
        "",
        "## Bordas exercitadas",
        "",
        "- Jan→Feb (mes 31 dias): 2024-01-31 → 2024-02-01",
        "- Feb 29 (ano bissexto 2024): 2024-02-28 → 2024-02-29",
        "- Feb 29 → Mar 1 (leap): 2024-02-29 → 2024-03-01",
        "- Year boundary: 2024-12-31 → 2025-01-01 (e 2025→2026)",
        "- Feb 28 → Mar 1 (non-leap): 2025-02-28 → 2025-03-01",
        "- Jan 31 → Mar 1 (com Feb non-leap): 2026-01-31 → 2026-02-28 → 2026-03-01",
        "",
        "## Bytes",
        "",
        "| Etapa | Bytes | vs raw csv | vs TCF puro |",
        "|---|---:|---:|---:|",
        f"| Raw CSV | {len(raw_csv)} | 100.0% | — |",
        f"| Pre-tx output | {len(pretx_b)} | "
        f"{len(pretx_b)/len(raw_csv)*100:.1f}% | — |",
        f"| TCF puro | {len(tcf_puro_b)} | "
        f"{len(tcf_puro_b)/len(raw_csv)*100:.1f}% | 100.0% |",
        f"| **Pre-tx + TCF** | **{len(tcf_b)}** | "
        f"**{len(tcf_b)/len(raw_csv)*100:.1f}%** | "
        f"**{len(tcf_b)/len(tcf_puro_b)*100:.1f}%** |",
        "",
        "## Roundtrip",
        "",
        f"- TCF roundtrip (pre-tx → tcf encode → tcf decode == pre-tx): "
        f"**{'OK' if tcf_rt else 'FAIL'}**",
        f"- RT full (pos-tx output == input): **{'OK' if rt_full else 'FAIL'}**",
        "",
        "## Conclusao desta iteracao",
        "",
        f"- H1 (RT preserva bordas calendar): "
        f"**{'CONFIRMADA' if rt_full else 'REFUTADA'}**.",
        f"- H2 (pre-tx + TCF < TCF puro): "
        f"**{'CONFIRMADA' if len(tcf_b) < len(tcf_puro_b) else 'REFUTADA'}** "
        f"({len(tcf_b)} vs {len(tcf_puro_b)} bytes).",
        "",
        "Comparacao com 01-D11a (12 linhas, sem bordas):",
        f"- D11a: raw=136, pretx=34, tcf_puro=87, pretx+tcf=42",
        f"- D11b: raw={len(raw_csv)}, pretx={len(pretx_b)}, "
        f"tcf_puro={len(tcf_puro_b)}, pretx+tcf={len(tcf_b)}",
        "",
        "## Debug",
        "",
        "Estagios intermediarios em `outputs/` (regeneravel via `run.py`):",
        "- `03-obat-tokens.txt`, `04-hcc-trace.txt`, `05-hcc-rede.txt`",
        "",
        "## Conexoes",
        "",
        "- [`README.md`](README.md) — pergunta cientifica + metodo",
        "- [`../README.md`](../README.md) — T01 macro pai",
        "- [`../01-prova-conceito-D11a-dia/`](../01-prova-conceito-D11a-dia/) — sub-exp 01 (encoder copiado dali)",
    ]
    write_lf(THIS / "result.md", "\n".join(result_md) + "\n")
    print()
    print(f"result.md: {THIS / 'result.md'}")
    print(f"Bytes: raw={len(raw_csv)}, pretx={len(pretx_b)}, "
          f"tcf_puro={len(tcf_puro_b)}, pretx+tcf={len(tcf_b)}")


if __name__ == "__main__":
    main()
