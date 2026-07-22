"""H-PERF-05d re-caracterizacao — profile do encode atual (pos prune+Cython).

READ-ONLY (src/tcf intocado). Le lineitem l_comment de Z: (tpch-sf001) e mede
onde o tempo do encode vai HOJE, pra confirmar se o rebuild do Counter em
_detect_compositions ainda e' o alvo (ele e' o que o incremental-counter remove).

Lab novo (nao modifica o old/refuted/2026-05-22-h-perf-05d-counter-incremental,
fechado). T-CODE... / decisao owner 2026-06-24: caracterizar antes de weldar.
"""
from __future__ import annotations

import cProfile
import io
import pstats
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from dataset_reader import DatasetReader  # noqa: E402
from tcf import encode  # noqa: E402


def main(n=5000):
    r = DatasetReader("tpch-sf001")
    col = [row["l_comment"] for row in r.rows("lineitem", limit=n)]
    r.close()
    print(f"coluna l_comment: N={len(col)} distinct={len(set(col))}")

    ts = []
    for _ in range(3):
        t0 = time.perf_counter()
        txt = encode(col)
        ts.append(time.perf_counter() - t0)
    print(f"encode wall (min de 3): {min(ts):.3f}s  bytes={len(txt.encode('utf-8'))}")

    pr = cProfile.Profile()
    pr.enable()
    encode(col)
    pr.disable()
    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(14)
    print(s.getvalue())


if __name__ == "__main__":
    main()
