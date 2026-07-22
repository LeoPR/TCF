"""run.py — modelo "multi-col + marcador N" (a via mais simples). Estágios: ENTRADA → TRADUÇÃO (colunas
em ordem + a linha #H) → TCF-MN (1 multi-col com flag N + #H) → DECODE. Auto-contido: `mnlib.py` + `tcf`.
NÃO toca src. `python run.py` regenera tudo.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
from tcf import encode, decode      # noqa: E402
import mnlib as M                   # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)


def write(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


def traducao_txt(doc):
    h = M.hspec(doc)
    cols = M.columns(doc)
    out = ["# TRADUÇÃO — colunas em ORDEM (DFS) + a linha de hierarquia que as reagrupa", "",
           "#H  " + h, "",
           "colunas (na ordem em que entram no corpo multi-col):"]
    for name, vals in cols:
        out.append(f"  {name:12s} {len(vals)} valor(es)   {vals}")
    out += ["", "leitura: colunas de 1 valor = escalar de nível (raiz/objeto); coluna de N = array.",
            "         a #H diz quem é raiz, objeto{...} e array[...]; agrupa as colunas pela ordem."]
    return "\n".join(out) + "\n"


def process(tag, fname):
    src = json.loads((HERE / "inputs" / fname).read_text(encoding="utf-8"))
    write(f"01-entrada-{tag}.json", json.dumps(src, ensure_ascii=False, indent=2) + "\n")
    write(f"02-traducao-{tag}.txt", traducao_txt(src))
    mn = M.encode_mn(src, encode)
    write(f"03-tcf-mn-{tag}.tcf.txt", mn if mn.endswith("\n") else mn + "\n")
    recon = M.decode_mn(mn, decode)
    ok = recon == src
    D = [f"# DECODE {tag} — split por bytes → colunas → reagrupa pela #H → JSON", "",
         f"reconstruído == entrada ? {'OK' if ok else 'MISMATCH'}", "",
         "--- o TCF-MN (o que foi decodado) ---", mn,
         "--- JSON reconstruído ---", json.dumps(recon, ensure_ascii=False, indent=2)]
    if not ok:
        D += ["", "!! entrada:", json.dumps(src, ensure_ascii=False, indent=2)]
    write(f"04-decode-roundtrip-{tag}.txt", "\n".join(D) + "\n")
    return tag, ok, mn


def main():
    results = [process("S4", "S4-pessoa-telefones.json"),
               process("S6", "S6-pessoa-endereco-geo.json")]
    print("Artefatos em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:32s} {p.stat().st_size:6d} B")
    print()
    for tag, ok, _ in results:
        print(f"DECODE {tag}: {'reconstrói o JSON (OK)' if ok else '!! MISMATCH'}")
    print("\n--- 03-tcf-mn-S4.tcf.txt (o modelo, mínimo) ---")
    print(results[0][2])
    print("--- 03-tcf-mn-S6.tcf.txt (generaliza p/ árvore) ---")
    print(results[1][2])


if __name__ == "__main__":
    main()
