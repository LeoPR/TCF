"""run_lote.py — M13 (welding step 3: API publica `from tcf import encode, decode`).

Smoke test do welding step 3: usa a API publica de alto nivel
(`encode(values: list[str])`, `decode(text: str)`) em vez de chamar
`M8AVirtualRefsSyntax` diretamente.

Validacao: bytes byte-a-byte identicos a M12 (e por extensao M11/M10/M9).

Apos passar, src/tcf esta com encode/decode formalmente funcionando.
"""

import csv
import sys
from pathlib import Path

THIS = Path(__file__).parent

# src/ no sys.path para `from tcf import encode, decode` funcionar.
SRC = THIS.parents[3] / "src"
sys.path.insert(0, str(SRC))

DATASETS_DIR = THIS.parents[3] / "datasets" / "synthetic"

from tcf import encode, decode  # noqa: E402


DATASETS = [
    "D1-emails-simples",
    "D2-emails-quote-id",
    "D3-stress-substring",
    "D4-caos-mix",
    "D5-padroes-multiplos",
    "D6-poucos-em-ruido",
    "D7-aninhamento",
    "D8-cabeca-cauda",
    "D9-frequencia-alta",
]


def write_lf(path, content):
    path.write_bytes(content.encode("utf-8"))


def ler_csv(path):
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)[0]
        return header, [row[0] for row in r if row]


def main():
    out_dir = THIS / "M13-tcf-api"
    (out_dir / "output").mkdir(parents=True, exist_ok=True)
    (out_dir / "decoded").mkdir(parents=True, exist_ok=True)
    (out_dir / "debug").mkdir(parents=True, exist_ok=True)

    print(f"=== M13 (welding step 3: API publica `from tcf import encode/decode`) ===")
    print()

    total_bytes = 0
    total_raw = 0
    rt_count = 0

    for ds in DATASETS:
        header, linhas = ler_csv(DATASETS_DIR / f"{ds}.csv")
        raw_bytes = sum(len(l.encode("utf-8")) + 1 for l in linhas)

        tcf = encode(linhas)
        write_lf(out_dir / "output" / f"{ds}.tcf", tcf)
        n_bytes = len(tcf.encode("utf-8"))

        decoded = decode(tcf)
        with (out_dir / "decoded" / f"{ds}.csv").open(
                "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow([header])
            for line in decoded:
                w.writerow([line])

        rt_ok = decoded == linhas
        if rt_ok:
            rt_count += 1
        total_bytes += n_bytes
        total_raw += raw_bytes

        mark = "OK" if rt_ok else "FAIL"
        ratio = f"{n_bytes/raw_bytes:.0%} raw" if raw_bytes else "?"
        print(f"  {ds:<30} [{mark}] {n_bytes:>4} bytes ({ratio})")

        # Debug summary
        debug = [
            f"# M13 — {ds}",
            f"# bytes={n_bytes}  roundtrip={'OK' if rt_ok else 'FAIL'}",
            "", "INPUT:",
        ]
        for i, l in enumerate(linhas, 1):
            debug.append(f"  [{i}] {l}")
        debug.append("\nTCF:")
        for line in tcf.splitlines():
            debug.append(f"  {line}")
        debug.append("\nDECODE:")
        for i, line in enumerate(decoded, 1):
            mark_line = " " if i <= len(linhas) and line == linhas[i-1] else "X"
            debug.append(f"  [{mark_line}] {line}")
        write_lf(out_dir / "debug" / f"{ds}.txt", "\n".join(debug))

    print()
    print(f"TOTAL: {total_bytes} bytes em {total_raw} raw "
          f"({total_bytes/total_raw:.1%} ratio)")
    print(f"RT: {rt_count}/{len(DATASETS)} OK")


if __name__ == "__main__":
    main()
