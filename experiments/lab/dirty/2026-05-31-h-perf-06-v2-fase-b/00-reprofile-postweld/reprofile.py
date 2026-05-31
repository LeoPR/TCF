"""H-PERF-06-v2 Fase B — re-profile POS-weld (#15 ja' em src/tcf).

O weld #15 cortou 87% das chamadas a _estimate_baseline_chars. O profile
da Fase A (pre-weld: _detect=87.7%, _estimate=18.5%) esta OBSOLETO. Antes
de decidir o que compilar (Cython), re-medir onde o tempo vai AGORA.

Mesmo workload da baseline Fase A (online-retail 20k x 8 col) pra
comparabilidade direta.

NAO modifica src/tcf.
"""
from __future__ import annotations

import cProfile
import csv
import pstats
import sys
from io import StringIO
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

RETAIL = Path("Z:/tcf-data/external/online-retail/online_retail.csv")
N = 20000


def load_cols(limit: int) -> dict[str, list[str]]:
    with RETAIL.open(encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for i, row in enumerate(r):
            if i >= limit:
                break
            if len(row) != len(header):
                continue
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


def main() -> int:
    if not RETAIL.exists():
        print("Z: online-retail indisponivel")
        return 1
    from tcf import encode
    cols = load_cols(N)
    nrows = len(next(iter(cols.values())))
    raw = sum(len(str(v)) for vs in cols.values() for v in vs)
    print(f"workload: online-retail {nrows} rows x {len(cols)} cols, {raw:,} chars")

    prof = cProfile.Profile()
    prof.enable()
    out = encode(cols)
    prof.disable()
    prof.dump_stats(str(HERE / "postweld.prof"))

    total = len(out.encode("utf-8"))
    print(f"encode -> {total:,} bytes\n")

    for sort_key, label in [("cumulative", "CUMULATIVE"), ("tottime", "TOTTIME")]:
        buf = StringIO()
        st = pstats.Stats(prof, stream=buf)
        st.sort_stats(sort_key).print_stats(18)
        print(f"===== TOP 18 by {label} =====")
        # imprime so' as linhas de dados (pula header do pstats)
        for line in buf.getvalue().splitlines():
            s = line.strip()
            if s and ("syntax.py" in s or "online.py" in s or "hcc_seqrle" in s
                      or "encoder.py" in s or "{" in s or "multi.py" in s
                      or "ncalls" in s):
                print(line)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
