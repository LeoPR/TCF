"""run.py — estuda a técnica de LIGAÇÃO pai/filho no cabeçalho de blocos TCF empilhados.

Estágios por dataset: ENTRADA → TRADUÇÃO (blocos + a árvore pai/filho) → CABEÇALHO+LINKING (a estrutura
aninhada, hint `#TCF.8 N` + adjacência lado-do-pai) → DECODE (volta ao JSON). Auto-contido: `linklib.py`
(local) + `tcf`. NÃO toca src. `python run.py` regenera tudo.
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
import linklib as L                 # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)


def write(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


def blocos_txt(doc):
    blocks, root = L.build_blocks(doc)
    out = ["# blocos (TRADUÇÃO): cada objeto/array vira 1 bloco; campo 'nome>K' = aresta pai→filho", ""]
    for b in blocks:
        parts = []
        for (k, n, x) in b["fields"]:
            parts.append(f"{n}:{x}" if k == "s" else f"{n}→b{x}")
        out.append(f"b{b['idx']} [{b['kind']}]  campos: " + ", ".join(parts))
        sc = [n for (k, n, _t) in b["fields"] if k == "s"]
        if sc:
            nrow = len(b["table"][sc[0]])
            out.append("     tabela: " + ", ".join(sc) + f"   ({nrow} linha(s))")
    return "\n".join(out) + "\n"


def process(tag, fname):
    src = json.loads((HERE / "inputs" / fname).read_text(encoding="utf-8"))
    write(f"01-entrada-{tag}.json", json.dumps(src, ensure_ascii=False, indent=2) + "\n")
    write(f"02-traducao-blocos-{tag}.txt", blocos_txt(src))
    nested = L.nest(src, encode)
    write(f"03-cabecalho-linking-{tag}.tcf.txt", nested)
    recon = L.unnest(nested, decode)
    ok = recon == src
    D = [f"# DECODE {tag} — desaninha o cabeçalho, decoda os blocos, reconstrói o JSON", "",
         f"reconstruído == entrada ? {'OK' if ok else 'MISMATCH'}", "",
         "--- estrutura aninhada (o que foi decodado) ---", nested,
         "--- JSON reconstruído (deve ser idêntico à entrada) ---",
         json.dumps(recon, ensure_ascii=False, indent=2)]
    if not ok:
        D += ["", "!! entrada:", json.dumps(src, ensure_ascii=False, indent=2)]
    write(f"04-decode-roundtrip-{tag}.txt", "\n".join(D) + "\n")
    return tag, ok, nested


def main():
    results = [process("S4", "S4-pessoa-telefones.json"),
               process("S6", "S6-pessoa-endereco-geo.json")]
    print("Artefatos em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:36s} {p.stat().st_size:6d} B")
    print()
    for tag, ok, _ in results:
        print(f"DECODE {tag}: {'reconstrói o JSON (OK)' if ok else '!! MISMATCH'}")
    print("\n--- 03-cabecalho-linking-S6.tcf.txt (a técnica de ligação pai/filho) ---")
    print(results[1][2])


if __name__ == "__main__":
    main()
