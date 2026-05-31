"""Sub-exp 03 — Opcao B (separator heuristico).

Mesmo plano sub-exp 02: cases + D1-D9 + TPC-H sample.
"""

from __future__ import annotations

import csv
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(THIS))

from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar  # noqa: E402
from dataset_reader import DatasetReader  # noqa: E402
from hcc_fork_separator import HCCSeparatorSyntax  # noqa: E402


def dedup(values):
    seen = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def encode_decode(rows, SyntaxClass):
    unicas = dedup(rows)
    tokens, _ = processar(unicas, min_len=3)
    syn = SyntaxClass()
    body = syn.encode(rows, unicas, tokens, "val")
    decoded = syn.decode(body)
    return body, decoded


CASES = [
    ("1-single-comma", ["a,b"]),
    ("2-comma-start", [",abc"]),
    ("3-comma-end", ["abc,"]),
    ("4-multi-commas", ["a,b,c"]),
    ("5-prefix-comma", ["abcXYZ", "abcXYZ,def"]),
    ("6-comma-suffix", ["xyzABC", "def,xyzABC"]),
    ("7-pref-lit-suf", ["abcXYZ...endZZZ", "abcXYZ,def,endZZZ"]),
    ("8-tpch-path", [
        "ar packages. regular excuses among the ironic requests cajole fluffily blithely final requests. furiously express p",
        "s are. furiously even pinto bea",
        "c, special dependencies around ",
        "e dolphins are furiously about the carefully ",
        " foxes boost furiously along the carefully dogged tithes. slyly regular orbits according to the special epit",
    ]),
    ("9-strong-pref", ["pending, bold reques", "pending, calm reques"]),
    ("10-multi-shared", [
        "prefix abc", "prefix def", "prefix a,b,c", "prefix x,y,z"
    ]),
]

D1_D9 = [
    "D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
    "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
    "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta",
]


def test_cases():
    print("\n--- Sub-exp 01 cases ---")
    print(f"{'caso':30} {'canon':>6} {'fork':>6}")
    for name, rows in CASES:
        try:
            b_c, d_c = encode_decode(rows, M8AVirtualRefsSyntax)
            rt_c = "OK" if d_c == rows else "FAIL"
        except Exception as e:
            rt_c = f"ERR"
        try:
            b_f, d_f = encode_decode(rows, HCCSeparatorSyntax)
            rt_f = "OK" if d_f == rows else "FAIL"
        except Exception:
            rt_f = "ERR"
        print(f"{name:30} {rt_c:>6} {rt_f:>6}")


def test_d1_d9():
    print("\n--- D1-D9 ---")
    print(f"{'dataset':22} {'canon':>6} {'fork':>6} {'delta':>6}")
    tot_c, tot_f = 0, 0
    for ds in D1_D9:
        p = ROOT / "datasets" / "synthetic" / f"{ds}.csv"
        with p.open(encoding="utf-8") as f:
            r = csv.reader(f)
            next(r)
            rows = [row[0] for row in r if row]
        b_c, _ = encode_decode(rows, M8AVirtualRefsSyntax)
        b_f, _ = encode_decode(rows, HCCSeparatorSyntax)
        n_c, n_f = len(b_c.encode("utf-8")), len(b_f.encode("utf-8"))
        tot_c += n_c
        tot_f += n_f
        print(f"{ds:22} {n_c:>6} {n_f:>6} {n_f-n_c:>+6}")
    print(f"{'TOTAL':22} {tot_c:>6} {tot_f:>6} {tot_f-tot_c:>+6}")


def test_tpch():
    print("\n--- TPC-H sample ---")
    reader = DatasetReader("tpch-sf001")
    for table in ["region", "nation", "supplier", "customer"]:
        rows_dict = reader.rows(table, limit=500)
        if not rows_dict:
            continue
        for col in rows_dict[0].keys():
            vals = [str(r[col]) if r[col] is not None else "" for r in rows_dict]
            try:
                b_c, d_c = encode_decode(vals, M8AVirtualRefsSyntax)
                rt_c = "OK" if d_c == vals else "FAIL"
                n_c = len(b_c.encode("utf-8"))
            except Exception:
                rt_c, n_c = "ERR", 0
            try:
                b_f, d_f = encode_decode(vals, HCCSeparatorSyntax)
                rt_f = "OK" if d_f == vals else "FAIL"
                n_f = len(b_f.encode("utf-8"))
            except Exception:
                rt_f, n_f = "ERR", 0
            marker = "*" if rt_c != rt_f else " "
            if rt_c != rt_f or n_c != n_f:
                print(f"{table+'.'+col:30} {n_c:>6} {n_f:>6} {rt_c:>4} {rt_f:>4} {marker}")
    reader.close()


def main():
    print("=== Sub-exp 03 — Opcao B (separator heuristico) ===")
    test_cases()
    test_d1_d9()
    test_tpch()


if __name__ == "__main__":
    main()
