"""run_lote.py — M12 (welding step 2: M8.A composicional em src/tcf/composicional/).

Smoke test do welding step 2: M8.A vem de
`src/tcf/composicional/syntax.py` (com imports adaptados pra
`tcf.core.online` e `tcf.core.syntax_base`). alg16 ja' welded em
step 1 (`src/tcf/core/online.py`).

Validacao: bytes byte-a-byte identicos a M11/M10/M9.
"""

import csv
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent

# Welding step 2: M8.A composicional + alg16 vem de src/tcf/.
# Adiciona src/ ao path para `from tcf.core.online import ...` e
# `from tcf.composicional.syntax import ...` resolverem como package.
SRC = THIS.parents[3] / "src"
sys.path.insert(0, str(SRC))

DATASETS_DIR = THIS.parents[3] / "datasets" / "synthetic"

from tcf.core.online import processar, reconstroi, TokLit, TokRefPref, TokRefSuf
from tcf.composicional.syntax import M8AVirtualRefsSyntax


def write_lf(path, content):
    path.write_bytes(content.encode("utf-8"))


def _carregar_sintaxe(folder_name):
    """M12: pasta -> class. M8-A-src e' carregada via import direto de
    `src/tcf/composicional/`. Sem dynamic loader local (welding step 2
    valida a import path como package)."""
    if folder_name == "M8-A-src":
        return M8AVirtualRefsSyntax
    raise RuntimeError(f"Folder desconhecido em M12: {folder_name}")


SINTAXES_REGISTRADAS = ["M8-A-src"]

DATASETS = [
    "D1-emails-simples",
    "D2-emails-quote-id",
    "D3-stress-substring",
    "D4-caos-mix",
    "D5-padroes-multiplos",
    "D6-poucos-em-ruido",
    "D7-aninhamento",
    "D8-cabeca-cauda",
    "D9-frequencia-alta",
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
            f"# Strings unicas: {len(unicas)}", "", "=" * 80]
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


def rodar_micro(syn, nome_ds, linhas, unicas, tokens, header, micro_dir):
    for sub in ("output", "decoded", "debug", "detector_trace", "redes"):
        (micro_dir / sub).mkdir(parents=True, exist_ok=True)
    try:
        tcf = syn.encode(linhas, unicas, tokens, header)
    except Exception as e:
        import traceback
        write_lf(micro_dir / "debug" / f"{nome_ds}.txt",
                  f"ENCODE FAILED: {e}\n{traceback.format_exc()}\n")
        return {"ok": False, "stage": "encode", "err": str(e), "bytes": -1}
    write_lf(micro_dir / "output" / f"{nome_ds}.tcf", tcf)
    n_bytes = len(tcf.encode("utf-8"))
    try:
        decoded = syn.decode(tcf)
    except Exception as e:
        import traceback
        write_lf(micro_dir / "debug" / f"{nome_ds}.txt",
                  f"DECODE FAILED: {e}\n{traceback.format_exc()}\n\nTCF:\n{tcf}\n")
        return {"ok": False, "stage": "decode", "err": str(e), "bytes": n_bytes}
    with (micro_dir / "decoded" / f"{nome_ds}.csv").open(
            "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([header])
        for line in decoded:
            w.writerow([line])
    rt_ok = decoded == linhas
    debug = [f"# Debug — sintaxe={syn.name} dataset={nome_ds}",
              f"# bytes={n_bytes}  roundtrip={'OK' if rt_ok else 'FAIL'}", "",
              "=" * 80, "INPUT", "=" * 80]
    for i, l in enumerate(linhas, 1):
        debug.append(f"  [{i}] {l}")
    debug.append("")
    debug.append("=" * 80 + "\nTCF (encode)\n" + "=" * 80)
    for line in tcf.splitlines():
        debug.append(f"  {line}")
    debug.append("")
    debug.append("=" * 80 + "\nDECODE\n" + "=" * 80)
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
        write_lf(micro_dir / "detector_trace" / f"{nome_ds}.txt", syn.get_trace())
    if hasattr(syn, 'get_rede') and syn.get_rede():
        write_lf(micro_dir / "redes" / f"{nome_ds}.txt", syn.get_rede())
    return {"ok": rt_ok, "stage": "complete", "bytes": n_bytes,
            "raw_bytes": sum(len(l.encode('utf-8')) + 1 for l in linhas)}


def gerar_relatorio(resultados, datasets, sintaxes_nomes, base_out):
    md = ["# M9 — Stress adversarial (M8.A em D1-D9)", "",
           f"Sintaxes: {', '.join(sintaxes_nomes)}",
           f"Datasets: {', '.join(datasets)}", "",
           "## Bytes por dataset", "",
           "| dataset | " + " | ".join(sintaxes_nomes) + " | raw | ratio | RT |",
           "|" + "|".join("---" for _ in range(len(sintaxes_nomes) + 4)) + "|"]
    for ds in datasets:
        row = [ds]
        for sn in sintaxes_nomes:
            r = resultados[(sn, ds)]
            row.append(str(r["bytes"]) if r["ok"] else "FAIL")
        r0 = resultados[(sintaxes_nomes[0], ds)]
        if r0["ok"]:
            row.append(str(r0.get("raw_bytes", "?")))
            row.append(f"{r0['bytes']/r0['raw_bytes']:.2%}")
            row.append("OK" if r0["ok"] else "FAIL")
        else:
            row.extend(["?", "?", "FAIL"])
        md.append("| " + " | ".join(row) + " |")
    write_lf(base_out / "matriz_comparativa.md", "\n".join(md))


def main():
    base_out = THIS / "resultados"
    base_out.mkdir(exist_ok=True)
    tokens_dir = base_out / "tokens"
    print(f"=== run_lote — M12 (welding step 2: M8.A composicional em src/) ===")
    print(f"Sintaxes: {SINTAXES_REGISTRADAS}\nDatasets: {DATASETS}\n")
    sintaxes_classes = [(folder, _carregar_sintaxe(folder))
                         for folder in SINTAXES_REGISTRADAS]
    resultados = {}
    sintaxes_nomes = [k.name for _, k in sintaxes_classes]
    for ds in DATASETS:
        print(f"-- {ds} --")
        header, linhas = ler_csv(DATASETS_DIR / f"{ds}.csv")
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
            r = rodar_micro(syn, ds, linhas, unicas, tokens, header, micro_dir)
            resultados[(syn.name, ds)] = r
            mark = "OK" if r["ok"] else f"FAIL({r['stage']})"
            ratio = (f" ({r['bytes']/r['raw_bytes']:.0%} raw)"
                     if r.get('raw_bytes') and r.get('bytes', -1) > 0 else "")
            print(f"  {syn.name:<24} [{mark}] {r.get('bytes', '?')} bytes{ratio}")
        print()
    gerar_relatorio(resultados, DATASETS, sintaxes_nomes, base_out)
    print(f"Relatorios em: {base_out}/")


if __name__ == "__main__":
    main()
