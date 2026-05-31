"""T-REGRESSION-REAL-WORLD — gera fixtures discriminantes (reproduzivel).

Extrai os PRIMEIROS N=2000 valores (ordem de insercao do hub) das colunas
free-text que provaram poder discriminante no probe.py (catch #03, regime
n_tam_est>=3):

  - online-retail Description  -> datasets/samples/online-retail/description-2k.csv
  - online-retail StockCode    -> datasets/samples/online-retail/stockcode-2k.csv
  - tpch lineitem l_comment    -> datasets/samples/tpch-sf001/lcomment-2k.csv

Determinismo: "primeiros N" da fonte canonica (CSV / SQLite rowid order).
Fixture committada vira a fonte-de-verdade frozen; teste le a fixture (NAO
Z:), entao e' portavel e independente de Z:.

NAO modifica src/tcf. Le de Z: (fonte canonica) e escreve fixtures em git.
Rodar uma vez; re-rodar regenera identico (fonte estatica).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SAMPLES = REPO / "datasets" / "samples"
RETAIL_CSV = Path("Z:/tcf-data/external/online-retail/online_retail.csv")
N = 2000


def retail_col(colname: str, limit: int) -> list[str]:
    with RETAIL_CSV.open(encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        idx = header.index(colname)
        out = []
        for i, row in enumerate(r):
            if len(out) >= limit:
                break
            if idx < len(row):
                out.append(row[idx])
        return out


def lineitem_col(colname: str, limit: int) -> list[str]:
    from dataset_reader import DatasetReader
    with DatasetReader("tpch-sf001") as rd:
        cols = rd.columns("lineitem", limit=limit)
    return [("" if v is None else str(v)) for v in cols[colname]]


def write_single_col(path: Path, header: str, values: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # newline='' + csv.writer => quoting correto; LF-only via lineterminator
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow([header])
        for v in values:
            w.writerow([v])
    # verifica read-back exato (fixture deve preservar strings)
    back = read_single_col(path)
    assert back == values, f"fixture read-back mismatch em {path.name}: {len(back)} vs {len(values)}"


def read_single_col(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def main() -> int:
    jobs = [
        (SAMPLES / "online-retail" / "description-2k.csv", "Description",
         retail_col("Description", N)),
        (SAMPLES / "online-retail" / "stockcode-2k.csv", "StockCode",
         retail_col("StockCode", N)),
        (SAMPLES / "tpch-sf001" / "lcomment-2k.csv", "l_comment",
         lineitem_col("l_comment", N)),
    ]
    for path, header, values in jobs:
        write_single_col(path, header, values)
        raw = path.stat().st_size
        print(f"WROTE {path.relative_to(REPO)}  rows={len(values)}  csv={raw}B  "
              f"read-back=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
