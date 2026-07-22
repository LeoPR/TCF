"""run.py — teoria de cardinalidade, DIDÁTICO + MEDIDO.
Secao 1: o trade RÁPIDO (RLE valor-inteiro) vs PLENO (OBAT/HCC) — mostra o que a redundancia INTER-ITEM
(afixo compartilhado, ex. dominio de email) custa ao caminho rapido. Secao 2: taxonomia de FORCA
(forte/fraca/quase/induzida) com medidas. Auto-contido: `theolib.py` + `tcf`. `python run.py` regenera.
"""
from __future__ import annotations
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import theolib as T          # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)


def write(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


def secao1():
    # coluna com redundancia INTER-ITEM (dominio @empresa.com compartilhado entre pessoas diferentes)
    interitem = ["leonardo@empresa.com", "leonardo@empresa.com", "mariana@empresa.com",
                 "mariana@empresa.com", "joao@empresa.com", "joao@empresa.com"]
    # coluna SEM redundancia inter-item (ids opacos, nada compartilhado)
    sem = ["a3f9c1", "a3f9c1", "7b2e88", "7b2e88", "c0d4a2", "c0d4a2"]

    L = ["# SEÇÃO 1 — RÁPIDO (RLE valor-inteiro) vs PLENO (OBAT/HCC)", "",
         "A cardinalidade 1:N (do JSON) permite um RLE rápido do pai (valor-inteiro). Mas se há",
         "redundância INTER-ITEM (afixo compartilhado entre itens), só o OBAT/HCC pleno a pega.", ""]
    for tag, col in [("COM inter-item (email, @empresa.com compartilhado)", interitem),
                     ("SEM inter-item (ids opacos)", sem)]:
        r_txt, r_b = T.rle_only(col)
        f_txt, f_b = T.full_tcf(col)
        L += [f"## {tag}",
              f"  RÁPIDO (RLE-only): {r_b:3d} B   :: {r_txt.strip()!r}",
              f"  PLENO  (OBAT/HCC): {f_b:3d} B   :: {f_txt.strip()!r}",
              f"  → pleno {'MENOR (pega o afixo inter-item)' if f_b < r_b else 'igual/maior (nada a fatorar → rápido basta)'}"
              f"  [Δ={r_b - f_b:+d} B]", ""]
    L += ["LEITURA: onde há afixo/dicionário cross-item, o PLENO ganha bytes (encode mais lento, mesmo RT).",
          "Onde não há, o RÁPIDO empata e é mais barato. É o trade velocidade↔razão do owner."]
    return "\n".join(L) + "\n"


def secao2():
    forte = ["leonardo@empresa.com"] * 4 + ["mariana@empresa.com"] * 4 + ["joao@empresa.com"] * 4
    fraca = [f"cliente_{i:03d}" for i in range(12)]
    # quase-cardinalidade: cpf→nome com 1 violação (linha suja)
    q_cpf = ["111", "111", "222", "222", "333", "333"]
    q_nome = ["Ana", "Ana", "Bob", "Bob", "Cida", "CIDA"]

    L = ["# SEÇÃO 2 — FORÇA de cardinalidade (forte / fraca / quase / induzida)", "",
         "medidas: multiplicidade (linhas/valor-pai), largura do valor, g3-error (FD aproximada).", ""]

    for tag, col in [("FORTE", forte), ("FRACA", fraca)]:
        m, w = T.multiplicity(col), T.value_width(col)
        r_b = T.rle_only(col)[1]; f_b = T.full_tcf(col)[1]
        L += [f"## {tag}  ({tag=='FORTE' and 'pai repete muito + valor largo' or 'pai quase não repete'})",
              f"  multiplicidade={m:.2f}  largura={w:.1f}  → força: {T.strength_label(m, w, 0.0)}",
              f"  fast(RLE)={r_b}B  full(TCF)={f_b}B  (a força prevê o quanto há a ganhar)", ""]

    g = T.g3(q_cpf, q_nome)
    L += ["## QUASE (FD aproximada — cpf→nome com 1 linha suja Cida/CIDA)",
          f"  classe (contagem): {T.classify(q_cpf, q_nome)}  |  g3-error(cpf→nome) = {g:.3f} ({g*len(q_cpf):.0f}/{len(q_cpf)} linhas)",
          f"  → força: {T.strength_label(T.multiplicity(q_cpf), T.value_width(q_cpf), g)}",
          "  → NÃO normalizar em silêncio (g3>0 = lossy); surfaçar como anomaly_flag (‘só detecta, nunca arruma’).", "",
          "## INDUZIDA (por definição, do JSON)",
          "  o schema do JSON já DITA a cardinalidade (1:N exato, g3=0 por construção). Não precisa deduzir;",
          "  a hierarquia vem de graça e o TCF pode explorá-la (rápido) OU rodar pleno (mais compressão).", "",
          "ACHADO-CHAVE (ortogonalidade): a FRACA acima tem full(42) << fast(144) — mas o ganho vem do AFIXO",
          "compartilhado ('cliente_'), NÃO da cardinalidade (multiplicidade=1, nada a normalizar). Ou seja:",
          "  CARDINALIDADE (multiplicidade → normalização/RLE) ≠ COMPRESSIBILIDADE (afixo/inter-item → OBAT/HCC).",
          "São EIXOS ORTOGONAIS. O trade rápido-vs-pleno é sobre QUAL redundância explorar, não sobre a força."]
    return "\n".join(L) + "\n"


def main():
    s1 = secao1(); s2 = secao2()
    write("01-rapido-vs-pleno.txt", s1)
    write("02-forca-cardinalidade.txt", s2)
    write("00-resumo.txt", s1 + "\n" + "=" * 80 + "\n\n" + s2)
    print("Artefatos em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:26s} {p.stat().st_size:6d} B")
    print("\n" + s1 + "\n" + s2)


if __name__ == "__main__":
    main()
