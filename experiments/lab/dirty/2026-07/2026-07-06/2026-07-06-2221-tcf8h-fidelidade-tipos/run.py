"""run.py — Ciclo 1a: FIDELIDADE DE TIPOS no TCF.8H (dirty).

Prova a lacuna e o conserto naive:
  baseline all-string (str(v), como EXP-015) → RT FALHA em JSON tipado;
  typed_codec (tag de tipo só na divergência) → RT EXATO, medindo o custo em bytes.

`python run.py` regenera artifacts/. Inputs em inputs/ (T1/T2/T3). Não toca src/tcf nem EXP-015.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import typed_codec as T                               # noqa: E402
from tcf import encode, SideOutputs                   # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)
CASES = ["T1-escalares-tipados", "T2-array-tipado", "T3-aninhado-misto"]


def nb(s): return len(s.encode("utf-8"))
def w(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")
def meta_of(blob): return blob.split("\n", 1)[0]


def flat_bodies(obj):
    """(nome, [bodies], letra) na ordem DFS — pra o trace por coluna."""
    return T._dfs_cols(obj)


def load(tag): return json.loads((HERE / "inputs" / f"{tag}.json").read_text(encoding="utf-8"))


def main():
    inp, tcf, rt, cost, trace = [], [], [], [], []
    for tag in CASES:
        src = load(tag)
        typed = T.obj_to_tcf(src)
        allstr = T.obj_to_tcf_allstr(src)
        back_typed = T.tcf_to_obj(typed)
        # baseline lossy: reusa o parser tipado (sem letras → tudo string) pra reverter
        back_allstr = T.tcf_to_obj(allstr)
        ok_t = back_typed == src
        ok_a = back_allstr == src

        tipos = ", ".join(f"{n}={l or 's'}" for n, _b, l in flat_bodies(src))
        inp.append(f"## {tag}\n  {json.dumps(src, ensure_ascii=False)}\n  tipos por folha: {tipos}")
        tcf.append(f"## {tag}  (typed, {nb(typed)}B)\n{typed}\n"
                   f"## {tag}  (all-string baseline lossy, {nb(allstr)}B)\n{allstr}\n")
        rt.append(f"## {tag}\n"
                  f"  TYPED     RT={'OK' if ok_t else 'MISMATCH'}  bytes={nb(typed):3d}  meta={meta_of(typed)!r}\n"
                  f"  ALL-STR   RT={'OK' if ok_a else 'MISMATCH (lossy: tipos viram string)'}  bytes={nb(allstr):3d}\n"
                  + ("" if ok_t else f"  !! TYPED in : {src}\n  !! TYPED out: {back_typed}\n")
                  + ("" if ok_a else f"     ALL-STR out: {back_allstr}\n"))
        cost.append(f"  {tag:22s} typed={nb(typed):3d}B  all-str={nb(allstr):3d}B  "
                    f"custo-tags=+{nb(typed)-nb(allstr)}B  (all-str RT={'OK' if ok_a else 'FALHA'})")

        # trace OBAT/HCC por coluna (SideOutputs)
        trace.append(f"## {tag}")
        for name, bodies, letter in flat_bodies(src):
            side = SideOutputs(); encode(bodies, side_outputs=side)
            per = (side.per_col or {})
            s = per.get(0) or (next(iter(per.values())) if per else None)
            bb = getattr(s, "body_bytes", "?") if s else "?"
            trace.append(f"  col({name}) tipo={letter or 's'} bodies={bodies} -> body_bytes={bb}")
        trace.append("")

    w("01-inputs.txt", "# INPUTS tipados (JSON)\n\n" + "\n".join(inp) + "\n")
    w("02-typed.tcf.txt", "# TCF.8H TYPED vs ALL-STRING (baseline lossy)\n\n" + "\n".join(tcf))
    w("03-obat-hcc-trace.txt", "# TRACE OBAT/HCC por coluna (SideOutputs.body_bytes)\n\n" + "\n".join(trace) + "\n")
    w("04-roundtrip.txt", "# ROUND-TRIP: typed (lossless) vs all-string (lossy)\n\n" + "\n".join(rt) + "\n")
    w("05-bytes-custo.txt",
      "# CUSTO EM BYTES da fidelidade de tipos (tags i/f/b/n) vs baseline all-string LOSSY\n\n"
      + "\n".join(cost) + "\n\n"
      "LEITURA: a baseline all-string é MENOR mas ERRADA (perde os tipos, RT FALHA). O custo das tags\n"
      "é o preço do RT-exato. Tag = 1 byte por folha divergente de string (letra colada no size).\n"
      "Custo LÍQUIDO > tags quando a folha DFS-última é tipada: ela perde a última-sem-size (paga\n"
      ":size + tag). Mitigação (1b/C5): reordenar pra deixar uma folha STRING por último.\n")

    R = ["# Ciclo 1a — fidelidade de tipos [resumo]", "",
         "| caso | typed bytes | typed RT | all-str bytes | all-str RT | custo-tags |",
         "|---|---|---|---|---|---|"]
    for tag in CASES:
        src = load(tag)
        typed, allstr = T.obj_to_tcf(src), T.obj_to_tcf_allstr(src)
        okt = T.tcf_to_obj(typed) == src
        oka = T.tcf_to_obj(allstr) == src
        R.append(f"| {tag} | {nb(typed)}B | {'OK' if okt else 'FAIL'} | {nb(allstr)}B | "
                 f"{'OK' if oka else 'FALHA (lossy)'} | +{nb(typed)-nb(allstr)}B |")
    R += ["", "CONCLUSÃO: string=default (sem tag); tipo divergente leva 1 letra (i/f/b/n) colada no size — tag=1B.",
          "Typed = RT-exato; all-string = menor mas LOSSY (tipos viram string). O custo LÍQUIDO varia:",
          "além da tag (1B/folha-tipada), se a folha DFS-ÚLTIMA for tipada ela PERDE a última-sem-size",
          "(paga :size + tag de volta) — daí T2 +5B, T3 +8B > só as tags. Isso liga com o reorder (C5):",
          "preferir uma folha STRING por último minimiza o custo dos tipos (SAVING(L) agora inclui a tag).",
          "Próximo (1b): escalar formas (array vazio, null em array, chave ausente, aninhamento fundo)."]
    w("00-resumo.txt", "\n".join(R) + "\n")

    print("artifacts em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:24s} {p.stat().st_size:6d} B")
    print("\n" + "\n".join(R))


if __name__ == "__main__":
    main()
