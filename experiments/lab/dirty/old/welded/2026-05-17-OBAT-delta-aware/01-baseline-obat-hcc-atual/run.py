"""Sub-exp 01 — Baseline OBAT+HCC atual.

Roda OBAT+HCC canonical (src/tcf/, intocado) sobre D11a-h.
Dump tokens, body, trace por dataset. Sem modificacao.

Objetivo: caracterizar o que sai hoje, identificar oportunidades pra
delta-awareness.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter, OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import (  # noqa: E402
    TokLit,
    TokRefPref,
    TokRefSuf,
    processar,
)


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


def load_rows(ds: str) -> list[str]:
    p = ROOT / "datasets" / "synthetic" / f"{ds}.csv"
    with p.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def dedup_preserve_order(values: list[str]) -> list[str]:
    seen: OrderedDict[str, bool] = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def fmt_token(tok) -> str:
    if isinstance(tok, TokLit):
        return f'L({tok.text!r})'
    if isinstance(tok, TokRefPref):
        return f'P({tok.string_id},{tok.length})'
    if isinstance(tok, TokRefSuf):
        return f'S({tok.string_id},{tok.length})'
    return repr(tok)


def render_obat_tokens(unicas: list[str], tokens_por: list[list]) -> str:
    out = ["# OBAT tokens (canonical, min_len=3)", ""]
    out.append(f"strings_unicas: {len(unicas)}")
    out.append("")
    width = max(len(s) for s in unicas) + 2
    for i, (s, toks) in enumerate(zip(unicas, tokens_por)):
        token_str = " + ".join(fmt_token(t) for t in toks)
        out.append(f"  [{i+1:2}] {s!r:<{width}} -> {token_str}")
    out.append("")
    return "\n".join(out) + "\n"


def analyze(rows: list[str], unicas: list[str], tokens_por: list[list],
            body: str) -> str:
    """Caracteriza o que OBAT+HCC produzem; aponta gaps pra delta-aware."""
    # Token structure stats
    n_strings = len(unicas)
    n_lit_only = sum(1 for toks in tokens_por
                     if len(toks) == 1 and isinstance(toks[0], TokLit))
    n_with_ref = n_strings - n_lit_only

    # Literal-middle frequency (middles after a pref ref)
    middle_lits: list[str] = []
    for toks in tokens_por:
        for t in toks:
            if isinstance(t, TokLit):
                middle_lits.append(t.text)
    lit_counter = Counter(middle_lits)
    distinct_lits = len(lit_counter)

    # Distribuicao tipos
    n_pref_only = 0
    n_suf_only = 0
    n_both = 0
    n_pref_lit = 0
    for toks in tokens_por[1:]:
        has_p = any(isinstance(t, TokRefPref) for t in toks)
        has_s = any(isinstance(t, TokRefSuf) for t in toks)
        has_l = any(isinstance(t, TokLit) for t in toks)
        if has_p and has_s and not has_l:
            n_both += 1
        elif has_p and has_l and not has_s:
            n_pref_lit += 1
        elif has_p and not has_s and not has_l:
            n_pref_only += 1
        elif has_s and not has_p:
            n_suf_only += 1

    # HCC body stats
    body_lines = body.rstrip("\n").split("\n")
    body_bytes = len(body.encode("utf-8"))
    n_body_lines = len(body_lines)

    out = [
        "# Analise — onde delta-awareness ajudaria",
        "",
        "## Estatisticas estruturais",
        "",
        f"- Input rows: {len(rows)}",
        f"- Strings unicas: {n_strings} (dedupe ratio: {n_strings/len(rows)*100:.1f}%)",
        f"- 1a string (literal puro): 1",
        f"- Strings com ref: {n_with_ref}",
        "",
        "## Padroes de token (strings 2..N)",
        "",
        f"- Pref + Lit (sem suf):    {n_pref_lit}",
        f"- Pref + Suf (sem lit):    {n_both}",
        f"- So Pref:                  {n_pref_only}",
        f"- So Suf:                   {n_suf_only}",
        "",
        "## Literais (middle) — onde RLE perde",
        "",
        f"- Total de literais: {len(middle_lits)}",
        f"- Distintos: {distinct_lits}",
        f"- Repeticao media: {len(middle_lits)/max(1,distinct_lits):.2f}",
        "",
        "Top 10 literais por frequencia:",
        "",
    ]
    for lit, n in lit_counter.most_common(10):
        out.append(f"  - {lit!r}: {n} ocorrencias")
    out.extend([
        "",
        "## HCC body (.tcf)",
        "",
        f"- Bytes totais: {body_bytes}",
        f"- Linhas no body: {n_body_lines}",
        f"- Bytes/linha medio: {body_bytes/n_body_lines:.1f}",
        "",
        "## Onde delta-awareness ajudaria (apontamentos)",
        "",
    ])
    if n_pref_lit > 0 and distinct_lits > 1:
        out.append(
            f"- **{n_pref_lit} linhas Pref+Lit com {distinct_lits} literais distintos**: "
            "se literais variam (delta crescente p. ex.), HCC nao agrupa via RLE. "
            "OBAT-delta-aware emitiria token identico (ex: ^N+1d) → HCC RLE-agrupa."
        )
    if distinct_lits == len(middle_lits):
        out.append(
            "- **Cada literal e' unico** → zero RLE-agrupamento pelos literais. "
            "Cenario pior caso pra HCC; melhor caso pra delta-awareness."
        )
    elif distinct_lits < len(middle_lits) / 2:
        out.append(
            f"- Literais repetem moderadamente ({len(middle_lits)/distinct_lits:.1f}x). "
            "Delta-awareness pode aumentar repeticao se semantica for monotonica."
        )
    out.append("")
    out.append("## Observacao")
    out.append("")
    out.append(
        "Esta analise e' descritiva — nao recomenda mudanca. Apos varrer "
        "todos os D11a-h, sintetizar em `../notas/observacoes.md` o padrao "
        "geral pra informar desenho do sub-exp 02."
    )
    out.append("")
    return "\n".join(out) + "\n"


def process(ds: str) -> dict:
    rows = load_rows(ds)
    unicas = dedup_preserve_order(rows)
    tokens_por, log = processar(unicas, min_len=3)

    syn = M8AVirtualRefsSyntax()
    body = syn.encode(rows, unicas, tokens_por, "val")
    trace = syn.get_trace()
    rede = syn.get_rede()

    out = THIS / "outputs" / ds
    write_lf(out / "0-obat-log.txt", log)
    write_lf(out / "1-obat-tokens.txt", render_obat_tokens(unicas, tokens_por))
    write_lf(out / "2-hcc-body.tcf", body)
    write_lf(
        out / "3-hcc-trace.txt",
        ("# HCC trace\n\n" + trace + "\n\n# HCC rede\n\n" + rede + "\n"),
    )
    write_lf(out / "4-analysis.md", analyze(rows, unicas, tokens_por, body))

    return {
        "dataset": ds,
        "rows": len(rows),
        "unicas": len(unicas),
        "body_bytes": len(body.encode("utf-8")),
    }


def main() -> None:
    print("=== 01-baseline-obat-hcc-atual ===\n")
    print("Roda OBAT+HCC canonical (src/tcf) sobre D11a-h. Dump tokens/body/trace.\n")

    results = []
    for ds in DATASETS:
        r = process(ds)
        results.append(r)
        print(
            f"  {ds:24}  rows={r['rows']:3}  unicas={r['unicas']:3}  "
            f"body={r['body_bytes']:4} bytes"
        )

    # Summary
    out = [
        "# Resultado — 01-baseline-obat-hcc-atual",
        "",
        "## Tabela",
        "",
        "| Dataset | rows | unicas | body bytes |",
        "|---|---:|---:|---:|",
    ]
    for r in results:
        out.append(
            f"| [{r['dataset']}]({r['dataset']}/4-analysis.md) | "
            f"{r['rows']} | {r['unicas']} | {r['body_bytes']} |"
        )
    out.extend([
        "",
        "## Para cada dataset, ver `4-analysis.md`",
        "",
        "Apos varrer os 8, escrever sintese em `../notas/observacoes.md`.",
        "",
    ])
    write_lf(THIS / "result.md", "\n".join(out) + "\n")
    print()
    print(f"result.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()
