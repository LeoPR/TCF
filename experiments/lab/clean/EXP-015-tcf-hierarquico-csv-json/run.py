"""run.py — EXP-015: protótipo TCF hierárquico que lê CSV e JSON e reverte pros dois.

Fluxo inspecionável (peça a peça, amostras minúsculas primeiro):
  JSON:  input → obj_to_tcf (preserva a árvore) → tcf_to_obj  [RT exato]
  CSV :  input → cols_to_tcf_flat (multi-col, plano) → tcf_flat_to_cols → csv  [RT plano]
  CSV+dedução: detecta 1:N → hierarquiza (implícito) → obj_to_tcf → re-achata  [RT plano]; compara bytes.

Testa a hipótese do owner: JSON PRECISA preservar a hierarquia (explícito); CSV NÃO precisa (a hierarquia
é opt-in, só p/ compressão) — e mede se compensa. `python run.py` regenera outputs/.
Ponteiro dataset sintético: `datasets/synthetic/` (D1-D17) — aqui amostras minúsculas p/ consistência.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import codec as C          # noqa: E402

OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)


def nb(s): return len(s.encode("utf-8"))
def write(name, text): (OUT / name).write_text(text, encoding="utf-8", newline="\n")


def json_path(tag, fname):
    src = json.loads((HERE / "inputs" / fname).read_text(encoding="utf-8"))
    blob = C.obj_to_tcf(src)
    back = C.tcf_to_obj(blob)
    ok = back == src
    write(f"01-json-{tag}.tcf.txt", blob)
    write(f"01-json-{tag}-decode.json", json.dumps(back, ensure_ascii=False, indent=2) + "\n")
    return tag, nb(blob), ok, blob


def csv_path(tag, fname):
    text = (HERE / "inputs" / fname).read_text(encoding="utf-8")
    cols, header = C.csv_to_cols(text)
    blob = C.cols_to_tcf_flat(cols)
    back_cols = C.tcf_flat_to_cols(blob)
    back_csv = C.cols_to_csv(back_cols, header)
    ok = back_csv.strip() == text.strip()
    write(f"02-csv-{tag}-flat.tcf.txt", blob)
    write(f"02-csv-{tag}-decode.csv", back_csv)
    return tag, nb(blob), ok, cols, header


def csv_deduce(tag, cols, parent, child):
    card = C.classify(cols[parent], cols[child])
    flat = C.cols_to_tcf_flat(cols)
    parent_alone = C.encode(cols[parent])          # o pai sozinho no multi-col → RLE (colapsado)
    # tentar hierarquizar + RT completo → bate no limite (array-dentro-de-array / N raízes)
    try:
        hier = C.obj_to_tcf(C.deduce_to_obj(cols, parent, child))
        reflat = C.obj_to_flat_cols(C.tcf_to_obj(hier), parent, child)
        rt = reflat == {parent: cols[parent], child: cols[child]}
        boundary = f"encodou {nb(hier)}B mas RT={'OK' if rt else 'FALHA (array-em-array corrompe)'}"
    except Exception as e:
        boundary = f"LINK POSICIONAL necessário (array-em-array / N raízes) — v0 NÃO faz [{type(e).__name__}]"
    L = [f"# CSV + DEDUÇÃO — {tag}: {parent}→{child} classificado {card}", "",
         f"EXPLÍCITO (tabela plana, multi-col): {nb(flat):3d}B",
         f"  {flat!r}", "",
         f"o pai '{parent}' SOZINHO já vira RLE no multi-col (o 'store once' de graça):",
         f"  {parent_alone!r}", "",
         f"IMPLÍCITO (hierarquizar a 1:N): {boundary}",
         "", "LEITURA: no CSV o RT-alvo é a tabela PLANA. Hierarquizar uma 1:N multi-pai exige link",
         "posicional (peça 10) — que o v0 não faz — E não compensaria em bytes (RLE↔fk duais, peça 1/8:",
         "o RLE do multi-col já colapsa o pai, o 'store once' que a hierarquia daria). → no CSV a",
         "hierarquia é DISPENSÁVEL. No JSON, ao contrário, a árvore É o RT-alvo → tem de ser preservada."]
    write("03-csv-deducao.txt", "\n".join(L) + "\n")
    return card, nb(flat), nb(parent_alone), boundary


def main():
    j = [json_path("S4", "S4-pessoa-telefones.json"),
         json_path("S6", "S6-pessoa-endereco-geo.json")]
    c = csv_path("C1", "C1-pessoa-telefone-flat.csv")
    ded = csv_deduce("C1", c[3], "pessoa", "telefone")

    R = ["# EXP-015 — TCF hierárquico CSV↔JSON (protótipo v0) [report]", "",
         "## JSON (preserva a árvore — RT exato)"]
    for tag, b, ok, _ in j:
        R.append(f"  {tag}: {b:3d}B  RT-JSON={'OK' if ok else 'FAIL'}")
    R += ["", "## CSV (plano — RT exato da tabela)",
          f"  {c[0]}: {c[1]:3d}B  RT-CSV={'OK' if c[2] else 'FAIL'}", "",
          "## CSV + dedução (explícito-plano vs implícito-hierárquico)",
          f"  classe={ded[0]}  plano={ded[1]}B  pai-sozinho(RLE)={ded[2]}B",
          f"  hierarquizar: {ded[3]}", "",
          "## conclusão (v0)",
          "- **JSON**: a árvore É o RT-alvo → hierarquia EXPLÍCITA (preservada). RT exato nos 2 casos.",
          "- **CSV**: o RT-alvo é a tabela plana → hierarquia DISPENSÁVEL. Deduzir a 1:N multi-pai precisa",
          "  de link posicional (peça 10) E não compensa bytes (RLE já colapsa o pai). Confirma 'no CSV",
          "  não precisa preservar tanto'.",
          "- Consistência OK em amostras minúsculas → escalar (ponteiro `datasets/synthetic/`) é o próximo.",
          "",
          "Ponteiro dataset sintético: datasets/synthetic/ (D1-D17). Aqui: S4/S6 (JSON) + C1 (CSV) minúsculos."]
    write("00-resumo.txt", "\n".join(R) + "\n")

    print("outputs em", OUT)
    for p in sorted(OUT.iterdir()):
        print(f"  {p.name:26s} {p.stat().st_size:6d} B")
    print("\n" + "\n".join(R))


if __name__ == "__main__":
    main()
