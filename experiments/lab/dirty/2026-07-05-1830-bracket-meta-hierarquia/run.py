"""run.py — modelo P5 'colchetes no meta'. Estágios: ENTRADA → TRADUÇÃO (colunas em ordem + o meta em
colchetes) → TCF-P5 (1 multi-col; hierarquia nos colchetes; M/N deduzidos) → DECODE (array/objeto
deduzido do nº de linhas). Auto-contido: `bracketlib.py` + `tcf`. NÃO toca src. `python run.py` regenera.
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
import bracketlib as B              # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)


def write(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


def traducao_txt(doc):
    cols = B.columns(doc)
    out = ["# TRADUÇÃO — colunas em ORDEM (DFS) + o meta em COLCHETES (a hierarquia vai no próprio meta)", ""]
    for name, vals in cols:
        card = "array (>1 linha)" if len(vals) > 1 else "escalar/objeto (1 linha)"
        out.append(f"  {name:10s} {len(vals)} valor(es)  [{card}]  {vals}")
    out += ["", "dedução: M = várias colunas; N = colchetes aninhados; array vs objeto = nº de linhas dos filhos."]
    return "\n".join(out) + "\n"


def process(tag, fname):
    src = json.loads((HERE / "inputs" / fname).read_text(encoding="utf-8"))
    write(f"01-entrada-{tag}.json", json.dumps(src, ensure_ascii=False, indent=2) + "\n")
    write(f"02-traducao-{tag}.txt", traducao_txt(src))
    p5 = B.encode_p5(src, encode)
    write(f"03-tcf-p5-{tag}.tcf.txt", p5 if p5.endswith("\n") else p5 + "\n")
    recon = B.decode_p5(p5, decode)
    ok = recon == src
    D = [f"# DECODE {tag} — parse dos colchetes → split por bytes → colunas → dedução array/objeto → JSON", "",
         f"reconstruído == entrada ? {'OK' if ok else 'MISMATCH'}", "",
         "--- o TCF-P5 (colchetes no meta) ---", p5,
         "--- JSON reconstruído ---", json.dumps(recon, ensure_ascii=False, indent=2)]
    if not ok:
        D += ["", "!! entrada:", json.dumps(src, ensure_ascii=False, indent=2)]
    write(f"04-decode-roundtrip-{tag}.txt", "\n".join(D) + "\n")
    return tag, ok, p5


def main():
    results = [process("S4", "S4-pessoa-telefones.json"),
               process("S6", "S6-pessoa-endereco-geo.json")]
    print("Artefatos em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:32s} {p.stat().st_size:6d} B")
    print()
    for tag, ok, _ in results:
        print(f"DECODE {tag}: {'reconstrói o JSON (OK)' if ok else '!! MISMATCH'}")
    print("\n--- 03-tcf-p5-S4.tcf.txt ---"); print(results[0][2])
    print("--- 03-tcf-p5-S6.tcf.txt ---"); print(results[1][2])


if __name__ == "__main__":
    main()
