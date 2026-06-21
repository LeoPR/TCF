"""H-PERF-06-v2 Fase A — baseline cProfile do encode TCF.

Carrega amostra 20k do online-retail (CSV externo em Z:),
roda `from tcf import encode` sob cProfile, salva `baseline.prof`
e imprime top 20 funcoes por cumtime.

Objetivo: verificar se `_detect_compositions` em HCC consome ~88%
do tempo, conforme hipotese H-PERF-06-v2.

Uso:
    python runner.py           # roda profile, salva baseline.prof, imprime top 20
"""
from __future__ import annotations

import cProfile
import csv
import io
import os
import pstats
import sys
from pathlib import Path

# Garantir que `src/` esta no path (rodar standalone, sem instalar pacote).
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # .../TCF
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tcf import encode  # noqa: E402

DATASET_CSV = Path(r"Z:/tcf-data/external/online-retail/online_retail.csv")
N_ROWS = 20_000
PROF_PATH = HERE / "baseline.prof"
TOP_N = 20


def load_dataset(path: Path, n_rows: int) -> dict[str, list[str]]:
    """Le n_rows do CSV em formato multi-col dict {col: [str, ...]}."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset nao encontrado: {path}")
    # online_retail.csv vem em latin-1 historicamente (special chars)
    # tentamos utf-8 primeiro, fallback latin-1.
    for enc in ("utf-8", "latin-1"):
        try:
            with path.open("r", encoding=enc, newline="") as fp:
                reader = csv.reader(fp)
                header = next(reader)
                cols: dict[str, list[str]] = {h: [] for h in header}
                for i, row in enumerate(reader):
                    if i >= n_rows:
                        break
                    if len(row) != len(header):
                        continue
                    for h, v in zip(header, row):
                        cols[h].append(v)
            return cols
        except UnicodeDecodeError:
            continue
    raise RuntimeError("Falha ao decodificar CSV em utf-8 ou latin-1")


def main() -> int:
    print(f"[baseline] dataset = {DATASET_CSV}")
    print(f"[baseline] n_rows alvo = {N_ROWS}")
    data = load_dataset(DATASET_CSV, N_ROWS)
    n_cols = len(data)
    n_rows_real = len(next(iter(data.values()))) if data else 0
    print(f"[baseline] carregado: {n_cols} colunas, {n_rows_real} linhas")
    total_chars = sum(sum(len(v) for v in vs) for vs in data.values())
    print(f"[baseline] total chars dado = {total_chars}")

    profiler = cProfile.Profile()
    print("[baseline] iniciando profile de encode(...)")
    profiler.enable()
    out = encode(data)
    profiler.disable()
    print(f"[baseline] encode OK. bytes saida = {len(out.encode('utf-8'))}")

    profiler.dump_stats(str(PROF_PATH))
    print(f"[baseline] profile salvo em {PROF_PATH}")

    # Top 20 por cumulative time
    sio = io.StringIO()
    stats = pstats.Stats(profiler, stream=sio).sort_stats("cumulative")
    stats.print_stats(TOP_N)
    print(sio.getvalue())

    # tambem por tottime (ajuda diagnostico)
    sio2 = io.StringIO()
    pstats.Stats(profiler, stream=sio2).sort_stats("tottime").print_stats(TOP_N)
    print("[baseline] === top por TOTTIME ===")
    print(sio2.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
