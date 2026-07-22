"""run.py — Ciclo 1b: escala de FORMAS + decisão de TIPO com número (A vs B vs C).

Thread 1 (tipo): mede A-explícita / B-dedução / C-híbrida em casos numéricos e ambíguos —
  bytes, RT (OK/LOSSY) e #tags. A decisão sai daqui.
Thread 2 (forma): escala formas de borda (aninhamento fundo, array vazio, chave ausente, null-em-array)
  — prova o que fecha RT e o que é FRONTEIRA honesta (crash caracterizado, não silencioso).

`python run.py` regenera artifacts/. Ponteiro de escala: datasets/synthetic/ (D1-D17, CSV).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8")          # console Windows cp1252 não engole '→'
except Exception:
    pass
import tipos_codec as TC                               # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)
LAB1A = HERE.parent / "2026-07-06-2221-tcf8h-fidelidade-tipos" / "inputs"


def nb(s): return len(s.encode("utf-8"))
def w(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")
def ntags(letters): return sum(1 for l in letters if l)


# ---------- Thread 1: estratégias de tipo ----------
def type_cases():
    cases = {}
    for tag in ("T1-escalares-tipados", "T2-array-tipado", "T3-aninhado-misto"):
        cases[tag] = json.loads((LAB1A / f"{tag}.json").read_text(encoding="utf-8"))
    cases["NUM-numeros-dominam"] = {"x": 1, "y": 2, "z": 3, "nome": "ana"}
    cases["AMB-strings-ambiguas"] = {"cep": "01310", "flag": "true", "n": 30, "nome": "ana"}
    return cases


def thread_types():
    L = ["# THREAD 1 — decisão de TIPO com número: A-explícita vs B-dedução vs C-híbrida", "",
         "A = tag em toda não-string (lossless, caro). B = sem tag, deduz (lossy em ambiguidade).",
         "C = tag só onde a dedução erraria (lossless, barato quando números dominam).", ""]
    tabela = ["| caso | A bytes/tags/RT | B bytes/tags/RT | C bytes/tags/RT |",
              "|---|---|---|---|"]
    for tag, src in type_cases().items():
        row = [f"| {tag} "]
        L.append(f"## {tag}\n  {json.dumps(src, ensure_ascii=False)}")
        for name in ("A-explicita", "B-deducao", "C-hibrida"):
            enc, dec = TC.STRAT[name]
            blob, letters = enc(src)
            back = dec(blob)
            ok = back == src
            L.append(f"  {name:12s} {nb(blob):3d}B  tags={ntags(letters)}  RT={'OK' if ok else 'LOSSY'}"
                     f"  meta={blob.splitlines()[0]!r}")
            if not ok:
                L.append(f"     LOSSY out: {back}")
            row.append(f"{nb(blob)}/{ntags(letters)}/{'OK' if ok else 'LOSSY'} ")
        L.append("")
        tabela.append("|".join(row) + "|")
    L += ["## tabela", ""] + tabela + ["",
          "LEITURA: B só é lossless quando não há string-ambígua; corrompe cep '01310'→1310, 'true'→bool,",
          "null→string vazia. A é sempre lossless mas paga toda não-string. C = lossless E o mais barato",
          "quando números dominam (deduz de graça, tag só a colisão).",
          "",
          "REGRA (do número): custo_A = #não-string; custo_C = #mal-deduzidos (strings-ambíguas + null).",
          "C < A  sse  (não-strings bem-deduzidos) > (strings-ambíguas). Em NUM/T1/T2/T3 C≤A (lossless).",
          "Em AMB (2 strings ambíguas > 1 número) C=52 > A=51: A vence. C default; A fallback quando",
          "strings-ambíguas dominam. B nunca default (lossy silencioso)."]
    w("01-tipos-A-B-C.txt", "\n".join(L) + "\n")
    return L


# ---------- Thread 2: escala de formas ----------
def shape_cases():
    return {
        "SH1-aninhamento-fundo": {"a": {"b": {"c": {"d": 1}}}},
        "SH2-array-vazio": {"nome": "x", "tags": []},
        "SH3-chave-ausente": {"linhas": [{"a": 1, "b": 2}, {"a": 3}]},
        "SH4-null-em-array-misto": {"linhas": [{"x": 1}, {"x": None}]},
    }


def thread_shapes():
    L = ["# THREAD 2 — escala de FORMAS (estratégia C-híbrida): o que fecha RT e o que é FRONTEIRA", ""]
    status = []
    for tag, src in shape_cases().items():
        L.append(f"## {tag}\n  {json.dumps(src, ensure_ascii=False)}")
        try:
            blob, letters = TC.encode_C(src)
            back = TC.decode_C(blob)
            ok = back == src
            L.append(f"  encode OK {nb(blob)}B  RT={'OK' if ok else 'MISMATCH'}  meta={blob.splitlines()[0]!r}")
            if not ok:
                L.append(f"  in : {src}\n  out: {back}")
            status.append((tag, "RT-OK" if ok else "RT-MISMATCH"))
        except Exception as e:
            L.append(f"  FRONTEIRA: {type(e).__name__}: {e}")
            status.append((tag, f"FRONTEIRA ({type(e).__name__})"))
        L.append("")
    L += ["## diagnóstico das fronteiras", "",
          "- SH3 chave-ausente: a tabela vira NÃO-retangular (linha 2 sem 'b'). O modelo colunar supõe",
          "  retângulo → precisa de presença (bitmap/sentinela). É a mesma família do link posicional (1c).",
          "- SH4 null-em-array-misto: coluna [1, null] tem tipo MISTO (int+null) → a tag por-coluna não",
          "  basta; precisa de nullable-int (tag por-coluna 'i?' ou máscara de null). Caracterizado, não v0.",
          "- SH1/SH2 (aninhamento fundo, array vazio): fecham RT → funcionalidade estendida de graça."]
    w("02-formas-fronteiras.txt", "\n".join(L) + "\n")
    return status


def main():
    thread_types()
    st = thread_shapes()

    # trace por coluna (SideOutputs) num caso representativo (T3)
    from tcf import encode as _enc, SideOutputs
    src3 = json.loads((LAB1A / "T3-aninhado-misto.json").read_text(encoding="utf-8"))
    tl = ["# TRACE OBAT/HCC por coluna (SideOutputs) — T3 (representativo)", ""]
    for name, bodies, letter in TC.TC._dfs_cols(src3):
        side = SideOutputs(); _enc(bodies, side_outputs=side)
        per = (side.per_col or {})
        s = per.get(0) or (next(iter(per.values())) if per else None)
        tl.append(f"  col({name}) tipo={letter or 's'} bodies={bodies} -> body_bytes={getattr(s,'body_bytes','?') if s else '?'}")
    w("03-obat-hcc-trace.txt", "\n".join(tl) + "\n")

    R = ["# Ciclo 1b — escala de formas + decisão de tipo (A/B/C) [resumo]", "",
         "## Tipo (thread 1) — bytes/tags/RT por estratégia"]
    for tag, src in type_cases().items():
        parts = []
        for name in ("A-explicita", "B-deducao", "C-hibrida"):
            enc, dec = TC.STRAT[name]
            blob, letters = enc(src); ok = dec(blob) == src
            parts.append(f"{name.split('-')[0]}={nb(blob)}B/{ntags(letters)}t/{'OK' if ok else 'LOSSY'}")
        R.append(f"  {tag:24s} " + "  ".join(parts))
    R += ["", "## Forma (thread 2) — RT vs fronteira"]
    for tag, s in st:
        R.append(f"  {tag:24s} {s}")
    R += ["", "## Decisão (do número)",
          "- **C-híbrida = default**: lossless como A; deduz número/bool/null-ok de graça, tag só a colisão",
          "  (string-ambígua → 's'; null → 'n'). REGRA: custo_A=#não-string, custo_C=#mal-deduzidos;",
          "  C<A sse não-strings-bem-deduzidos > strings-ambíguas. T1/T2/T3/NUM: C≤A. AMB: C=52 > A=51",
          "  (2 strings ambíguas > 1 número) — A vence lá. Não é 'C sempre'; é config-dependente.",
          "- **B pura** descartada como default: corrompe silenciosamente (cep '01310'→1310, null→'').",
          "- **A** = fallback (tudo taggeado): simples/auditável, e MENOR quando strings-ambíguas dominam.",
          "## Fronteiras (viram 1c / char. honesta)",
          "- chave-ausente + null-em-array-misto = tabela não-retangular / coluna de tipo misto → família do",
          "  link posicional (peça 10/11). Aninhamento fundo e array vazio já fecham RT."]
    w("00-resumo.txt", "\n".join(R) + "\n")

    print("artifacts em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:24s} {p.stat().st_size:6d} B")
    print("\n" + "\n".join(R))


if __name__ == "__main__":
    main()
