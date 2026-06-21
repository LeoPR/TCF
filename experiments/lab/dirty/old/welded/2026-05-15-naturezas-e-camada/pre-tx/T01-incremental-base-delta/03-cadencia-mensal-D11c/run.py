"""Orquestrador 03-cadencia-mensal-D11c.

Roda 3 pipelines pra comparacao:
1. TCF puro (sem pre-tx)
2. Pre-tx v0 (dia-only) + TCF
3. Pre-tx v1 (escalas dia/M/Y) + TCF

Hipotese central: v1 vence v0 em cadencia mensal (repeticao exata
de `1M` vs dias varios).
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

import pretx_dia  # noqa: E402  (v0)
import postx_dia  # noqa: E402  (v0)
import pretx_dia_mes_ano  # noqa: E402  (v1)
import postx_dia_mes_ano  # noqa: E402  (v1)


DATASET_NAME = "D11c-datas-mensal"


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
    for i, u in enumerate(unicas):
        out.append(f"  [{i}] {u!r}")
    out.append("")
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

    print(f"=== 03-cadencia-mensal-{DATASET_NAME} ===")
    print(f"dataset: {ds_path}")
    print()

    with ds_path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        linhas = [row[0] for row in r if row]

    write_lf(out_dir / "00-input.txt", "\n".join(linhas) + "\n")
    print(f"00 input: {len(linhas)} linhas")

    # === Pipeline V0: pre-tx dia-only + TCF
    pretx_v0 = pretx_dia.encode(linhas)
    pretx_v0_text = "\n".join(pretx_v0) + "\n"
    write_lf(out_dir / "01a-pretx-v0.txt", pretx_v0_text)
    debug_v0 = encode_com_debug(pretx_v0)
    tcf_v0_text = debug_v0["text"]
    write_lf(out_dir / "02a-tcf-v0.tcf", tcf_v0_text)
    postx_v0 = postx_dia.decode(tcf_decode(tcf_v0_text))
    write_lf(out_dir / "06a-postx-v0.txt", "\n".join(postx_v0) + "\n")
    rt_v0 = postx_v0 == linhas
    write_lf(out_dir / "07-rt-v0.txt",
             f"RT v0: {'OK' if rt_v0 else 'FAIL'}\n")
    print(f"v0 (dia-only):   pretx={len(pretx_v0_text.encode('utf-8'))} bytes, "
          f"tcf={len(tcf_v0_text.encode('utf-8'))} bytes, "
          f"RT={'OK' if rt_v0 else 'FAIL'}")

    # === Pipeline V1: pre-tx dia/M/Y + TCF
    pretx_v1 = pretx_dia_mes_ano.encode(linhas)
    pretx_v1_text = "\n".join(pretx_v1) + "\n"
    write_lf(out_dir / "01b-pretx-v1.txt", pretx_v1_text)
    debug_v1 = encode_com_debug(pretx_v1)
    tcf_v1_text = debug_v1["text"]
    write_lf(out_dir / "02b-tcf-v1.tcf", tcf_v1_text)
    postx_v1 = postx_dia_mes_ano.decode(tcf_decode(tcf_v1_text))
    write_lf(out_dir / "06b-postx-v1.txt", "\n".join(postx_v1) + "\n")
    rt_v1 = postx_v1 == linhas
    write_lf(out_dir / "08-rt-v1.txt",
             f"RT v1: {'OK' if rt_v1 else 'FAIL'}\n")
    print(f"v1 (dia/M/Y):    pretx={len(pretx_v1_text.encode('utf-8'))} bytes, "
          f"tcf={len(tcf_v1_text.encode('utf-8'))} bytes, "
          f"RT={'OK' if rt_v1 else 'FAIL'}")

    # === Pipeline TCF puro
    tcf_puro_debug = encode_com_debug(linhas)
    tcf_puro_text = tcf_puro_debug["text"]
    write_lf(out_dir / "02c-tcf-puro.tcf", tcf_puro_text)
    print(f"TCF puro:        tcf={len(tcf_puro_text.encode('utf-8'))} bytes")

    # === Debug v1
    write_lf(out_dir / "03-obat-tokens-v1.txt",
             format_obat_tokens(debug_v1["unicas"], debug_v1["tokens"]))
    write_lf(out_dir / "04-hcc-trace-v1.txt",
             debug_v1["trace"] + "\n" if debug_v1["trace"] else "(trace vazio)\n")
    write_lf(out_dir / "05-hcc-rede-v1.txt",
             debug_v1["rede"] + "\n" if debug_v1["rede"] else "(rede vazia)\n")

    # === Bytes comparison
    raw_csv = ds_path.read_bytes()
    pretx_v0_b = pretx_v0_text.encode("utf-8")
    pretx_v1_b = pretx_v1_text.encode("utf-8")
    tcf_v0_b = tcf_v0_text.encode("utf-8")
    tcf_v1_b = tcf_v1_text.encode("utf-8")
    tcf_puro_b = tcf_puro_text.encode("utf-8")

    cmp_md = [
        f"# Bytes — {DATASET_NAME} ({len(linhas)} linhas, fatura mensal dia 5)",
        "",
        "## 3 pipelines comparados",
        "",
        "| Pipeline | Pre-tx bytes | TCF bytes | vs raw csv | vs TCF puro |",
        "|---|---:|---:|---:|---:|",
        f"| TCF puro (sem pre-tx) | — | **{len(tcf_puro_b)}** | "
        f"{len(tcf_puro_b)/len(raw_csv)*100:.1f}% | 100.0% |",
        f"| Pre-tx v0 (dia-only) | {len(pretx_v0_b)} | **{len(tcf_v0_b)}** | "
        f"{len(tcf_v0_b)/len(raw_csv)*100:.1f}% | "
        f"{len(tcf_v0_b)/len(tcf_puro_b)*100:.1f}% |",
        f"| **Pre-tx v1 (escalas M/Y)** | **{len(pretx_v1_b)}** | "
        f"**{len(tcf_v1_b)}** | "
        f"**{len(tcf_v1_b)/len(raw_csv)*100:.1f}%** | "
        f"**{len(tcf_v1_b)/len(tcf_puro_b)*100:.1f}%** |",
        "",
        f"Raw CSV: {len(raw_csv)} bytes",
        "",
        "## Roundtrip",
        "",
        f"- RT v0 (dia-only pipeline): **{'OK' if rt_v0 else 'FAIL'}**",
        f"- RT v1 (escalas pipeline): **{'OK' if rt_v1 else 'FAIL'}**",
    ]
    write_lf(out_dir / "bytes-comparison.md", "\n".join(cmp_md) + "\n")

    # === result.md
    h1 = "CONFIRMADA" if rt_v1 else "REFUTADA"
    h2 = "CONFIRMADA" if (rt_v1 and len(tcf_v1_b) < len(tcf_v0_b)) else "REFUTADA"
    h3 = "CONFIRMADA" if (rt_v0 and len(tcf_v0_b) < len(tcf_puro_b)) else "REFUTADA"

    result_md = [
        f"# Resultado — 03-cadencia-mensal-{DATASET_NAME}",
        "",
        f"Dataset com {len(linhas)} linhas: fatura mensal dia 5 por 13 meses",
        f"(Jan/2025 a Jan/2026). Padrao realistic (sistema real de cobranca).",
        "",
        "## Bytes",
        "",
        "| Pipeline | Pre-tx bytes | TCF bytes | vs raw csv | vs TCF puro |",
        "|---|---:|---:|---:|---:|",
        f"| TCF puro | — | {len(tcf_puro_b)} | "
        f"{len(tcf_puro_b)/len(raw_csv)*100:.1f}% | 100.0% |",
        f"| Pre-tx v0 + TCF | {len(pretx_v0_b)} | {len(tcf_v0_b)} | "
        f"{len(tcf_v0_b)/len(raw_csv)*100:.1f}% | "
        f"{len(tcf_v0_b)/len(tcf_puro_b)*100:.1f}% |",
        f"| **Pre-tx v1 + TCF** | **{len(pretx_v1_b)}** | "
        f"**{len(tcf_v1_b)}** | "
        f"**{len(tcf_v1_b)/len(raw_csv)*100:.1f}%** | "
        f"**{len(tcf_v1_b)/len(tcf_puro_b)*100:.1f}%** |",
        "",
        f"Raw CSV: {len(raw_csv)} bytes",
        "",
        "## Hipoteses",
        "",
        f"- **H1 (RT v1 preserva dados)**: {h1}",
        f"- **H2 (escala vence em cadencia, v1 < v0)**: {h2}",
        f"  - v1 TCF: {len(tcf_v1_b)} bytes",
        f"  - v0 TCF: {len(tcf_v0_b)} bytes",
        f"  - Diferenca: {len(tcf_v1_b) - len(tcf_v0_b):+d} bytes "
        f"({(len(tcf_v1_b)/len(tcf_v0_b) - 1)*100:+.1f}%)",
        f"- **H3 (pre-tx v0 < TCF puro)**: {h3}",
        "",
        "## Pre-tx outputs (comparacao visual)",
        "",
        "### V0 (dia-only) — deltas variam por mes",
        "",
        "```",
        pretx_v0_text.rstrip(),
        "```",
        "",
        "### V1 (escalas) — todos iguais a `1M`",
        "",
        "```",
        pretx_v1_text.rstrip(),
        "```",
        "",
        "## Debug",
        "",
        "Estagios intermediarios em `outputs/`:",
        "- `01a-pretx-v0.txt` / `01b-pretx-v1.txt` — outputs do pretx",
        "- `02a-tcf-v0.tcf` / `02b-tcf-v1.tcf` / `02c-tcf-puro.tcf` — TCF encoded",
        "- `03-obat-tokens-v1.txt` / `04-hcc-trace-v1.txt` / `05-hcc-rede-v1.txt` — debug v1",
        "- `06a-postx-v0.txt` / `06b-postx-v1.txt` — outputs do postx",
        "- `07-rt-v0.txt` / `08-rt-v1.txt` — RT results",
        "",
        "## Conexoes",
        "",
        "- [`README.md`](README.md) — pergunta cientifica",
        "- [`../README.md`](../README.md) — T01 macro pai",
        "- [`pretx_dia_mes_ano.py`](pretx_dia_mes_ano.py) — encoder v1",
        "- [`../01-prova-conceito-D11a-dia/`](../01-prova-conceito-D11a-dia/) e",
        "  [`../02-bordas-D11b/`](../02-bordas-D11b/) — sub-exps com encoder v0",
    ]
    write_lf(THIS / "result.md", "\n".join(result_md) + "\n")
    print()
    print(f"result.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()
