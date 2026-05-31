"""Sub-exp 02 — testa Opcao A em 3 frentes:
1. Casos sub-exp 01 (deve fixar bugs)
2. D1-D9 (M9 baseline — verificar shifts)
3. TPC-H 5 tabelas pequenas (validar fix em real-world)
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
from hcc_fork_escape_comma import HCCEscapeCommaSyntax  # noqa: E402


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


def test_subexp01_cases():
    """Casos sub-exp 01 — devem agora passar com fork."""
    cases = [
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
    print("\n--- Sub-exp 01 cases (canonical vs fork) ---")
    print(f"{'caso':30} {'canon':>6} {'fork':>6}")
    for name, rows in cases:
        try:
            b_c, d_c = encode_decode(rows, M8AVirtualRefsSyntax)
            rt_c = "OK" if d_c == rows else "FAIL"
        except Exception as e:
            rt_c = f"ERR({type(e).__name__})"
        try:
            b_f, d_f = encode_decode(rows, HCCEscapeCommaSyntax)
            rt_f = "OK" if d_f == rows else "FAIL"
        except Exception as e:
            rt_f = f"ERR({type(e).__name__})"
        print(f"{name:30} {rt_c:>6} {rt_f:>6}")


def test_d1_d9():
    """D1-D9 byte-canonical comparison."""
    DATASETS = [f"D{i}" for i in range(1, 10)]
    NAMES = {
        "D1": "D1-emails-simples",
        "D2": "D2-emails-quote-id",
        "D3": "D3-stress-substring",
        "D4": "D4-caos-mix",
        "D5": "D5-padroes-multiplos",
        "D6": "D6-poucos-em-ruido",
        "D7": "D7-aninhamento",
        "D8": "D8-cabeca-cauda",
        "D9": "D9-frequencia-alta",
    }
    print("\n--- D1-D9 (M9 baseline shift?) ---")
    print(f"{'dataset':22} {'canon':>6} {'fork':>6} {'delta':>6} RT-canon RT-fork")
    total_canon, total_fork = 0, 0
    for d in DATASETS:
        ds_name = NAMES[d]
        p = ROOT / "datasets" / "synthetic" / f"{ds_name}.csv"
        with p.open(encoding="utf-8") as f:
            r = csv.reader(f)
            next(r)
            rows = [row[0] for row in r if row]
        try:
            b_c, d_c = encode_decode(rows, M8AVirtualRefsSyntax)
            n_c = len(b_c.encode("utf-8"))
            rt_c = "OK" if d_c == rows else "FAIL"
        except Exception:
            n_c, rt_c = 0, "ERR"
        try:
            b_f, d_f = encode_decode(rows, HCCEscapeCommaSyntax)
            n_f = len(b_f.encode("utf-8"))
            rt_f = "OK" if d_f == rows else "FAIL"
        except Exception:
            n_f, rt_f = 0, "ERR"
        delta = n_f - n_c
        total_canon += n_c
        total_fork += n_f
        print(f"{ds_name:22} {n_c:>6} {n_f:>6} {delta:>+6} {rt_c:>8} {rt_f:>7}")
    print(f"{'TOTAL':22} {total_canon:>6} {total_fork:>6} {total_fork-total_canon:>+6}")


def test_tpch_sample():
    """TPC-H — re-test tabelas que falharam em EXP-013."""
    print("\n--- TPC-H sample ---")
    print(f"{'tabela':14} {'rows':>5} {'canon':>8} {'fork':>8} RT-canon RT-fork")
    reader = DatasetReader("tpch-sf001")
    for table in ["region", "nation", "supplier", "customer"]:
        rows_dict = reader.rows(table, limit=500)
        if not rows_dict:
            continue
        # All columns concatenated as test
        for col in rows_dict[0].keys():
            vals = [str(r[col]) if r[col] is not None else "" for r in rows_dict]
            try:
                b_c, d_c = encode_decode(vals, M8AVirtualRefsSyntax)
                rt_c = "OK" if d_c == vals else "FAIL"
                n_c = len(b_c.encode("utf-8"))
            except Exception:
                rt_c, n_c = "ERR", 0
            try:
                b_f, d_f = encode_decode(vals, HCCEscapeCommaSyntax)
                rt_f = "OK" if d_f == vals else "FAIL"
                n_f = len(b_f.encode("utf-8"))
            except Exception:
                rt_f, n_f = "ERR", 0
            marker = "*" if rt_c != rt_f else " "
            print(f"{table+'.'+col:30} {n_c:>6} {n_f:>6} {rt_c:>4} {rt_f:>4} {marker}")
    reader.close()


def main():
    print("=== Sub-exp 02 — Opcao A (escape `,`) ===")
    test_subexp01_cases()
    test_d1_d9()
    test_tpch_sample()


if __name__ == "__main__":
    main()
