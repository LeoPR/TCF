"""run_lote.py — M5 (pilha M2.A + M4.C1').

Adaptado de M3/M4 (autocontido por micro).

SINTAXES_REGISTRADAS:
- M1-E-range-baseline       (referencia base)
- M2-A-alias-tupla          (referencia)
- M4-C1p-batch-subsequencias (referencia, lider atual)
- M5-A-pilha-hibrida         (detector que considera ambos custos)
"""

import csv
import importlib.util
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
sys.path.insert(0, str(THIS))

from online import processar, reconstroi, TokLit, TokRefPref, TokRefSuf


def _carregar_sintaxe(folder_name):
    path = THIS / folder_name / "syntax.py"
    spec = importlib.util.spec_from_file_location(
        f"sintaxe_{folder_name.replace('-', '_')}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    from syntax_base import Syntax
    for attr in dir(mod):
        obj = getattr(mod, attr)
        if (isinstance(obj, type) and issubclass(obj, Syntax)
                and obj is not Syntax):
            return obj
    raise RuntimeError(f"Sintaxe nao encontrada em {path}")


SINTAXES_REGISTRADAS = [
    "M1-E-range-baseline",
    "M2-A-alias-tupla",
    "M4-C1p-batch-subsequencias",
    "M5-A-pilha-hibrida",
]

DATASETS = [
    "D1-emails-simples",
    "D2-emails-quote-id",
    "D3-stress-substring",
    "D4-caos-mix",
]


def ler_csv(path):
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)[0]
        return header, [row[0] for row in r if row]


def fmt_tok(tok):
    if isinstance(tok, TokLit):
        return f"L({tok.text!r})"
    if isinstance(tok, TokRefPref):
        return f"P({tok.string_id},{tok.length})"
    return f"S({tok.string_id},{tok.length})"


def coletar_quebras_e_frags(unicas, tokens_por_string):
    quebras = {eid: set() for eid in range(1, len(unicas) + 1)}
    for tokens in tokens_por_string:
        for tok in tokens:
            if isinstance(tok, TokRefPref):
                quebras[tok.string_id].add(tok.length)
            elif isinstance(tok, TokRefSuf):
                s_ref = unicas[tok.string_id - 1]
                quebras[tok.string_id].add(len(s_ref) - tok.length)
    for eid in range(len(unicas), 0, -1):
        tokens = tokens_por_string[eid - 1]
        pos = 0
        for tok in tokens:
            if isinstance(tok, TokLit):
                pos += len(tok.text)
            elif isinstance(tok, TokRefPref):
                cov = tok.length
                for q in list(quebras[eid]):
                    if pos < q < pos + cov:
                        quebras[tok.string_id].add(q - pos)
                pos += cov
            else:
                cov = tok.length
                rs = len(unicas[tok.string_id - 1]) - cov
                for q in list(quebras[eid]):
                    if pos < q < pos + cov:
                        quebras[tok.string_id].add((q - pos) + rs)
                pos += cov

    frags_por_no = {}
    for eid in range(1, len(unicas) + 1):
        s = unicas[eid - 1]
        qa = quebras[eid]
        frags = []
        pos = 0
        for tok in tokens_por_string[eid - 1]:
            if isinstance(tok, TokLit):
                sl, el = pos, pos + len(tok.text)
                qs = sorted(q for q in qa if sl < q < el)
                pts = [sl] + qs + [el]
                for i in range(len(pts) - 1):
                    a, b = pts[i], pts[i + 1]
                    frags.append((a, b, s[a:b]))
                pos = el
            else:
                pos += tok.length
        frags_por_no[eid] = frags
    return frags_por_no


def salvar_tokens(nome_ds, unicas, tokens, frags_por_no, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    linhas_out = []
    linhas_out.append(f"# Tokens raiz (online.py exp 16) — {nome_ds}")
    linhas_out.append(f"# Strings unicas: {len(unicas)}")
    linhas_out.append("")
    linhas_out.append("=" * 80)
    for eid, s in enumerate(unicas, start=1):
        toks = tokens[eid - 1]
        frags = frags_por_no.get(eid, [])
        linhas_out.append("")
        linhas_out.append(f"eid={eid}: {s!r}")
        linhas_out.append(
            f"  tokens: [{', '.join(fmt_tok(t) for t in toks)}]")
        if frags:
            frags_str = ' | '.join(f"[{a}:{b}]={t!r}" for a, b, t in frags)
            linhas_out.append(f"  fragmentos literais: {frags_str}")
        else:
            linhas_out.append(f"  fragmentos literais: (nenhum)")
    (out_dir / f"{nome_ds}.txt").write_text(
        "\n".join(linhas_out), encoding="utf-8")


def rodar_micro_em_dataset(syn, nome_ds, linhas, unicas, tokens,
                              frags_por_no, header, micro_dir):
    output_dir = micro_dir / "output"
    decoded_dir = micro_dir / "decoded"
    debug_dir = micro_dir / "debug"
    output_dir.mkdir(parents=True, exist_ok=True)
    decoded_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)

    try:
        tcf = syn.encode(linhas, unicas, tokens, header)
    except Exception as e:
        (debug_dir / f"{nome_ds}.txt").write_text(
            f"ENCODE FAILED: {e}\n", encoding="utf-8")
        return {"ok": False, "stage": "encode", "err": str(e), "bytes": -1}

    (output_dir / f"{nome_ds}.tcf").write_text(tcf, encoding="utf-8")
    n_bytes = len(tcf.encode("utf-8"))

    try:
        decoded = syn.decode(tcf)
    except Exception as e:
        (debug_dir / f"{nome_ds}.txt").write_text(
            f"DECODE FAILED: {e}\n\nTCF:\n{tcf}\n", encoding="utf-8")
        return {"ok": False, "stage": "decode", "err": str(e),
                "bytes": n_bytes, "tcf": tcf}

    with (decoded_dir / f"{nome_ds}.csv").open(
            "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([header])
        for line in decoded:
            w.writerow([line])

    rt_ok = decoded == linhas

    debug = []
    debug.append(f"# Debug — sintaxe={syn.name} dataset={nome_ds}")
    debug.append(f"# bytes={n_bytes}  roundtrip={'OK' if rt_ok else 'FAIL'}")
    debug.append("")
    debug.append("=" * 80)
    debug.append("INPUT")
    debug.append("=" * 80)
    for i, l in enumerate(linhas, 1):
        debug.append(f"  [{i}] {l}")
    debug.append("")
    debug.append("=" * 80)
    debug.append("TOKENS (raiz online.py)")
    debug.append("=" * 80)
    for eid, s in enumerate(unicas, start=1):
        toks = tokens[eid - 1]
        frags = frags_por_no.get(eid, [])
        debug.append(f"  eid={eid}: {s!r}")
        debug.append(f"    tokens: [{', '.join(fmt_tok(t) for t in toks)}]")
        if frags:
            frags_str = ' | '.join(f"[{a}:{b}]={t!r}" for a, b, t in frags)
            debug.append(f"    fragmentos: {frags_str}")
    debug.append("")
    debug.append("=" * 80)
    debug.append(f"TCF (encode — {syn.name})")
    debug.append("=" * 80)
    for line in tcf.splitlines():
        debug.append(f"  {line}")
    debug.append("")
    debug.append("=" * 80)
    debug.append("DECODE (contra-prova)")
    debug.append("=" * 80)
    for i, line in enumerate(decoded, 1):
        orig = linhas[i - 1] if i - 1 < len(linhas) else "(faltando)"
        marca = " " if line == orig else "X"
        debug.append(f"  [{marca}] {line}")
    debug.append("")
    if rt_ok:
        debug.append(f"  -> {len(decoded)} linhas reconstruidas IGUAIS")
    else:
        n_iguais = sum(1 for a, b in zip(decoded, linhas) if a == b)
        debug.append(f"  -> {n_iguais}/{len(linhas)} linhas iguais")
    (debug_dir / f"{nome_ds}.txt").write_text(
        "\n".join(debug), encoding="utf-8")

    return {"ok": rt_ok, "stage": "complete", "bytes": n_bytes, "tcf": tcf}


def gerar_relatorio(resultados, datasets, sintaxes_nomes, base_out):
    with (base_out / "matriz_bytes.csv").open(
            "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["dataset"] + sintaxes_nomes + ["menor"])
        for ds in datasets:
            row = [ds]
            bytes_por_syn = {}
            for sn in sintaxes_nomes:
                r = resultados[(sn, ds)]
                if r["ok"]:
                    row.append(r["bytes"])
                    bytes_por_syn[sn] = r["bytes"]
                else:
                    row.append("FAIL")
            if bytes_por_syn:
                menor = min(bytes_por_syn, key=bytes_por_syn.get)
                row.append(menor)
            else:
                row.append("(nenhum)")
            w.writerow(row)

    md = []
    md.append("# M5 — Matriz comparativa (pilha M2.A + M4.C1')")
    md.append("")
    md.append(f"Sintaxes: {', '.join(sintaxes_nomes)}")
    md.append(f"Datasets: {', '.join(datasets)}")
    md.append("")
    md.append("Cada micro tem suas pastas output/decoded/debug autocontidas:")
    for sn in sintaxes_nomes:
        md.append(f"- `{sn}/output/<dataset>.tcf`")
        md.append(f"- `{sn}/decoded/<dataset>.csv`")
        md.append(f"- `{sn}/debug/<dataset>.txt`")
    md.append("")
    md.append("## Bytes por (sintaxe x dataset)")
    md.append("")
    cols = ["dataset"] + sintaxes_nomes + ["delta_min_max"]
    md.append("| " + " | ".join(cols) + " |")
    md.append("|" + "|".join("---" for _ in cols) + "|")
    totais = {sn: 0 for sn in sintaxes_nomes}
    for ds in datasets:
        row = [ds]
        bytes_por_syn = {}
        for sn in sintaxes_nomes:
            r = resultados[(sn, ds)]
            if r["ok"]:
                row.append(str(r["bytes"]))
                bytes_por_syn[sn] = r["bytes"]
                totais[sn] += r["bytes"]
            else:
                row.append("X")
        if bytes_por_syn:
            mn = min(bytes_por_syn.values())
            mx = max(bytes_por_syn.values())
            row.append(f"{mx - mn}")
        else:
            row.append("---")
        md.append("| " + " | ".join(row) + " |")
    row = ["**TOTAL**"]
    for sn in sintaxes_nomes:
        row.append(f"**{totais[sn]}**")
    row.append("---")
    md.append("| " + " | ".join(row) + " |")
    md.append("")
    md.append("## Roundtrip")
    md.append("")
    md.append("| dataset | " + " | ".join(sintaxes_nomes) + " |")
    md.append("|" + "|".join("---" for _ in range(len(sintaxes_nomes) + 1)) + "|")
    for ds in datasets:
        row = [ds]
        for sn in sintaxes_nomes:
            r = resultados[(sn, ds)]
            mark = "OK" if r["ok"] else f"FAIL({r['stage']})"
            row.append(mark)
        md.append("| " + " | ".join(row) + " |")
    (base_out / "matriz_comparativa.md").write_text(
        "\n".join(md), encoding="utf-8")


def main():
    base_out = THIS / "resultados"
    base_out.mkdir(exist_ok=True)
    tokens_dir = base_out / "tokens"

    print(f"=== run_lote — M5 (pilha M2.A + M4.C1') ===")
    print(f"Sintaxes: {SINTAXES_REGISTRADAS}")
    print(f"Datasets: {DATASETS}")
    print()

    sintaxes_classes = []
    for folder in SINTAXES_REGISTRADAS:
        klass = _carregar_sintaxe(folder)
        sintaxes_classes.append((folder, klass))
        print(f"  [carregada] {folder} -> {klass.__name__}")
    print()

    resultados = {}
    sintaxes_nomes = [k.name for _, k in sintaxes_classes]

    for ds in DATASETS:
        print(f"-- {ds} --")
        header, linhas = ler_csv(THIS / "data" / f"{ds}.csv")
        seen = OrderedDict()
        for s in linhas:
            seen[s] = True
        unicas = list(seen.keys())
        tokens, _ = processar(unicas, min_len=3)
        for s, t in zip(unicas, tokens):
            assert reconstroi(t, unicas) == s

        frags_por_no = coletar_quebras_e_frags(unicas, tokens)
        salvar_tokens(ds, unicas, tokens, frags_por_no, tokens_dir)

        for folder, klass in sintaxes_classes:
            syn = klass()
            micro_dir = THIS / folder
            r = rodar_micro_em_dataset(
                syn, ds, linhas, unicas, tokens,
                frags_por_no, header, micro_dir)
            resultados[(syn.name, ds)] = r
            marca = "OK" if r["ok"] else f"FAIL({r['stage']})"
            print(f"  {syn.name:<32} [{marca}] {r.get('bytes', '?')} bytes")
        print()

    gerar_relatorio(resultados, DATASETS, sintaxes_nomes, base_out)
    print(f"Relatorios em: {base_out}/")
    print(f"  - matriz_comparativa.md")
    print(f"  - matriz_bytes.csv")
    print(f"  - tokens/*.txt")
    print(f"  - <micro>/output|decoded|debug/<dataset>.*")


if __name__ == "__main__":
    main()
