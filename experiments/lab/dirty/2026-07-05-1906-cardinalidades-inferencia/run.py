"""run.py — ESTUDO: deduzir cardinalidade (1x1/1xN/Nx1/NxN) dos dados e mapear pra mecânica do TCF.
4 exemplos planos (como um CSV): classifica pela contagem de distintos (FD), mostra a fatoração
(normalização) e a intuição de bytes. Auto-contido: `cardlib.py` (nem usa `tcf`). `python run.py` regenera.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cardlib as C          # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)


def write(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


# 4 exemplos (tabelas planas de 2 colunas A,B) — um por cardinalidade
EXEMPLOS = {
    "1x1-cpf-nome": (
        ("cpf", ["111", "222", "333"]),
        ("nome", ["Ana", "Bob", "Cida"])),
    "1xN-pessoa-telefone": (
        ("pessoa", ["leonardo", "leonardo", "maria"]),
        ("telefone", ["(41) 99999-9999", "(41) 99994-9999", "(11) 98888-8888"])),
    "Nx1-produto-categoria": (
        ("produto", ["P1", "P2", "P3", "P4"]),
        ("categoria", ["eletronico", "eletronico", "alimento", "alimento"])),
    "NxN-pessoa-curso": (
        ("pessoa", ["leonardo", "leonardo", "maria"]),
        ("curso", ["math", "physics", "math"])),
}


def mapa_tcf(card):
    return {
        "1:1": "TCF nativo (colunas 1x1, retangular). Nada a fatorar.",
        "1:N": "hierarquia: pai guardado 1x + coluna-filho ligada (peça 3/4/5). O '*N|' do plano some.",
        "N:1": "@dict low-card: valor guardado 1x + índice por linha (o TCF JÁ faz isso).",
        "N:N": "tabela-ponte: dict(A) + dict(B) + lista de pares (índices).",
    }[card]


def analisar(tag, colA, colB):
    (na, a), (nb, b) = colA, colB
    r = C.classify(a, b)
    L = [f"# {tag}", "",
         f"colunas: A={na}  B={nb}   ({r['R']} linhas)",
         f"tabela plana:", *[f"    {a[i]:>10s} | {b[i]}" for i in range(len(a))], "",
         f"distintos: |{na}|={r['nA']}  |{nb}|={r['nB']}  |pares|={r['nAB']}",
         f"FD: {na}→{nb}? {r['A->B']}   {nb}→{na}? {r['B->A']}",
         f"=> CARDINALIDADE {na}:{nb} = **{r['card']}**   ({r['leitura']})", "",
         f"mapa TCF: {mapa_tcf(r['card'])}", ""]
    if r["card"] == "1:N":
        pais, groups = C.factor_1n(a, b)
        bi = C.byte_intuition(a, b, r["card"])
        L += ["fatoração (normalização) — o pai vira 'elemento' 1x:",
              f"    pais distintos ({len(pais)}): {pais}",
              *[f"    {p} → {groups[p]}" for p in pais],
              f"    bytes A: plano(repetido)={bi['A_plano_chars']}  1x={bi['A_1x_chars']}  economia≈{bi['economia_A_chars']} chars",
              "    → declarar 1:N no header = trocar o RLE '*N|pai' por 'pai 1x + link' (dual da peça 1)."]
    elif r["card"] == "N:1":
        vals, idx = C.dict_n1(a, b)
        L += ["fatoração — B é dicionário low-card:",
              f"    dicionário B ({len(vals)}): {vals}",
              f"    índice por linha: {idx}",
              "    → é o @dict que o TCF já emite; a cardinalidade N:1 EXPLICA o @dict."]
    elif r["card"] == "N:N":
        va, vb, pairs = C.bridge_nn(a, b)
        L += ["fatoração — tabela-ponte (junction):",
              f"    dict A ({len(va)}): {va}",
              f"    dict B ({len(vb)}): {vb}",
              f"    pares (índices): {pairs}",
              "    → NxN não vira hierarquia simples; precisa da ponte (2 dicts + pares)."]
    else:
        L += ["1:1 é o caso natural do TCF; as duas colunas seguem lado a lado."]
    return "\n".join(L) + "\n", r


def main():
    resumo = ["# ESTUDO — inferência de cardinalidade (1x1/1xN/Nx1/NxN) → mecânica TCF [probatório]", "",
              "Deduz a cardinalidade de uma tabela PLANA (como um CSV) pela contagem de distintos (FD).", "",
              "| exemplo | A:B | dedução | mecânica TCF |", "|---|---|---|---|"]
    for tag, (colA, colB) in EXEMPLOS.items():
        txt, r = analisar(tag, colA, colB)
        write(f"01-{tag}.txt", txt)
        resumo.append(f"| {tag} | **{r['card']}** | |A|={r['nA']} |B|={r['nB']} |AB|={r['nAB']} | {mapa_tcf(r['card']).split(':')[0].split('(')[0].strip()} |")
    resumo += ["", "PRINCÍPIO: a cardinalidade é uma CAMADA DECLARATIVA (independe do encoding, como OBAT/HCC).",
               "1:1 nativo · 1:N → hierarquia (pai 1x + link, o dual do RLE) · N:1 → @dict · N:N → ponte.",
               "Deduz do CSV (contagem/FD) OU vem definida do JSON (a árvore já força a hierarquia)."]
    write("00-resumo.txt", "\n".join(resumo) + "\n")

    print("Artefatos em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:28s} {p.stat().st_size:6d} B")
    print("\n" + (ART / "00-resumo.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
