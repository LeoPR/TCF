"""Sub-exp 10 — Pacote completo com validacao embutida.

Combina sub-exp 08 (8 datasets, pipeline staged completo) +
sub-exp 09 (validacao self-contained com decoder isolado).

Estrutura de output (por dataset):
    outputs/<D11x>/
        _SUMMARY.md                  one-pager
        1-input/data.txt             linhas extraidas
        2-pre-tx/                    Stage A/B/C
            A-metadata.json
            B-normalized.txt
            C-optimized.txt
        3-obat/tokens.txt            tokenizador alg16
        4-hcc/                       composicional
            trace.txt
            rede.txt
        5-encoded/output.tcf         saida final .tcf
        6-decode/                    decode staged
            tcf-decoded.txt
            stage-C-reverse.txt
            final.txt
        7-validation/                checks obrigatorios
            rt-staged.txt
            rt-self-contained.txt
            byte-canonical.txt

Top-level result.md consolida todos os datasets.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
LIB = THIS / "lib"
ROOT = THIS.parents[6]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(LIB))

from tcf import decode as tcf_decode  # noqa: E402
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar  # noqa: E402

import stage_a_identify  # noqa: E402
import stage_b_normalize  # noqa: E402
import stage_c_optimize  # noqa: E402
import decoder  # noqa: E402  staged
from self_contained_decoder import decode_self_contained  # noqa: E402


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


def encode_tcf_with_debug(values: list[str]) -> dict:
    """TCF encode capturando OBAT tokens + HCC trace/rede."""
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())
    tokens, _ = processar(unicas, min_len=3)
    syn = M8AVirtualRefsSyntax()
    text = syn.encode(values, unicas, tokens, "val")
    return {
        "text": text,
        "unicas": unicas,
        "tokens": tokens,
        "trace": syn.get_trace(),
        "rede": syn.get_rede(),
    }


def format_obat_tokens(unicas: list[str], tokens: list) -> str:
    lines = ["# OBAT tokenization", ""]
    lines.append("## Strings unicas (ordem de aparicao)")
    for i, u in enumerate(unicas):
        lines.append(f"  [{i}] {u!r}")
    lines.append("")
    lines.append("## Tokens por string")
    lines.append("`L(text)` = literal; `P(id, n)` = prefix ref; `S(id, n)` = suffix ref.")
    lines.append("")
    for i, tok_list in enumerate(tokens):
        lines.append(f"  String [{i}] = {unicas[i]!r}:")
        for j, t in enumerate(tok_list):
            lines.append(f"    {j}: {t!r}")
        lines.append("")
    return "\n".join(lines)


def process_dataset(ds: str) -> dict:
    ds_path = ROOT / "datasets" / "synthetic" / f"{ds}.csv"
    out_dir = THIS / "outputs" / ds

    # === 1-input: linhas extraidas (sem header)
    with ds_path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        linhas = [row[0] for row in r if row]
    write_lf(out_dir / "1-input" / "data.txt", "\n".join(linhas) + "\n")

    # === 2-pre-tx: A → B → C
    meta = stage_a_identify.identify(linhas)
    write_lf(
        out_dir / "2-pre-tx" / "A-metadata.json",
        json.dumps(meta, indent=2) + "\n",
    )
    stage_b = stage_b_normalize.normalize_to_unit(linhas, meta)
    write_lf(
        out_dir / "2-pre-tx" / "B-normalized.txt",
        "\n".join(stage_b) + "\n",
    )
    stage_c = stage_c_optimize.optimize_scales(stage_b, meta)
    write_lf(
        out_dir / "2-pre-tx" / "C-optimized.txt",
        "\n".join(stage_c) + "\n",
    )

    # === TCF encode com debug
    enc = encode_tcf_with_debug(stage_c)

    # === 3-obat
    write_lf(
        out_dir / "3-obat" / "tokens.txt",
        format_obat_tokens(enc["unicas"], enc["tokens"]),
    )

    # === 4-hcc
    write_lf(
        out_dir / "4-hcc" / "trace.txt",
        enc["trace"] + "\n" if enc["trace"] else "(trace vazio)\n",
    )
    write_lf(
        out_dir / "4-hcc" / "rede.txt",
        enc["rede"] + "\n" if enc["rede"] else "(rede vazia)\n",
    )

    # === 5-encoded
    tcf_path = out_dir / "5-encoded" / "output.tcf"
    write_lf(tcf_path, enc["text"])

    # === 6-decode (staged)
    tcf_decoded_lines = tcf_decode(enc["text"])
    write_lf(
        out_dir / "6-decode" / "tcf-decoded.txt",
        "\n".join(tcf_decoded_lines) + "\n",
    )
    stage_c_reverse = stage_c_optimize.deoptimize_scales(tcf_decoded_lines, meta)
    write_lf(
        out_dir / "6-decode" / "stage-C-reverse.txt",
        "\n".join(stage_c_reverse) + "\n",
    )
    final = stage_b_normalize.denormalize_from_unit(stage_c_reverse, meta)
    write_lf(
        out_dir / "6-decode" / "final.txt",
        "\n".join(final) + "\n",
    )

    # === 7-validation
    # rt-staged: decoder com modulos
    rt_staged_ok = final == linhas
    rt_staged_text = [
        f"RT staged: {'OK' if rt_staged_ok else 'FAIL'}",
        f"input lines: {len(linhas)}",
        f"final lines: {len(final)}",
    ]
    if not rt_staged_ok:
        rt_staged_text.append("")
        rt_staged_text.append("Diferencas:")
        for i in range(max(len(linhas), len(final))):
            a = linhas[i] if i < len(linhas) else "<missing>"
            b = final[i] if i < len(final) else "<missing>"
            if a != b:
                rt_staged_text.append(f"  [{i}] input={a!r} final={b!r}")
    write_lf(
        out_dir / "7-validation" / "rt-staged.txt",
        "\n".join(rt_staged_text) + "\n",
    )

    # rt-self-contained: decoder isolado recebe APENAS o .tcf
    sc_lines, sc_meta = decode_self_contained(tcf_path)
    rt_sc_ok = sc_lines == linhas
    rt_sc_text = [
        f"RT self-contained: {'OK' if rt_sc_ok else 'FAIL'}",
        f"input lines: {len(linhas)}",
        f"sc lines: {len(sc_lines)}",
        f"meta auto-detected from first line: {sc_meta}",
        "",
        "Decoder recebeu APENAS o file path (sem D11x.csv, sem hint, sem meta).",
    ]
    if not rt_sc_ok:
        rt_sc_text.append("")
        rt_sc_text.append("Diferencas:")
        for i in range(max(len(linhas), len(sc_lines))):
            a = linhas[i] if i < len(linhas) else "<missing>"
            b = sc_lines[i] if i < len(sc_lines) else "<missing>"
            if a != b:
                rt_sc_text.append(f"  [{i}] input={a!r} sc={b!r}")
    write_lf(
        out_dir / "7-validation" / "rt-self-contained.txt",
        "\n".join(rt_sc_text) + "\n",
    )

    # byte-canonical: diff exato
    bc_text = []
    if rt_sc_ok and rt_staged_ok:
        bc_text.append("byte-canonical: MATCH")
        bc_text.append(f"  staged decoder    == input ({len(linhas)} linhas)")
        bc_text.append(f"  self-contained    == input ({len(linhas)} linhas)")
    else:
        bc_text.append("byte-canonical: FAIL (ver rt-*.txt)")
    write_lf(
        out_dir / "7-validation" / "byte-canonical.txt",
        "\n".join(bc_text) + "\n",
    )

    # === _SUMMARY.md per dataset
    raw_csv = ds_path.read_bytes()
    tcf_bytes = enc["text"].encode("utf-8")
    pre_b_bytes = ("\n".join(stage_b) + "\n").encode("utf-8")
    pre_c_bytes = ("\n".join(stage_c) + "\n").encode("utf-8")
    summary = [
        f"# _SUMMARY — {ds}",
        "",
        f"**Granularidade**: `{meta['granularity']}` (auto-detectada em Stage A)",
        f"**Formato**: `{meta.get('format', '—')}`",
        f"**Linhas**: {len(linhas)}",
        "",
        "## Validacao",
        "",
        f"- **RT staged**: {'OK' if rt_staged_ok else '**FAIL**'} (decoder com modulos)",
        f"- **RT self-contained**: {'OK' if rt_sc_ok else '**FAIL**'} (decoder recebe APENAS o .tcf)",
        f"- **Byte-canonical vs input**: {'MATCH' if (rt_staged_ok and rt_sc_ok) else '**FAIL**'}",
        "",
        "## Bytes por fase",
        "",
        "| Fase | Bytes | vs raw csv |",
        "|---|---:|---:|",
        f"| 1-input (raw csv) | {len(raw_csv)} | 100.0% |",
        f"| 2-pre-tx B (normalize) | {len(pre_b_bytes)} | "
        f"{len(pre_b_bytes)/len(raw_csv)*100:.1f}% |",
        f"| 2-pre-tx C (optimize) | {len(pre_c_bytes)} | "
        f"{len(pre_c_bytes)/len(raw_csv)*100:.1f}% |",
        f"| **5-encoded (.tcf final)** | **{len(tcf_bytes)}** | "
        f"**{len(tcf_bytes)/len(raw_csv)*100:.1f}%** |",
        "",
        "## Audit trail",
        "",
        f"- Stage A detectou `{meta.get('type')}` / `{meta.get('granularity')}` da primeira linha",
        f"- Stage B normalizou em {len(stage_b)} entradas (base + {len(stage_b)-1} deltas)",
        f"- Stage C {'aplicou escala' if stage_b != stage_c else 'no-op (sem escala exata)'} "
        f"→ {len(stage_c)} entradas",
        f"- OBAT: {len(enc['unicas'])} strings unicas, tokenizadas",
        f"- HCC: {len(enc['text'].split(chr(10)))-1} linhas no .tcf",
        "",
        "## Navegacao",
        "",
        "- [`1-input/data.txt`](1-input/data.txt) — input linhas",
        "- [`2-pre-tx/`](2-pre-tx/) — A/B/C",
        "- [`3-obat/tokens.txt`](3-obat/tokens.txt) — tokens alg16",
        "- [`4-hcc/`](4-hcc/) — trace + rede",
        "- [`5-encoded/output.tcf`](5-encoded/output.tcf) — saida final (gitignored)",
        "- [`6-decode/`](6-decode/) — caminho de volta",
        "- [`7-validation/`](7-validation/) — RT + self-contained + byte-canonical",
    ]
    write_lf(out_dir / "_SUMMARY.md", "\n".join(summary) + "\n")

    return {
        "dataset": ds,
        "granularity": meta.get("granularity"),
        "linhas": len(linhas),
        "raw_bytes": len(raw_csv),
        "tcf_bytes": len(tcf_bytes),
        "rt_staged": rt_staged_ok,
        "rt_self_contained": rt_sc_ok,
        "byte_canonical": rt_staged_ok and rt_sc_ok,
    }


def main() -> None:
    print("=== 10-pacote-completo-com-validacao ===\n")
    print(f"Datasets: {len(DATASETS)}")
    print(f"Output base: {THIS / 'outputs'}\n")

    results = []
    for ds in DATASETS:
        print(f"--- {ds} ---")
        r = process_dataset(ds)
        results.append(r)
        print(
            f"  granul={r['granularity']:6} | linhas={r['linhas']:2} | "
            f"raw={r['raw_bytes']:4} | tcf={r['tcf_bytes']:4} | "
            f"RT_staged={'OK' if r['rt_staged'] else 'FAIL'} | "
            f"RT_sc={'OK' if r['rt_self_contained'] else 'FAIL'} | "
            f"BC={'MATCH' if r['byte_canonical'] else 'FAIL'}"
        )

    # === result.md consolidado
    all_ok = all(r["byte_canonical"] for r in results)
    out = [
        "# Resultado — 10-pacote-completo-com-validacao",
        "",
        f"**Status global**: {'**TODOS OK**' if all_ok else '**FALHAS DETECTADAS**'} "
        f"({sum(1 for r in results if r['byte_canonical'])}/{len(results)})",
        "",
        "## Tabela consolidada",
        "",
        "| Dataset | Granul. | Linhas | Raw | TCF | RT staged | RT self-contained | Byte-canonical |",
        "|---|---|---:|---:|---:|---|---|---|",
    ]
    for r in results:
        out.append(
            f"| [{r['dataset']}]({r['dataset']}/_SUMMARY.md) | "
            f"{r['granularity']} | {r['linhas']} | {r['raw_bytes']} | "
            f"**{r['tcf_bytes']}** | "
            f"{'OK' if r['rt_staged'] else '**FAIL**'} | "
            f"{'OK' if r['rt_self_contained'] else '**FAIL**'} | "
            f"{'MATCH' if r['byte_canonical'] else '**FAIL**'} |"
        )
    out.append("")

    out.append("## Validacao em duas vias")
    out.append("")
    out.append("Cada dataset valida duas decodificacoes independentes:")
    out.append("")
    out.append("1. **RT staged** (`6-decode/final.txt`): decoder usa modulos")
    out.append("   `decoder.py` + `stage_*.py`. Demonstra que o pipeline e'")
    out.append("   inversivel.")
    out.append("")
    out.append("2. **RT self-contained** (`7-validation/rt-self-contained.txt`):")
    out.append("   `decode_self_contained()` recebe APENAS o file path do `.tcf`.")
    out.append("   Auto-detecta natureza pela primeira linha. Sem hint externo,")
    out.append("   sem D11x.csv, sem metadata sidecar. Demonstra que o arquivo")
    out.append("   carrega TUDO necessario.")
    out.append("")

    out.append("## Estrutura de output (parcimoniosa, 7 fases por dataset)")
    out.append("")
    out.append("```")
    out.append("outputs/<dataset>/")
    out.append("├── _SUMMARY.md             one-pager")
    out.append("├── 1-input/data.txt")
    out.append("├── 2-pre-tx/{A-metadata.json, B-normalized.txt, C-optimized.txt}")
    out.append("├── 3-obat/tokens.txt")
    out.append("├── 4-hcc/{trace.txt, rede.txt}")
    out.append("├── 5-encoded/output.tcf      (gitignored, regeneravel)")
    out.append("├── 6-decode/{tcf-decoded.txt, stage-C-reverse.txt, final.txt}")
    out.append("└── 7-validation/{rt-staged.txt, rt-self-contained.txt, byte-canonical.txt}")
    out.append("```")
    out.append("")

    out.append("## Como rodar")
    out.append("")
    out.append("```bash")
    out.append("python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/10-pacote-completo-com-validacao/run.py")
    out.append("```")
    out.append("")
    out.append("Ou validacao standalone de um .tcf qualquer:")
    out.append("")
    out.append("```bash")
    out.append("python lib/self_contained_decoder.py outputs/D11a-datas-dia/5-encoded/output.tcf")
    out.append("```")
    out.append("")

    out.append("## Conexoes")
    out.append("")
    out.append("- [`../08-granularidades-finas/`](../08-granularidades-finas/) — pipeline base")
    out.append("- [`../09-auditoria-self-contained-D11a/`](../09-auditoria-self-contained-D11a/) — auditoria pioneira")

    write_lf(THIS / "result.md", "\n".join(out) + "\n")
    print()
    print(f"result.md: {THIS / 'result.md'}")
    print(f"Status: {'TODOS OK' if all_ok else 'FALHAS — ver acima'}")


if __name__ == "__main__":
    main()
