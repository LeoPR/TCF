"""Valida decoder TCF v0.5 mínimo (SRDM) contra exemplos manuais.

Roda 5 casos de teste cobrindo:
  - Coluna simples não-numérica (bare)
  - Coluna numérica inteira (marked auto-detectada)
  - Run literal (N*<valor>)
  - Run ref (N*<idx>)
  - Auto-discriminação (flag M)

Saida: console com OK / FAIL por caso.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from tcf.v05 import decode


def assert_eq(label: str, got, expected) -> bool:
    if got == expected:
        print(f"  [OK]   {label}")
        return True
    else:
        print(f"  [FAIL] {label}")
        print(f"         got      = {got}")
        print(f"         expected = {expected}")
        return False


def main() -> None:
    print("=" * 78)
    print("Validacao decoder TCF v0.5 minimo (SRDM)")
    print("=" * 78)
    n_pass = 0
    n_total = 0

    # ------------------------------------------------------------------
    # T1 — Coluna simples não-numérica, sem refs
    # ------------------------------------------------------------------
    print("\n[T1] Coluna não-numérica simples, só literais")
    text = """#TCF.5 SRDM
nome:
Ana
Beto
Carlos
"""
    decoded = decode(text)
    n_total += 1
    if assert_eq("nome", decoded.get("nome"), ["Ana", "Beto", "Carlos"]):
        n_pass += 1

    # ------------------------------------------------------------------
    # T2 — Coluna não-numérica com refs (bare auto-detectado)
    # ------------------------------------------------------------------
    print("\n[T2] Coluna não-numérica com refs (bare)")
    text = """#TCF.5 SRDM
nome:
Ana
Beto
Carlos
2
1
"""
    decoded = decode(text)
    n_total += 1
    if assert_eq("nome", decoded.get("nome"),
                  ["Ana", "Beto", "Carlos", "Beto", "Ana"]):
        n_pass += 1

    # ------------------------------------------------------------------
    # T3 — RLE literal e RLE ref na mesma coluna
    # ------------------------------------------------------------------
    print("\n[T3] RLE literal + RLE ref")
    text = """#TCF.5 SRDM
produto:
2*Apontador
5*Caderno
2*1
"""
    decoded = decode(text)
    n_total += 1
    expected = ["Apontador", "Apontador", "Caderno", "Caderno", "Caderno",
                 "Caderno", "Caderno", "Apontador", "Apontador"]
    if assert_eq("produto", decoded.get("produto"), expected):
        n_pass += 1

    # ------------------------------------------------------------------
    # T4 — Coluna inteira (marked auto-detectada, refs com `:`)
    # ------------------------------------------------------------------
    print("\n[T4] Coluna inteira pura, refs marcadas")
    text = """#TCF.5 SRDM
qty:
5
10
3
:1
:2
"""
    decoded = decode(text)
    n_total += 1
    if assert_eq("qty", decoded.get("qty"), ["5", "10", "3", "5", "10"]):
        n_pass += 1

    # ------------------------------------------------------------------
    # T5 — Múltiplas colunas + sort header + RLE em ambas
    # ------------------------------------------------------------------
    print("\n[T5] Multi-coluna com sort + RLE")
    text = """#TCF.5 SRDM
# sort: nome
# discrim: nome=bare, qty=marked
nome:
Ana
3*Beto
Carlos
qty:
2*100
3*200
50
"""
    decoded = decode(text)
    n_total += 1
    ok1 = assert_eq("nome", decoded.get("nome"),
                     ["Ana", "Beto", "Beto", "Beto", "Carlos"])
    ok2 = assert_eq("qty", decoded.get("qty"),
                     ["100", "100", "200", "200", "200", "50"])
    if ok1 and ok2:
        n_pass += 1

    # ------------------------------------------------------------------
    # T6 — Exemplo do `02-aplicado.md` (mesa rle-dict-unificado)
    # Coluna nome com 30 posições e mistura literal/ref/RLE
    # ------------------------------------------------------------------
    print("\n[T6] Exemplo da mesa rle-dict-unificado (coluna nome)")
    text = """#TCF.5 SRDM
nome:
Beto
Helena
Carlos
Eduardo
Ana
2
Gabriel
2*Diana
2*1
6
4
5
Fernanda
3
2
4
2
3
6
5
8
1
7
5
8
3
7
4
"""
    decoded = decode(text)
    n_total += 1
    expected_nome = [
        "Beto", "Helena", "Carlos", "Eduardo", "Ana",
        "Helena",        # ref 2
        "Gabriel",
        "Diana", "Diana",  # 2*Diana
        "Beto", "Beto",   # 2*1
        "Gabriel",       # ref 6
        "Eduardo",       # ref 4
        "Ana",           # ref 5
        "Fernanda",
        "Carlos",        # ref 3
        "Helena",        # ref 2
        "Eduardo",       # ref 4
        "Helena",        # ref 2
        "Carlos",        # ref 3
        "Gabriel",       # ref 6
        "Ana",           # ref 5
        "Fernanda",      # ref 8
        "Beto",          # ref 1
        "Diana",         # ref 7
        "Ana",           # ref 5
        "Fernanda",      # ref 8
        "Carlos",        # ref 3
        "Diana",         # ref 7
        "Eduardo",       # ref 4
    ]
    if assert_eq("nome (30 posicoes)", decoded.get("nome"), expected_nome):
        n_pass += 1

    # ---- Sumario ----
    print("\n" + "=" * 78)
    print(f"Resultado: {n_pass}/{n_total} testes passaram")
    print("=" * 78)
    if n_pass == n_total:
        print("\n  [SUCCESS] Decoder v0.5 mínimo (SRDM) está funcional.")
    else:
        print(f"\n  [FAIL] {n_total - n_pass} testes falharam.")
        sys.exit(1)


if __name__ == "__main__":
    main()
