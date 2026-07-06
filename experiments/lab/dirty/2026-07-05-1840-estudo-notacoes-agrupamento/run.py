"""run.py — ESTUDO das notações de agrupamento. Para cada fixture: monta a árvore, codifica o
AGRUPAMENTO (topologia+nomes) em cada notação, faz parse-de-volta (RT da topologia), mede bytes, e
escreve a comparação. FOCO: qual forma de agrupar é mais minimalista — não os colchetes em si.
Auto-contido: `notationlib.py` (não usa nem `tcf`, é só a camada de header). `python run.py` regenera.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import notationlib as N            # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)


def write(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


def compare(tag, doc):
    forest = N.build_tree(doc)
    lines = [f"# {tag} — árvore: {json.dumps(doc, ensure_ascii=False)[:90]}...", "",
             "notação                     | bytes | RT topologia | string", "-" * 110]
    rows = []
    for label, (enc, parse) in N.NOTATIONS.items():
        s = enc(forest)
        rt = parse(s) == forest
        rows.append((label, len(s.encode()), rt, s))
        lines.append(f"{label:27s} | {len(s.encode()):5d} | {'OK' if rt else 'FALHA':11s} | {s}")
    lines += ["", "leitura:",
              " - S e A são a MESMA família (delimitador casado): ~mesmos bytes, 2 marcas por grupo interno.",
              " - C (contagem) marca SÓ nós internos (folhas ficam nuas) → menos marcas em árvore com muitas folhas.",
              " - D (profundidade) marca TODO nó (inclusive folhas) → 1 número por coluna.",
              "",
              "teoria: lista linear de irmãos + separador NÃO reconstrói árvore; precisa de UM portador de",
              "forma — {delimitador casado} OU {contagem/aridade} OU {profundidade}. 'Símbolo entre elementos'",
              "só resolve se o símbolo for um desses (ex.: > < = delimitador). array-vs-objeto continua",
              "deduzido do nº de linhas (peça 5), ortogonal à notação."]
    return "\n".join(lines) + "\n", rows


def main():
    summary = ["# ESTUDO — notações de agrupamento (qual a mais minimalista) [probatório]", ""]
    for tag, fn in [("S4", "S4-pessoa-telefones.json"), ("S6", "S6-pessoa-endereco-geo.json")]:
        doc = json.loads((HERE / "inputs" / fn).read_text(encoding="utf-8"))
        txt, rows = compare(tag, doc)
        write(f"01-comparacao-{tag}.txt", txt)
        summary.append(f"## {tag}")
        for label, b, rt, s in rows:
            summary.append(f"  {label:27s} {b:4d}B  RT={'OK' if rt else 'FALHA'}   {s}")
        summary.append("")
    write("00-resumo.txt", "\n".join(summary) + "\n")

    print("Artefatos em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:24s} {p.stat().st_size:6d} B")
    print()
    print((ART / "00-resumo.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
