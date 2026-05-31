"""Confirma que o weld #15 esta ATIVO: timing + contagem de chamadas a
_estimate_baseline_chars (welded deve chamar MENOS, prove o prune ativo).

Compara src/tcf atual (WELDED) vs HEAD pre-weld (git show -> temp module),
encodando uma coluna free-text real de tamanho moderado.

NAO modifica src/tcf.
"""
from __future__ import annotations

import csv
import importlib.util
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

RETAIL = Path("Z:/tcf-data/external/online-retail/online_retail.csv")
N = 8000
RUNS = 3


def retail_col(col: str, limit: int) -> list[str]:
    with RETAIL.open(encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        idx = header.index(col)
        out = []
        for row in r:
            if len(out) >= limit:
                break
            if idx < len(row):
                out.append(row[idx])
        return out


def load_head_detect():
    """Carrega _detect_compositions da versao HEAD (pre-weld) de syntax.py."""
    blob = subprocess.check_output(
        ["git", "show", "HEAD:src/tcf/composicional/syntax.py"], cwd=str(REPO))
    tmp = HERE / "_head_syntax.py"
    tmp.write_bytes(blob)
    spec = importlib.util.spec_from_file_location("head_syntax", str(tmp))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["head_syntax"] = mod
    spec.loader.exec_module(mod)
    return mod.M8AVirtualRefsSyntax._detect_compositions, tmp


def timed_encode(values, runs):
    from tcf import encode
    best = min(_one(values, encode) for _ in range(runs))
    return best


def _one(values, encode):
    t0 = time.perf_counter()
    encode(values)
    return time.perf_counter() - t0


def count_estimate_calls(values):
    """Conta chamadas a _estimate_baseline_chars durante 1 encode."""
    from tcf import encode
    from tcf.composicional.syntax import M8AVirtualRefsSyntax
    orig = M8AVirtualRefsSyntax._estimate_baseline_chars
    n = [0]

    def counting(self, *a, **k):
        n[0] += 1
        return orig(self, *a, **k)

    M8AVirtualRefsSyntax._estimate_baseline_chars = counting
    try:
        encode(values)
    finally:
        M8AVirtualRefsSyntax._estimate_baseline_chars = orig
    return n[0]


def main() -> int:
    if not RETAIL.exists():
        print("Z: online-retail indisponivel — skip bench")
        return 0
    vals = retail_col("Description", N)
    print(f"workload: online-retail Description, {len(vals)} rows")

    from tcf.composicional.syntax import M8AVirtualRefsSyntax
    welded = M8AVirtualRefsSyntax._detect_compositions
    head, tmp = load_head_detect()

    # WELDED (current)
    M8AVirtualRefsSyntax._detect_compositions = welded
    t_welded = timed_encode(vals, RUNS)
    c_welded = count_estimate_calls(vals)

    # HEAD pre-weld
    M8AVirtualRefsSyntax._detect_compositions = head
    t_head = timed_encode(vals, RUNS)
    c_head = count_estimate_calls(vals)

    # restore
    M8AVirtualRefsSyntax._detect_compositions = welded
    tmp.unlink(missing_ok=True)

    print(f"\n{'':12} {'time(s)':>10} {'_estimate calls':>18}")
    print(f"{'HEAD':12} {t_head:>10.3f} {c_head:>18,}")
    print(f"{'WELDED #15':12} {t_welded:>10.3f} {c_welded:>18,}")
    print(f"\nspeedup (HEAD/WELDED): {t_head / t_welded:.3f}x")
    print(f"_estimate calls reduzidas: {(1 - c_welded / c_head) * 100:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
