"""run.py — a linguagem semântica do schema TCF.8 (cardinalidade/hierarquia): EXPLÍCITA → dedução → MÍNIMA.
Estágios: ENTRADA → HEADER EXPLÍCITO (todos os itens) → DEDUÇÃO (o que sai) → HEADER MÍNIMO (= colchete P5)
→ DECODE (o mínimo reconstrói o JSON — nada perdido). Auto-contido: `schemalib.py` + `tcf`. NÃO toca src.
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
import schemalib as S               # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)


def nb(s): return len(s.encode("utf-8"))
def write(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


def process(tag, fname):
    src = json.loads((HERE / "inputs" / fname).read_text(encoding="utf-8"))
    cols = S.columns(src)
    bodies = [encode(vals) for _n, vals in cols]
    sizes = [nb(b) for b in bodies]

    exp_h = S.explicit_header(src)
    min_h = S.minimal_header(src, sizes)
    min_blob = min_h + "".join(bodies)

    recon = S.decode_minimal(min_blob, decode)
    ok = recon == src

    write(f"01-header-explicito-{tag}.txt",
          "# HEADER EXPLÍCITO — todos os itens da linguagem semântica (cardinalidade + hierarquia)\n\n" + exp_h)
    write(f"02-header-minimo-{tag}.tcf.txt",
          "# HEADER MÍNIMO (dedução aplicada) = o colchete da P5, + bodies\n\n" + min_blob)
    D = [f"# DECODE {tag} — o MÍNIMO reconstrói o JSON (nada perdido pela dedução)", "",
         f"reconstruído == entrada ? {'OK' if ok else 'MISMATCH'}", "",
         json.dumps(recon, ensure_ascii=False, indent=2)]
    if not ok:
        D += ["", "!! entrada:", json.dumps(src, ensure_ascii=False, indent=2)]
    write(f"03-decode-rt-{tag}.txt", "\n".join(D) + "\n")
    return tag, nb(exp_h), nb(min_h), ok


def main():
    results = [process("S4", "S4-pessoa-telefones.json"),
               process("S6", "S6-pessoa-endereco-geo.json")]

    L = ["# DEDUÇÃO — o que sai da linguagem explícita (implícito) e o que é IRREDUTÍVEL", "",
         f"{'item':34} {'deduzível?':>10}  de quê", "-" * 90]
    for item, ded, why in S.DEDUCTION:
        L.append(f"{item:34} {ded:>10}  {why}")
    L += ["", "## header (bytes): EXPLÍCITO vs MÍNIMO", ""]
    for tag, e, m, ok in results:
        L.append(f"  {tag}: explícito {e:4d}B  →  mínimo {m:3d}B  ({100.0*m/e:.0f}% do explícito)  RT={'OK' if ok else 'FAIL'}")
    L += ["", "LEITURA: a linguagem completa (explícita) tem TODOS os itens; a dedução tira flags(M/N),",
          "kind, cardinalidade, rows, tipo-se-uniforme → a forma MÍNIMA CONVERGE pro colchete da P5.",
          "IRREDUTÍVEL (fica explícito, salvo contrato pré-acordado): magic, arestas de hierarquia,",
          "markers, sizes. O MÍNIMO reconstrói o JSON — a dedução não perde informação (só a explicita).",
          "",
          "→ RESPOSTA: SIM, incluir a semântica de cardinalidade/hierarquia no TCF.8 é sólido; o custo",
          "  é ZERO no formato transmitido (fica implícito/deduzido) e vira EXPLÍCITO só quando o consumidor",
          "  quer o schema (ou pré-acordado = O-FMT-14). Cardinalidade e hierarquia sao a mesma camada."]
    write("00-deducao-e-bytes.txt", "\n".join(L) + "\n")

    print("Artefatos em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:38s} {p.stat().st_size:6d} B")
    print("\n" + "\n".join(L))
    print("\n--- 01-header-explicito-S6 (amostra) ---")
    print((ART / "01-header-explicito-S6.txt").read_text(encoding="utf-8"))
    print("--- 02-header-minimo-S6 ---")
    print((ART / "02-header-minimo-S6.tcf.txt").read_text(encoding="utf-8")[:300])


if __name__ == "__main__":
    main()
