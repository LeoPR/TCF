"""Teste de hipotese (proporcao) — header por LINHAS vs por BYTES. Lab read-only, SEM tocar core.

Pergunta do owner: trocar o byte-size do header por row-count (linhas) economiza? Em que
PROPORCAO das situacoes vale, estatisticamente? Modelo parametrico (nao precisa do encoder):
varre forma de tabela (C colunas x N linhas x b bytes/valor comprimido) e mede a economia de
header como % do blob, pra 3 opcoes:

  A) byte-size DECIMAL no header (ATUAL). Acesso O(1) a coluna + decode paralelo.
  B) byte-size BASE-94 no header (o "hexa" do owner, melhor). MANTEM O(1) + paralelo; so' encurta o numero.
  C) ROW-COUNT (linhas), 1 numero compartilhado + restaurar \\n separador/coluna (modo "solid block").
     PERDE O(1) (vira scan), decode paralelo e group por slice.

Saida: onde cada opcao economiza >= 1% e >= 5% do blob (a "noção de proporção").
"""
from __future__ import annotations


def d10(x: int) -> int:
    return len(str(max(1, int(x))))


def d94(x: int) -> int:
    x = max(1, int(x)); n, cap = 1, 94
    while x >= cap:
        n += 1; cap *= 94
    return n


def analisa(C: int, N: int, b: float):
    size = N * b                       # bytes do corpo de uma coluna (aprox)
    blob = C * N * b                   # corpo total (header e' fracao minima)
    hdr_A = (C - 1) * d10(size)        # byte-sizes decimais (ultima omitida, min_header)
    hdr_B = (C - 1) * d94(size)        # byte-sizes base-94
    hdr_C = d10(N) + C                 # row-count 1x + C separadores \n restaurados
    saveB = hdr_A - hdr_B              # vs atual; SEM perder nada
    saveC = hdr_A - hdr_C             # vs atual; PERDE O(1)+paralelo+groups
    return blob, 100 * saveB / blob, 100 * saveC / blob, saveB, saveC


def main():
    print("# Header por LINHAS vs BYTES — modelo de proporcao\n")
    print("b = bytes/valor comprimido. blob ~ C*N*b. Economia como % do blob.\n")
    Cs = [2, 5, 20, 50]
    Ns = [5, 20, 100, 1000, 100_000]
    bs = [1.5, 4, 12]                  # 1.5=muito comprimido(low-card), 4=tipico, 12=texto
    hdr = f"{'C':>3} {'N':>7} {'b':>5} {'blob~':>9} | {'B(base94) %':>12} {'C(linhas) %':>12}  {'C bytes':>8}"
    print(hdr); print("-" * len(hdr))
    n_ge1_C = n_ge5_C = total = 0
    n_ge1_B = 0
    for C in Cs:
        for N in Ns:
            for b in bs:
                blob, pB, pC, sB, sC = analisa(C, N, b)
                total += 1
                if pC >= 1: n_ge1_C += 1
                if pC >= 5: n_ge5_C += 1
                if pB >= 1: n_ge1_B += 1
                flag = "  <-- C>=1%" if pC >= 1 else ""
                print(f"{C:>3} {N:>7} {b:>5} {int(blob):>9} | {pB:>11.2f}% {pC:>11.2f}% {int(sC):>8}{flag}")
    print("-" * len(hdr))
    print(f"\nPROPORCAO (de {total} formas testadas):")
    print(f"  C (row-count) economiza >= 1% do blob em {n_ge1_C}/{total} casos; >= 5% em {n_ge5_C}/{total}")
    print(f"  B (base-94 size) economiza >= 1% do blob em {n_ge1_B}/{total} casos (SEM perder O(1)/paralelo)")
    print("\nLeitura: C so' passa de 1% em tabela MINUSCULA (N pequeno) + MUITAS colunas — e ai")
    print("a economia ABSOLUTA e' de poucas/dezenas de bytes. Em tabela com volume real (N grande),")
    print("ambas << 1%. B captura parte da economia SEM perder acesso O(1)/paralelo/groups.")


if __name__ == "__main__":
    main()
