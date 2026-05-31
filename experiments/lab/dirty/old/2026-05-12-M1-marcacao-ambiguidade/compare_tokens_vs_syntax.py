"""Compara tokens semanticos (raiz exp 16) com as sintaxes M1.A e M1.B.

Para cada dataset, imprime:
  - string original
  - tokens abstratos do online.py (TokLit, TokRefPref, TokRefSuf)
  - fragmentos literais (apos quebras propagadas)
  - linha TCF em M1.A (escape)
  - linha TCF em M1.B (quote)

Util para visualizar **onde a compressao ocorre** (tokens) e
**onde os marcadores sao gastos** (encoding).
"""

import csv
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
sys.path.insert(0, str(THIS))
sys.path.insert(0, str(THIS / "M1-A-escape"))
sys.path.insert(0, str(THIS / "M1-B-quote"))

from online import processar, reconstroi, TokLit, TokRefPref, TokRefSuf

# Imports usando paths diretos para evitar conflito de nomes
import importlib.util


def _carregar(modulo_path, modulo_name):
    spec = importlib.util.spec_from_file_location(modulo_name, modulo_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modulo_name] = mod
    spec.loader.exec_module(mod)
    return mod


m1a = _carregar(THIS / "M1-A-escape" / "syntax.py", "m1a_syntax")
m1b = _carregar(THIS / "M1-B-quote" / "syntax.py", "m1b_syntax")

M1A = m1a.M1AEscapeSyntax
M1B = m1b.M1BQuoteSyntax

DATASETS = ["D1-emails-simples", "D2-emails-quote-id",
             "D3-stress-substring", "D4-caos-mix"]


def ler_csv(path):
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def fmt_tok(tok):
    if isinstance(tok, TokLit):
        return f"L({tok.text!r})"
    if isinstance(tok, TokRefPref):
        return f"P({tok.string_id},{tok.length})"
    return f"S({tok.string_id},{tok.length})"


def fragmentos_de_no(eid, tokens_eid, unicas, quebras):
    """Lista fragmentos literais (vindo de TokLit) com suas
    positions absolutas em s, apos sub-divisao por quebras."""
    s = unicas[eid - 1]
    qa = quebras[eid]
    out = []
    pos = 0
    for tok in tokens_eid:
        if isinstance(tok, TokLit):
            sl, el = pos, pos + len(tok.text)
            qs = sorted(q for q in qa if sl < q < el)
            pts = [sl] + qs + [el]
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i + 1]
                out.append((a, b, s[a:b]))
            pos = el
        else:
            pos += tok.length
    return out


def processar_ds(nome):
    linhas = ler_csv(THIS / "data" / f"{nome}.csv")
    seen = OrderedDict()
    for s in linhas:
        seen[s] = True
    unicas = list(seen.keys())
    tokens, _ = processar(unicas, min_len=3)
    return linhas, unicas, tokens


def main():
    out_dir = THIS / "tokens_dump"
    out_dir.mkdir(exist_ok=True)
    relatorio_geral = []

    for nome in DATASETS:
        linhas, unicas, tokens = processar_ds(nome)
        linhas_relat = []
        linhas_relat.append("=" * 90)
        linhas_relat.append(f"DATASET: {nome}  ({len(unicas)} strings unicas)")
        linhas_relat.append("=" * 90)

        syn_a = M1A()
        quebras = syn_a._coletar_quebras(unicas, tokens)

        tcf_a = M1A().encode(linhas, unicas, tokens, "")
        tcf_b = M1B().encode(linhas, unicas, tokens, "")
        a_lines = [l for l in tcf_a.splitlines() if l not in ("[", "]")]
        b_lines = [l for l in tcf_b.splitlines() if l not in ("[", "]")]

        b_a = len(tcf_a.encode("utf-8"))
        b_b = len(tcf_b.encode("utf-8"))
        linhas_relat.append(
            f"M1.A: {b_a} bytes    M1.B: {b_b} bytes    diff: {b_b - b_a:+d}")

        for idx, s in enumerate(unicas, start=1):
            toks = tokens[idx - 1]
            frags = fragmentos_de_no(idx, toks, unicas, quebras)
            linhas_relat.append("")
            linhas_relat.append(f"  eid={idx}: {s!r}")
            linhas_relat.append(
                f"    tokens (online.py raiz): "
                f"[{', '.join(fmt_tok(t) for t in toks)}]")
            if frags:
                frags_str = ' | '.join(
                    f"[{a}:{b}]={t!r}" for a, b, t in frags)
                linhas_relat.append(f"    fragmentos literais: {frags_str}")
            else:
                linhas_relat.append(
                    f"    fragmentos literais: (nenhum -- so' refs)")
            if idx - 1 < len(a_lines):
                linhas_relat.append(f"    M1.A: {a_lines[idx - 1]}")
            if idx - 1 < len(b_lines):
                linhas_relat.append(f"    M1.B: {b_lines[idx - 1]}")

        # Salvar relatorio individual + acumular geral
        relat_str = "\n".join(linhas_relat)
        (out_dir / f"{nome}.txt").write_text(relat_str, encoding="utf-8")
        relatorio_geral.append(relat_str)
        print(relat_str)
        print()

    # Salvar tudo agregado
    (out_dir / "_TODOS.txt").write_text(
        "\n\n".join(relatorio_geral), encoding="utf-8")
    print(f"\nRelatorios salvos em: {out_dir}/")


if __name__ == "__main__":
    main()
