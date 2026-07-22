"""run-baseline — regenera outputs/ canonical pra baseline 2026-05-27.

Roda pipeline canonical em D1-D9 + D17a + reais (se disponivel),
salva `.tcf`s em `outputs/<dataset>/<name>.tcf`, valida RT, imprime
bytes pra comparacao com METRICS.md.

Uso:
    python run-baseline.py           # D1-D9 + D17a
    python run-baseline.py D1-D9     # so' single-col sint
    python run-baseline.py D17a      # so' multi-col INVARIANT
    python run-baseline.py --all     # tudo + real-world (se Z: disponivel)
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# Ajusta path pra src/
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from tcf import encode, decode  # noqa: E402

THIS = Path(__file__).resolve().parent
OUT = THIS / "outputs"
DATASETS = ROOT / "datasets" / "synthetic"

D1_D9 = [
    "D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
    "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
    "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta",
]


def _load_single_col(name: str) -> list[str]:
    path = DATASETS / f"{name}.csv"
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def _load_multi_col(name: str) -> dict[str, list[str]]:
    path = DATASETS / f"{name}.csv"
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for row in r:
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


def _save(name: str, text: str) -> int:
    sub = OUT / name
    sub.mkdir(parents=True, exist_ok=True)
    p = sub / f"{name}.tcf"
    raw = text.encode("utf-8")
    p.write_bytes(raw)
    return len(raw)


def run_d1_d9() -> None:
    print("=== D1-D9 single-column ===")
    print(f"{'dataset':<28} {'raw_B':>8} {'tcf_B':>8} {'ratio':>8} {'RT':>6}")
    print("-" * 64)
    total_raw = 0
    total_tcf = 0
    for name in D1_D9:
        values = _load_single_col(name)
        raw_bytes = sum(len(v.encode("utf-8")) for v in values)
        text = encode(values)
        tcf_bytes = _save(name, text)
        rt = decode(text) == values
        ratio = tcf_bytes / raw_bytes * 100 if raw_bytes else 0
        total_raw += raw_bytes
        total_tcf += tcf_bytes
        rt_str = "OK" if rt else "FAIL"
        print(f"{name:<28} {raw_bytes:>8} {tcf_bytes:>8} {ratio:>7.1f}% {rt_str:>6}")
    print("-" * 64)
    total_ratio = total_tcf / total_raw * 100 if total_raw else 0
    print(f"{'TOTAL':<28} {total_raw:>8} {total_tcf:>8} {total_ratio:>7.1f}%")
    print()


def run_d17a() -> None:
    print("=== D17a multi-column INVARIANT ===")
    cols = _load_multi_col("D17a-multi-column-mixed")
    text = encode(cols)
    tcf_bytes = _save("D17a-multi-column-mixed", text)
    rt = decode(text) == cols
    invariant_ok = tcf_bytes == 322
    print(f"D17a bytes:     {tcf_bytes} (esperado: 322)")
    print(f"RT:             {'OK' if rt else 'FAIL'}")
    print(f"INVARIANT 322B: {'OK' if invariant_ok else 'BROKEN'}")
    print()


def main() -> int:
    args = sys.argv[1:]
    if not args:
        run_d1_d9()
        run_d17a()
        return 0
    if args[0] == "D1-D9":
        run_d1_d9()
    elif args[0] == "D17a":
        run_d17a()
    elif args[0] == "--all":
        run_d1_d9()
        run_d17a()
        # Real-world tem que apontar pra Z:/ — skip aqui (out of scope baseline simples)
        print("[real-world skipped — usar experiments/lab/dirty/old/welded/2026-05-23-multi-column-scaling]")
    else:
        print(f"unknown arg: {args[0]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
