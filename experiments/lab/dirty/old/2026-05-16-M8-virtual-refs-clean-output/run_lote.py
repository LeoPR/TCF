"""run_lote.py — M8 (detector unificado + convencao output).

Convencao output (ver `../notas/convencao-output-tcf.md`):
- Sem brackets `[`/`]` (cada syntax emit ja' nao adiciona)
- LF only (single `\n`); write_text com `newline=''` para preservar
"""

import csv
import importlib.util
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
sys.path.insert(0, str(THIS))

from online import processar, reconstroi, TokLit, TokRefPref, TokRefSuf


def write_lf(path, content):
    """Escreve content preservando LF (sem CRLF translation)."""
    path.write_bytes(content.encode("utf-8"))


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
    "M1-E-clean",
    "M7-A-clean",
    "M8-A-detector-unificado",
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


def coletar_frags(unicas, tokens_por_string):
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
            else:
                cov = tok.length
                if isinstance(tok, TokRefPref):
                    rs = 0
                else:
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
                for a, b in zip([sl] + qs, qs + [el]):
                    frags.append((a, b, s[a:b]))
                pos = el
            else:
                pos += tok.length
        frags_por_no[eid] = frags
    return frags_por_no


def gerar_tokens_raiz(nome_ds, unicas, tokens, frags_por_no, tokens_dir):
    tokens_dir.mkdir(parents=True, exist_ok=True)
    out = [f"# Tokens raiz (online.py exp 16) — {nome_ds}",
            f"# Strings unicas: {len(unicas)}",
            "", "=" * 80]
    for eid, s in enumerate(unicas, start=1):
        toks = tokens[eid - 1]
        frags = frags_por_no.get(eid, [])
        out.append("")
        out.append(f"eid={eid}: {s!r}")
        out.append(f"  tokens: [{', '.join(fmt_tok(t) for t in toks)}]")
        if frags:
            frags_str = ' | '.join(f"[{a}:{b}]={t!r}" for a, b, t in frags)
            out.append(f"  fragmentos: {frags_str}")
    write_lf(tokens_dir / f"{nome_ds}.txt", "\n".join(out))


def rodar_micro(syn, nome_ds, linhas, unicas, tokens,
                  header, micro_dir):
    for sub in ("output", "decoded", "debug",
                 "detector_trace", "redes"):
        (micro_dir / sub).mkdir(parents=True, exist_ok=True)

    try:
        tcf = syn.encode(linhas, unicas, tokens, header)
    except Exception as e:
        import traceback
        write_lf(micro_dir / "debug" / f"{nome_ds}.txt",
                  f"ENCODE FAILED: {e}\n{traceback.format_exc()}\n")
        return {"ok": False, "stage": "encode", "err": str(e),
                "bytes": -1}

    write_lf(micro_dir / "output" / f"{nome_ds}.tcf", tcf)
    n_bytes = len(tcf.encode("utf-8"))

    try:
        decoded = syn.decode(tcf)
    except Exception as e:
        import traceback
        write_lf(micro_dir / "debug" / f"{nome_ds}.txt",
                  f"DECODE FAILED: {e}\n{traceback.format_exc()}\n\nTCF:\n{tcf}\n")
        return {"ok": False, "stage": "decode", "err": str(e),
                "bytes": n_bytes, "tcf": tcf}

    with (micro_dir / "decoded" / f"{nome_ds}.csv").open(
            "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([header])
        for line in decoded:
            w.writerow([line])

    rt_ok = decoded == linhas

    debug = [f"# Debug — sintaxe={syn.name} dataset={nome_ds}",
              f"# bytes={n_bytes}  roundtrip={'OK' if rt_ok else 'FAIL'}",
              "", "=" * 80, "INPUT", "=" * 80]
    for i, l in enumerate(linhas, 1):
        debug.append(f"  [{i}] {l}")
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
        mark = " " if line == orig else "X"
        debug.append(f"  [{mark}] {line}")
    debug.append("")
    if rt_ok:
        debug.append(f"  -> {len(decoded)} linhas reconstruidas IGUAIS")
    else:
        n_iguais = sum(1 for a, b in zip(decoded, linhas) if a == b)
        debug.append(f"  -> {n_iguais}/{len(linhas)} linhas iguais")
    write_lf(micro_dir / "debug" / f"{nome_ds}.txt", "\n".join(debug))

    if hasattr(syn, 'get_trace') and syn.get_trace():
        write_lf(micro_dir / "detector_trace" / f"{nome_ds}.txt",
                  syn.get_trace())
    if hasattr(syn, 'get_rede') and syn.get_rede():
        write_lf(micro_dir / "redes" / f"{nome_ds}.txt", syn.get_rede())

    return {"ok": rt_ok, "stage": "complete", "bytes": n_bytes, "tcf": tcf}


def gerar_relatorio(resultados, datasets, sintaxes_nomes, base_out):
    with (base_out / "matriz_bytes.csv").open(
            "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["dataset"] + sintaxes_nomes + ["menor"])
        for ds in datasets:
            row = [ds]
            by_syn = {}
            for sn in sintaxes_nomes:
                r = resultados[(sn, ds)]
                if r["ok"]:
                    row.append(r["bytes"])
                    by_syn[sn] = r["bytes"]
                else:
                    row.append("FAIL")
            menor = (min(by_syn, key=by_syn.get) if by_syn else "(nenhum)")
            row.append(menor)
            w.writerow(row)

    md = ["# M8 — Matriz comparativa (detector unificado + convencao output)",
           "",
           f"Sintaxes: {', '.join(sintaxes_nomes)}",
           f"Datasets: {', '.join(datasets)}",
           "",
           "## Bytes por (sintaxe x dataset)",
           "",
           "| " + " | ".join(["dataset"] + sintaxes_nomes + ["delta"]) + " |",
           "|" + "|".join("---" for _ in range(len(sintaxes_nomes) + 2)) + "|"]
    totais = {sn: 0 for sn in sintaxes_nomes}
    for ds in datasets:
        row = [ds]
        by = {}
        for sn in sintaxes_nomes:
            r = resultados[(sn, ds)]
            if r["ok"]:
                row.append(str(r["bytes"]))
                by[sn] = r["bytes"]
                totais[sn] += r["bytes"]
            else:
                row.append("X")
        if by:
            row.append(f"{max(by.values()) - min(by.values())}")
        else:
            row.append("---")
        md.append("| " + " | ".join(row) + " |")
    row = ["**TOTAL**"] + [f"**{totais[sn]}**" for sn in sintaxes_nomes] + ["---"]
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
    write_lf(base_out / "matriz_comparativa.md", "\n".join(md))


def main():
    base_out = THIS / "resultados"
    base_out.mkdir(exist_ok=True)
    tokens_dir = base_out / "tokens"

    print(f"=== run_lote — M8 (detector unificado + clean output) ===")
    print(f"Sintaxes: {SINTAXES_REGISTRADAS}")
    print(f"Datasets: {DATASETS}")
    print()

    sintaxes_classes = [
        (folder, _carregar_sintaxe(folder))
        for folder in SINTAXES_REGISTRADAS
    ]
    for folder, klass in sintaxes_classes:
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

        frags_por_no = coletar_frags(unicas, tokens)
        gerar_tokens_raiz(ds, unicas, tokens, frags_por_no, tokens_dir)

        for folder, klass in sintaxes_classes:
            syn = klass()
            micro_dir = THIS / folder
            r = rodar_micro(syn, ds, linhas, unicas, tokens,
                              header, micro_dir)
            resultados[(syn.name, ds)] = r
            mark = "OK" if r["ok"] else f"FAIL({r['stage']})"
            print(f"  {syn.name:<32} [{mark}] {r.get('bytes', '?')} bytes")
        print()

    gerar_relatorio(resultados, DATASETS, sintaxes_nomes, base_out)
    print(f"Relatorios em: {base_out}/")


if __name__ == "__main__":
    main()
