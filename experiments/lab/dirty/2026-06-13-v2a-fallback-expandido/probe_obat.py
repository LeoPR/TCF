"""Probe: como OBAT (processar) tokeniza '' em varias posicoes + pieces."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf.core.online import processar  # noqa: E402
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402


def dump(label, unicas):
    tokens, _log = processar(unicas, min_len=3)
    print(f"\n== {label} ==")
    print(f"unicas: {unicas}")
    for i, (u, toks) in enumerate(zip(unicas, tokens)):
        print(f"  [{i}] {u!r} -> {toks}")
    syn = M8AVirtualRefsSyntax()
    pieces_per_line, line_meta, atom_count = syn._tokenize_pieces(
        unicas, unicas, tokens)
    print(f"atom_count={atom_count}")
    for i, (pp, lm) in enumerate(zip(pieces_per_line, line_meta)):
        print(f"  line[{i}] meta={lm} pieces={pp}")


def main():
    dump("'' primeiro", ['', 'AAAB', 'AAAC'])
    dump("'' segundo", ['RED', '', 'HEART OF WICKER LARGE', 'HEART OF WICKER SMALL'])
    dump("'' sozinho", [''])
    dump("'' depois de 1", ['X', ''])
    dump("só '' no fim", ['AAAB', 'AAAC', ''])


if __name__ == "__main__":
    main()
