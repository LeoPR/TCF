"""Diagnostico do RT FAIL em receita-estab.

Separa m10_rt de fb_rt e localiza a 1a coluna/valor que diverge.
Se for M10 -> potencial bug de CORE (src/tcf) exposto por dado real.
Se for fallback -> artefato do proto (raw split).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402
from tcf.decoder import _decode_column  # noqa: E402

PATH = Path("Z:/tcf-data/external/receita-cnpj/estabelecimentos.csv")
LIMIT = 20000


def load_cols(path, limit=None):
    for enc in ("utf-8", "latin-1"):
        try:
            with path.open(encoding=enc, newline="") as f:
                r = csv.reader(f)
                header = next(r)
                cols = {h: [] for h in header}
                for i, row in enumerate(r):
                    if limit and i >= limit:
                        break
                    if len(row) != len(header):
                        continue
                    for h, v in zip(header, row):
                        cols[h].append(v)
            return cols
        except UnicodeDecodeError:
            continue
    raise RuntimeError("decode fail")


def first_diff(a, b, name):
    if a == b:
        return
    if len(a) != len(b):
        print(f"  [{name}] LEN DIFF in={len(a)} out={len(b)}")
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            print(f"  [{name}] linha {i}: in={a[i]!r}  out={b[i]!r}")
            return
    print(f"  [{name}] prefix ok, tail differs (len)")


def main():
    cols = load_cols(PATH, LIMIT)
    print(f"colunas: {list(cols.keys())}")
    print(f"rows: {len(next(iter(cols.values())))}")

    # --- M10 RT por coluna isolada ---
    print("\n=== M10 RT por coluna (decode(encode) isolado) ===")
    m10_bad = []
    for name, values in cols.items():
        body = _encode_column(values, header=name)
        back = _decode_column(body)
        ok = back == values
        if not ok:
            m10_bad.append(name)
            print(f"FAIL {name}")
            first_diff(values, back, name)
    if not m10_bad:
        print("todas colunas M10 RT OK (isolado)")

    # --- M10 RT multi-col (encode/decode dict completo) ---
    print("\n=== M10 RT multi-col (encode(dict)) ===")
    m10_text = encode(cols)
    back = decode(m10_text)
    if back == cols:
        print("multi-col M10 RT OK")
    else:
        print("multi-col M10 RT FAIL")
        for name in cols:
            if cols[name] != back.get(name):
                first_diff(cols[name], back.get(name, []), name)

    # --- Caracteres especiais TCF presentes? ---
    print("\n=== metacaracteres TCF nas colunas ===")
    specials = ["~", ",", "*", "|", "\\", "\n", "\r", "\t"]
    for name, values in cols.items():
        found = {s: sum(v.count(s) for v in values) for s in specials}
        found = {s: c for s, c in found.items() if c}
        if found:
            print(f"  {name}: {found}")


if __name__ == "__main__":
    main()
