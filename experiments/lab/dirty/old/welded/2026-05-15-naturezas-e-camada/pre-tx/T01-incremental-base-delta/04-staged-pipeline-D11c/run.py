"""Orquestrador do sub-experimento 04 (staged pipeline).

Roda 3 estagios SEPARADOS + TCF + decode. Dumps intermediarios em
`outputs/` pra inspecao. Compara bytes vs sub-exp 03 (encoder
monolitico v1) — esperado mesmo resultado final.
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


DATASET_NAME = "D11c-datas-mensal"


def encode_com_debug(values: list[str], header: str = "val") -> dict:
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())
    tokens, _ = processar(unicas, min_len=3)
    syn = M8AVirtualRefsSyntax()
    text = syn.encode(values, unicas, tokens, header)
    return {"text": text, "unicas": unicas, "tokens": tokens,
            "trace": syn.get_trace(), "rede": syn.get_rede()}


def format_obat(unicas, tokens) -> str:
    out = ["# OBAT tokenization\n"]
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

    print(f"=== 04-staged-pipeline-{DATASET_NAME} ===")
    print(f"dataset: {ds_path}\n")

    with ds_path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        linhas = [row[0] for row in r if row]

    write_lf(out_dir / "00-input.txt", "\n".join(linhas) + "\n")
    print(f"00 input: {len(linhas)} linhas")

    # === STAGE A: identify ===
    meta = stage_a_identify.identify(linhas)
    write_lf(out_dir / "stage-A-metadata.json",
             json.dumps(meta, indent=2) + "\n")
    print(f"A identify: type={meta['type']}, "
          f"format={meta['format']}, "
          f"granularity={meta['granularity']}")

    # === STAGE B: normalize to unit (day) ===
    stage_b = stage_b_normalize.normalize_to_unit(linhas, meta)
    stage_b_text = "\n".join(stage_b) + "\n"
    write_lf(out_dir / "stage-B-normalized.txt", stage_b_text)
    print(f"B normalize: {len(stage_b)} linhas, "
          f"{len(stage_b_text.encode('utf-8'))} bytes "
          f"(deltas em dias)")

    # === STAGE C: optimize scales ===
    stage_c = stage_c_optimize.optimize_scales(stage_b, meta)
    stage_c_text = "\n".join(stage_c) + "\n"
    write_lf(out_dir / "stage-C-optimized.txt", stage_c_text)
    print(f"C optimize: {len(stage_c)} linhas, "
          f"{len(stage_c_text.encode('utf-8'))} bytes "
          f"(com escalas onde exato)")

    # === TCF encode 3 entradas ===
    debug_puro = encode_com_debug(linhas)
    write_lf(out_dir / "tcf-puro.tcf", debug_puro["text"])

    debug_b = encode_com_debug(stage_b)
    write_lf(out_dir / "tcf-B.tcf", debug_b["text"])

    debug_c = encode_com_debug(stage_c)
    write_lf(out_dir / "tcf-C.tcf", debug_c["text"])
    write_lf(out_dir / "debug-obat-C.txt",
             format_obat(debug_c["unicas"], debug_c["tokens"]))
    write_lf(out_dir / "debug-hcc-trace-C.txt",
             debug_c["trace"] + "\n" if debug_c["trace"] else "(vazio)\n")
    write_lf(out_dir / "debug-hcc-rede-C.txt",
             debug_c["rede"] + "\n" if debug_c["rede"] else "(vazia)\n")

    tcf_puro_b = len(debug_puro["text"].encode("utf-8"))
    tcf_b_b = len(debug_b["text"].encode("utf-8"))
    tcf_c_b = len(debug_c["text"].encode("utf-8"))
    print(f"TCF puro:      {tcf_puro_b} bytes")
    print(f"TCF de B:      {tcf_b_b} bytes (= encoder v0)")
    print(f"TCF de C:      {tcf_c_b} bytes (= encoder v1, esperado 22)")

    # === Decode + RT verification ===
    tcf_decoded_c = tcf_decode(debug_c["text"])
    rt_tcf_c = tcf_decoded_c == stage_c
    decoded_linhas, meta_dec = decoder.decode(tcf_decoded_c)
    rt_full = decoded_linhas == linhas
    write_lf(out_dir / "decoded-C.txt",
             "\n".join(decoded_linhas) + "\n")

    # Tambem decode pelo caminho B (sem otimizacao de escala)
    tcf_decoded_b = tcf_decode(debug_b["text"])
    rt_tcf_b = tcf_decoded_b == stage_b
    decoded_b_linhas = stage_b_normalize.denormalize_from_unit(
        tcf_decoded_b, meta)
    rt_b_full = decoded_b_linhas == linhas
    write_lf(out_dir / "decoded-B.txt",
             "\n".join(decoded_b_linhas) + "\n")

    rt_text = [
        f"RT TCF C (tcf_decode == stage_c): {'OK' if rt_tcf_c else 'FAIL'}",
        f"RT TCF B (tcf_decode == stage_b): {'OK' if rt_tcf_b else 'FAIL'}",
        f"RT full C (decoder.decode == linhas): {'OK' if rt_full else 'FAIL'}",
        f"RT full B (B reverse == linhas): {'OK' if rt_b_full else 'FAIL'}",
        f"Meta re-identificado no decode: {meta_dec}",
    ]
    write_lf(out_dir / "rt-result.txt", "\n".join(rt_text) + "\n")
    print()
    for line in rt_text:
        print(f"  {line}")

    # === Bytes comparison ===
    raw_csv = ds_path.read_bytes()
    cmp_md = [
        f"# Bytes — {DATASET_NAME} (staged pipeline, 3 estagios)",
        "",
        f"Raw CSV: **{len(raw_csv)}** bytes",
        "",
        "| Pipeline | Saida intermediaria | TCF bytes | vs raw |",
        "|---|---|---:|---:|",
        f"| TCF puro | — | **{tcf_puro_b}** | "
        f"{tcf_puro_b/len(raw_csv)*100:.1f}% |",
        f"| Stage A+B (= v0) | "
        f"{len(stage_b_text.encode('utf-8'))} bytes intermediarios | "
        f"**{tcf_b_b}** | {tcf_b_b/len(raw_csv)*100:.1f}% |",
        f"| **Stage A+B+C (= v1)** | "
        f"{len(stage_c_text.encode('utf-8'))} bytes intermediarios | "
        f"**{tcf_c_b}** | {tcf_c_b/len(raw_csv)*100:.1f}% |",
        "",
        f"Comparacao com sub-exp 03 (v1 monolitico): 22 bytes — "
        f"{'identico' if tcf_c_b == 22 else f'diferente ({tcf_c_b} vs 22)'}.",
    ]
    write_lf(out_dir / "bytes-comparison.md", "\n".join(cmp_md) + "\n")

    # === result.md ===
    h1 = "CONFIRMADO" if (rt_full and rt_b_full) else "REFUTADO"
    h2 = "CONFIRMADO" if tcf_c_b == 22 else f"DIFERENTE ({tcf_c_b} != 22)"

    result = [
        f"# Resultado — 04-staged-pipeline-{DATASET_NAME}",
        "",
        "## Estagios em sequencia",
        "",
        "### Stage A (identify) — metadata",
        "",
        "```json",
        json.dumps(meta, indent=2),
        "```",
        "",
        f"### Stage B (normalize) — {len(stage_b_text.encode('utf-8'))} bytes intermediarios",
        "",
        "```",
        stage_b_text.rstrip(),
        "```",
        "",
        f"### Stage C (optimize) — {len(stage_c_text.encode('utf-8'))} bytes intermediarios",
        "",
        "```",
        stage_c_text.rstrip(),
        "```",
        "",
        f"### TCF (de C) — {tcf_c_b} bytes",
        "",
        "```",
        debug_c["text"].rstrip(),
        "```",
        "",
        "## Comparacao de pipelines",
        "",
        f"Raw CSV: {len(raw_csv)} bytes",
        "",
        "| Pipeline | TCF bytes | vs raw csv | vs TCF puro |",
        "|---|---:|---:|---:|",
        f"| TCF puro | {tcf_puro_b} | "
        f"{tcf_puro_b/len(raw_csv)*100:.1f}% | 100.0% |",
        f"| Stage A+B (= encoder v0) | {tcf_b_b} | "
        f"{tcf_b_b/len(raw_csv)*100:.1f}% | "
        f"{tcf_b_b/tcf_puro_b*100:.1f}% |",
        f"| **Stage A+B+C (= encoder v1)** | **{tcf_c_b}** | "
        f"**{tcf_c_b/len(raw_csv)*100:.1f}%** | "
        f"**{tcf_c_b/tcf_puro_b*100:.1f}%** |",
        "",
        "## Hipoteses",
        "",
        f"- **H1 (RT preservado em ambos os pipelines)**: {h1}",
        f"  - RT full via C (com escala): {'OK' if rt_full else 'FAIL'}",
        f"  - RT full via B (so dias): {'OK' if rt_b_full else 'FAIL'}",
        f"- **H2 (bytes iguais a v1 monolitico do sub-exp 03)**: {h2}",
        "",
        "## Comparacao com encoder monolitico (sub-exp 03)",
        "",
        "Sub-exp 03 (encoder v1 monolitico): 22 bytes em D11c.",
        f"Sub-exp 04 (encoder em 3 estagios): {tcf_c_b} bytes em D11c.",
        "",
        f"Resultado: {'IDENTICO' if tcf_c_b == 22 else 'DIFERENTE'} — separar em estagios",
        "preserva compressao final, com vantagem de ter estados intermediarios",
        "visiveis pra inspecao e raciocinio futuro.",
        "",
        "## Conexoes",
        "",
        "- [`README.md`](README.md) — pergunta cientifica + metodo",
        "- [`stage_a_identify.py`](stage_a_identify.py) — estagio A",
        "- [`stage_b_normalize.py`](stage_b_normalize.py) — estagio B",
        "- [`stage_c_optimize.py`](stage_c_optimize.py) — estagio C",
        "- [`decoder.py`](decoder.py) — inverso completo",
        "- [`../03-cadencia-mensal-D11c/`](../03-cadencia-mensal-D11c/) — encoder monolitico equivalente",
    ]
    write_lf(THIS / "result.md", "\n".join(result) + "\n")
    print()
    print(f"result.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()
