"""Dump dos bodies pra entender por que o fix decode-side quebrou retail.

Compara como '' e' tokenizado/numerado em:
  A) sintetico ['', 'AAAB', 'AAAC']  (fix corrige)
  B) slice minimo do retail description (fix quebra)
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

FIX = ROOT / "datasets" / "samples" / "online-retail" / "description-2k.csv"


def load_desc():
    with FIX.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def rt_fails(vals):
    try:
        return _decode_column(_encode_column(vals, header="c")) != vals
    except Exception as e:
        return ("EXC", type(e).__name__, str(e))


def ddmin(vals):
    lo, hi = 0, len(vals)
    step = hi // 2
    while step >= 1:
        while hi - step > lo and rt_fails(vals[lo:hi - step]) is True:
            hi -= step
        step //= 2
    step = (hi - lo) // 2
    while step >= 1:
        while lo + step < hi and rt_fails(vals[lo + step:hi]) is True:
            lo += step
        step //= 2
    sub = vals[lo:hi]
    changed = True
    while changed and len(sub) > 1:
        changed = False
        for i in range(len(sub)):
            cand = sub[:i] + sub[i + 1:]
            if cand and rt_fails(cand) is True:
                sub = cand
                changed = True
                break
    return sub


def dump(label, vals):
    print(f"\n===== {label} =====")
    print(f"in: {vals}")
    print("empties em posicoes:", [i for i, v in enumerate(vals) if v == ''])
    body = _encode_column(vals, header="c")
    print(f"body repr: {body!r}")
    print("body linhas:")
    for j, ln in enumerate(body.split('\n')):
        print(f"  [{j}] {ln!r}")
    print(f"out: {_decode_column(body)}")


def main():
    dump("A sintetico ['','AAAB','AAAC']", ['', 'AAAB', 'AAAC'])

    desc = load_desc()
    print(f"\nretail description: {len(desc)} valores")
    print("full RT falha?", rt_fails(desc))
    print("empties no full:", [i for i, v in enumerate(desc) if v == ''][:20])
    sub = ddmin(desc)
    dump("B retail slice minimo", sub)


if __name__ == "__main__":
    main()
