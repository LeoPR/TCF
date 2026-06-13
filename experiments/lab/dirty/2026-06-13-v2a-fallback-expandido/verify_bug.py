"""Verifica o bug de RT via API PUBLICA + mapeia a fronteira.

Standalone (NAO depende de Z:). Reproducer derivado de receita nome_fantasia.
Contrato violado: decode(encode(x)) == x.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode  # noqa: E402


def check(label, vals):
    text = encode(vals)
    back = decode(text)
    ok = back == vals
    flag = "OK  " if ok else "FAIL"
    print(f"[{flag}] {label}")
    if not ok:
        for i, (a, b) in enumerate(zip(vals, back)):
            if a != b:
                print(f"        linha {i}: in={a!r}  out={b!r}")
        if len(vals) != len(back):
            print(f"        len in={len(vals)} out={len(back)}")
    return ok


CASES = [
    # reproducer real (receita)
    ("repro real", ['', 'RESTAURANTE AR DE MINAS', 'RESIDENCIAL NOVA BATALHA']),
    # sem o empty -> deve passar (empty e' load-bearing)
    ("sem empty inicial", ['RESTAURANTE AR DE MINAS', 'RESIDENCIAL NOVA BATALHA']),
    # empty no meio
    ("empty no meio", ['RESTAURANTE AR DE MINAS', '', 'RESIDENCIAL NOVA BATALHA']),
    # empty no fim
    ("empty no fim", ['RESTAURANTE AR DE MINAS', 'RESIDENCIAL NOVA BATALHA', '']),
    # synthetic minimo: empty + 2 strings com prefixo compartilhado
    ("synth AAAB/AAAC", ['', 'AAAB', 'AAAC']),
    ("synth prefixo longo", ['', 'PREFIXOxxx', 'PREFIXOyyy']),
    # 2 emptys
    ("dois emptys", ['', '', 'RESTAURANTE AR DE MINAS', 'RESIDENCIAL NOVA BATALHA']),
    # sem prefixo compartilhado (com empty)
    ("empty + sem prefixo", ['', 'ABCDEF', 'GHIJKL']),
    # so' o par que compartilha, empty antes
    ("empty + par curto", ['', 'RES', 'RESID']),
]


def main():
    print("=== fronteira do bug (API publica encode/decode) ===\n")
    n_fail = 0
    for label, vals in CASES:
        if not check(label, vals):
            n_fail += 1
    print(f"\n{n_fail}/{len(CASES)} casos FALHAM o contrato decode(encode(x))==x")


if __name__ == "__main__":
    main()
