"""Valida byte-canonical do porte Cython + mede speedup vs welded-Python.

Monkeypatcha M8AVirtualRefsSyntax._detect_compositions com a versao Cython.
Gate: D1-D9=1523B, D17a=322B, 3 fixtures real-world (27581/11437/50598).
Speedup: online-retail Description 8k, Cython vs Python-welded (HEAD atual).

NAO modifica src/tcf.
"""
from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
SRC = REPO / "src"
for p in (str(SRC), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

SYN = REPO / "datasets" / "synthetic"
SAMP = REPO / "datasets" / "samples"
RETAIL = Path("Z:/tcf-data/external/online-retail/online_retail.csv")

D1_D9 = ["D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
         "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
         "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta"]
FIXT = {"retail-description-2k": (27581, SAMP / "online-retail/description-2k.csv"),
        "retail-stockcode-2k": (11437, SAMP / "online-retail/stockcode-2k.csv"),
        "lineitem-comment-2k": (50598, SAMP / "tpch-sf001/lcomment-2k.csv")}


def single(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f); next(r)
        return [row[0] for row in r if row]


def multi(path: Path) -> dict[str, list[str]]:
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f); h = next(r)
        cols = {c: [] for c in h}
        for row in r:
            if len(row) == len(h):
                for c, v in zip(h, row):
                    cols[c].append(v)
    return cols


def retail_desc(n: int) -> list[str]:
    with RETAIL.open(encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f); hdr = next(r); idx = hdr.index("Description")
        out = []
        for row in r:
            if len(out) >= n:
                break
            if idx < len(row):
                out.append(row[idx])
        return out


def main() -> int:
    import detect_cy
    from tcf import encode, decode
    from tcf.composicional.syntax import M8AVirtualRefsSyntax
    py_detect = M8AVirtualRefsSyntax._detect_compositions
    cy_detect = detect_cy._detect_compositions

    # ---- byte-canonical gate (Cython patched) ----
    M8AVirtualRefsSyntax._detect_compositions = cy_detect
    print("=== BYTE-CANONICAL (Cython) ===")
    total = 0
    ok = True
    for name in D1_D9:
        vals = single(SYN / f"{name}.csv")
        out = encode(vals); b = len(out.encode("utf-8"))
        total += b
        if decode(out) != vals:
            print(f"  {name}: RT FAIL"); ok = False
    print(f"  D1-D9 total = {total}B (esperado 1523) {'OK' if total == 1523 else 'FAIL'}")
    ok = ok and total == 1523

    d17 = multi(SYN / "D17a-multi-column-mixed.csv")
    out = encode(d17); b17 = len(out.encode("utf-8"))
    rt17 = decode(out) == d17
    print(f"  D17a = {b17}B (esperado 322) {'OK' if b17 == 322 and rt17 else 'FAIL'}")
    ok = ok and b17 == 322 and rt17

    for name, (exp, path) in FIXT.items():
        vals = single(path)
        out = encode(vals); b = len(out.encode("utf-8")); rt = decode(out) == vals
        good = (b == exp and rt)
        print(f"  {name} = {b}B (esperado {exp}) {'OK' if good else 'FAIL'}")
        ok = ok and good

    print(f"\nBYTE-CANONICAL: {'PASS' if ok else 'FAIL'}\n")

    # ---- speedup ----
    if RETAIL.exists():
        vals = retail_desc(8000)
        print(f"=== SPEEDUP (online-retail Description {len(vals)} rows, best de 3) ===")

        def best_time(detect):
            M8AVirtualRefsSyntax._detect_compositions = detect
            return min(_t(encode, vals) for _ in range(3))

        t_py = best_time(py_detect)
        t_cy = best_time(cy_detect)
        M8AVirtualRefsSyntax._detect_compositions = py_detect
        print(f"  Python-welded: {t_py:.3f}s")
        print(f"  Cython:        {t_cy:.3f}s")
        print(f"  speedup:       {t_py / t_cy:.3f}x")
    else:
        print("Z: indisponivel — skip speedup")

    return 0 if ok else 1


def _t(encode, vals):
    t0 = time.perf_counter(); encode(vals); return time.perf_counter() - t0


if __name__ == "__main__":
    raise SystemExit(main())
