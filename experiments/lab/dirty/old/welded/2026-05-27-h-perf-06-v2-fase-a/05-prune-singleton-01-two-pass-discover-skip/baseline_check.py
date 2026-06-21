"""Sanity: run baseline (NO patch) on D1-D9 + D17a to confirm 1523/322."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
SRC = REPO / "src"
DATASETS = REPO / "datasets" / "synthetic"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tcf import encode  # noqa: E402

D1_D9 = [
    "D1-emails-simples.csv",
    "D2-emails-quote-id.csv",
    "D3-stress-substring.csv",
    "D4-caos-mix.csv",
    "D5-padroes-multiplos.csv",
    "D6-poucos-em-ruido.csv",
    "D7-aninhamento.csv",
    "D8-cabeca-cauda.csv",
    "D9-frequencia-alta.csv",
]


def load_single_col(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        rows = [r[0] if r else "" for r in reader]
    return rows


def main() -> int:
    total = 0
    for name in D1_D9:
        path = DATASETS / name
        values = load_single_col(path)
        out = encode(values)
        n = len(out.encode("utf-8"))
        total += n
        print(f"{name}: {n}B (n_rows={len(values)})")
    print(f"TOTAL D1-D9 (no-patch): {total}B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
