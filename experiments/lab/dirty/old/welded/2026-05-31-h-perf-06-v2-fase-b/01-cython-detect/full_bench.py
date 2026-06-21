"""Speedup OVERALL no encode completo (online-retail 20k x 8 col),
Cython vs Python-welded vs (referencia) original pre-weld."""
from __future__ import annotations

import csv
import subprocess
import sys
import time
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
SRC = REPO / "src"
for p in (str(SRC), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)
RETAIL = Path("Z:/tcf-data/external/online-retail/online_retail.csv")
N = 20000


def cols(n):
    with RETAIL.open(encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f); h = next(r); c = {x: [] for x in h}
        for i, row in enumerate(r):
            if i >= n: break
            if len(row) == len(h):
                for x, v in zip(h, row): c[x].append(v)
    return c


def head_detect():
    blob = subprocess.check_output(
        ["git", "show", "HEAD~3:src/tcf/composicional/syntax.py"], cwd=str(REPO))
    # HEAD~3 = antes do weld #15 (2b6edc0 fix < bb321c5 gate < 8118d7a weld);
    # ajustar se necessario. Fallback: pula referencia pre-weld.
    tmp = HERE / "_preweld.py"; tmp.write_bytes(blob)
    spec = importlib.util.spec_from_file_location("preweld_syntax", str(tmp))
    m = importlib.util.module_from_spec(spec); sys.modules["preweld_syntax"] = m
    spec.loader.exec_module(m)
    return m.M8AVirtualRefsSyntax._detect_compositions, tmp


def best(encode, data, detect, M):
    M._detect_compositions = detect
    return min(_t(encode, data) for _ in range(3))


def _t(encode, data):
    t0 = time.perf_counter(); encode(data); return time.perf_counter() - t0


def main():
    if not RETAIL.exists():
        print("Z: indisponivel"); return 1
    import detect_cy
    from tcf import encode
    from tcf.composicional.syntax import M8AVirtualRefsSyntax as M
    data = cols(N)
    py = M._detect_compositions
    cy = detect_cy._detect_compositions
    try:
        pre, tmp = head_detect()
    except Exception as e:
        pre, tmp = None, None
        print(f"(pre-weld ref indisponivel: {e})")

    t_py = best(encode, data, py, M)
    t_cy = best(encode, data, cy, M)
    print(f"encode completo online-retail {N}x8col (best de 3):")
    if pre is not None:
        t_pre = best(encode, data, pre, M)
        print(f"  pre-weld (Python):    {t_pre:.3f}s")
    print(f"  welded #15 (Python):  {t_py:.3f}s")
    print(f"  welded + Cython:      {t_cy:.3f}s")
    print(f"  speedup Cython vs Python-welded: {t_py / t_cy:.3f}x")
    if pre is not None:
        print(f"  speedup Cython vs pre-weld total: {t_pre / t_cy:.3f}x")
    M._detect_compositions = py
    if tmp: tmp.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
