"""Orquestrador da prova de conceito 01-D11a-dia.

Pipeline completo com debug em cada estagio:
    csv → pretx_dia.encode → TCF.encode (OBAT+HCC) → TCF.decode → postx_dia.decode

Saidas:
    outputs/00..08 — estados intermediarios + RT
    outputs/bytes-comparison.md — tabela de bytes
    result.md (top-level) — resumo commitavel
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


def encode_com_debug(values: list[str], header: str = "val") -> dict:
    """Replica tcf.encoder.encode mas captura OBAT tokens + HCC trace.

    A API publica (`tcf.encode`) cria instancia interna do
    M8AVirtualRefsSyntax — nao da' acesso a `get_trace`/`get_rede`.
    Aqui rodamos os mesmos passos manualmente pra capturar.
    """
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
    """Dump human-readable da tokenizacao OBAT (arvore por string)."""
    out = ["# OBAT tokenization (debug)\n"]
    out.append("## Strings unicas (ordem de aparicao)\n")
    for i, u in enumerate(unicas):
        out.append(f"  [{i}] {u!r}")
    out.append("")
    out.append("## Tokens por string\n")
    out.append("Cada string e' tokenizada como sequencia de:")
    out.append("- `L(text)` = literal puro")
    out.append("- `P(id, n)` = prefix ref a string `id`, comprimento `n`")
    out.append("- `S(id, n)` = suffix ref a string `id`, comprimento `n`")
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
    ds_path = ROOT / "datasets" / "synthetic" / "D11a-datas-dia.csv"
    out_dir = THIS / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== 01-prova-conceito-D11a-dia ===")
    print(f"dataset: {ds_path}")
    print(f"out:     {out_dir}")
    print()

    # Le CSV
    with ds_path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)  # skip header
        linhas = [row[0] for row in r if row]

    # === Estagio 0: input
    write_lf(out_dir / "00-input.txt", "\n".join(linhas) + "\n")
    print(f"00 input:      {len(linhas)} linhas")

    # === Estagio 1: pre-tx encode (dia delta)
    pretx_out = pretx_dia.encode(linhas)
    pretx_text = "\n".join(pretx_out) + "\n"
    write_lf(out_dir / "01-pretx-output.txt", pretx_text)
    print(f"01 pre-tx:     {len(pretx_out)} linhas, "
          f"{len(pretx_text.encode('utf-8'))} bytes")

    # === Estagio 2: TCF encode (com debug)
    debug = encode_com_debug(pretx_out)
    tcf_text = debug["text"]
    write_lf(out_dir / "02-tcf-encoded.tcf", tcf_text)
    print(f"02 tcf encode: {len(tcf_text.encode('utf-8'))} bytes")

    # === Estagio 3: OBAT tokens (debug arvore)
    write_lf(
        out_dir / "03-obat-tokens.txt",
        format_obat_tokens(debug["unicas"], debug["tokens"]),
    )

    # === Estagio 4: HCC trace
    write_lf(
        out_dir / "04-hcc-trace.txt",
        debug["trace"] + "\n" if debug["trace"] else "(trace vazio)\n",
    )

    # === Estagio 5: HCC rede
    write_lf(
        out_dir / "05-hcc-rede.txt",
        debug["rede"] + "\n" if debug["rede"] else "(rede vazia)\n",
    )

    # === Estagio 6: TCF decode
    tcf_decoded = tcf_decode(tcf_text)
    write_lf(
        out_dir / "06-tcf-decoded.txt",
        "\n".join(tcf_decoded) + "\n",
    )
    tcf_rt = tcf_decoded == pretx_out
    print(f"06 tcf decode: {len(tcf_decoded)} linhas, RT vs pre-tx = {'OK' if tcf_rt else 'FAIL'}")

    # === Estagio 7: pos-tx decode
    postx_out = postx_dia.decode(tcf_decoded)
    write_lf(
        out_dir / "07-postx-output.txt",
        "\n".join(postx_out) + "\n",
    )

    # === Estagio 8: RT full
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

    # === Bytes comparison
    raw_csv = ds_path.read_bytes()
    pretx_b = pretx_text.encode("utf-8")
    tcf_b = tcf_text.encode("utf-8")

    # Baseline: TCF puro sem pre-tx
    tcf_puro_debug = encode_com_debug(linhas)
    tcf_puro_text = tcf_puro_debug["text"]
    tcf_puro_b = tcf_puro_text.encode("utf-8")

    cmp_md = [
        "# Bytes — D11a (12 linhas YYYY-MM-DD, variacao apenas em dias)",
        "",
        "| Etapa | Bytes | vs raw csv | vs TCF puro |",
        "|---|---:|---:|---:|",
        f"| Raw CSV (com header) | {len(raw_csv)} | 100.0% | — |",
        f"| Pre-tx output (base + deltas em dias) | {len(pretx_b)} | "
        f"{len(pretx_b)/len(raw_csv)*100:.1f}% | — |",
        f"| **TCF puro** (sem pre-tx) | **{len(tcf_puro_b)}** | "
        f"{len(tcf_puro_b)/len(raw_csv)*100:.1f}% | 100.0% |",
        f"| **TCF de pre-tx** | **{len(tcf_b)}** | "
        f"{len(tcf_b)/len(raw_csv)*100:.1f}% | "
        f"{len(tcf_b)/len(tcf_puro_b)*100:.1f}% |",
        "",
        f"RT full: **{'OK' if rt_full else 'FAIL'}**",
        "",
        "## Interpretacao",
        "",
        f"- TCF puro reduz a {len(tcf_puro_b)/len(raw_csv)*100:.1f}% do raw csv.",
        f"- Pre-tx + TCF reduz a {len(tcf_b)/len(raw_csv)*100:.1f}% do raw csv.",
        f"- Razao pre-tx+TCF / TCF puro: "
        f"{len(tcf_b)/len(tcf_puro_b)*100:.1f}% (menor que 100% = pre-tx ajuda).",
    ]
    write_lf(out_dir / "bytes-comparison.md", "\n".join(cmp_md) + "\n")

    # === result.md commitavel
    result_md = [
        "# Resultado — 01-prova-conceito-D11a-dia",
        "",
        f"Executado a partir de [`D11a-datas-dia.csv`]"
        f"(../../../../../../../datasets/synthetic/D11a-datas-dia.csv) "
        f"({len(linhas)} linhas).",
        "",
        "## Bytes",
        "",
        "| Etapa | Bytes | vs raw csv | vs TCF puro |",
        "|---|---:|---:|---:|",
        f"| Raw CSV (com header) | {len(raw_csv)} | 100.0% | — |",
        f"| Pre-tx output | {len(pretx_b)} | "
        f"{len(pretx_b)/len(raw_csv)*100:.1f}% | — |",
        f"| TCF puro | {len(tcf_puro_b)} | "
        f"{len(tcf_puro_b)/len(raw_csv)*100:.1f}% | 100.0% |",
        f"| **TCF de pre-tx** | **{len(tcf_b)}** | "
        f"**{len(tcf_b)/len(raw_csv)*100:.1f}%** | "
        f"**{len(tcf_b)/len(tcf_puro_b)*100:.1f}%** |",
        "",
        f"## Roundtrip",
        "",
        f"- TCF roundtrip (pre-tx output): **{'OK' if tcf_rt else 'FAIL'}**",
        f"- RT full (pos-tx output == input): **{'OK' if rt_full else 'FAIL'}**",
        "",
        "## Conclusao desta iteracao",
        "",
        f"- Hipotese pre-tx reduz bytes vs TCF puro: "
        f"**{'CONFIRMADA' if len(tcf_b) < len(tcf_puro_b) else 'REFUTADA'}** "
        f"({len(tcf_b)} vs {len(tcf_puro_b)} bytes).",
        f"- Hipotese pipeline preserva dados (RT): "
        f"**{'CONFIRMADA' if rt_full else 'REFUTADA'}**.",
        "",
        "## Debug",
        "",
        "Estagios intermediarios em `outputs/` (regeneravel via `run.py`):",
        "- `00-input.txt` ... `08-rt-result.txt`",
        "- `03-obat-tokens.txt` — arvore OBAT da saida pre-tx",
        "- `04-hcc-trace.txt` — composicao HCC",
        "- `05-hcc-rede.txt` — rede de refs HCC",
        "",
        "## Conexoes",
        "",
        "- [`README.md`](README.md) — pergunta cientifica + metodo",
        "- [`../README.md`](../README.md) — T01 macro pai",
        "- [`pretx_dia.py`](pretx_dia.py) / [`postx_dia.py`](postx_dia.py) — encoder/decoder",
    ]
    write_lf(THIS / "result.md", "\n".join(result_md) + "\n")
    print()
    print(f"result.md: {THIS / 'result.md'}")
    print(f"Bytes resumo: raw={len(raw_csv)}, pretx={len(pretx_b)}, "
          f"tcf_puro={len(tcf_puro_b)}, pretx+tcf={len(tcf_b)}")


if __name__ == "__main__":
    main()
