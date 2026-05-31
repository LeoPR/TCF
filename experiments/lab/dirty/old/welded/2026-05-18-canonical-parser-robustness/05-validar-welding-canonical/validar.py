"""Sub-exp 05 — validar welding canonical do fix bug `,` em literais.

Welding foi aplicado em src/tcf/composicional/syntax.py linhas 435-442
em 2026-05-19 (Bug fix 2026-05-19 (ADR-0007)). Mas ADR-0007 esta com
status `proposed` e roadmap H-FIX-01/02/03 esta `aberta`.

Este sub-exp valida:
1. Casos sub-exp 01 (10 casos minimos) — esperado 10/10 OK (era 7/10 pre-fix)
2. D1-D9 M10 baseline 1523B preservado
3. RT 100% em Adult Census + TPC-H

Se OK: atualizar ADR-0007 (proposed -> accepted + welded), roadmap, ticket.
"""

from __future__ import annotations

import csv
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))

from dataset_reader import DatasetReader  # noqa: E402
from tcf import encode as tcf_encode  # noqa: E402
from tcf import decode as tcf_decode  # noqa: E402


D1_D9 = [
    "D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
    "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
    "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta",
]

# Casos minimos do sub-exp 01
TEST_CASES = [
    ("1-single-string-with-comma", ['a,b']),
    ("2-comma-at-start", [',abc']),
    ("3-comma-at-end", ['abc,']),
    ("4-multiple-commas", ['a,b,c']),
    ("5-prefix-and-comma", ['abcXYZ', 'abcXYZ,def']),
    ("6-comma-and-suffix", ['xyzABC', 'def,xyzABC']),
    ("7-pref-lit-comma-suf", ['abcXYZ...endZZZ', 'abcXYZ,def,endZZZ']),
    ("8-tpch-pathological", [
        'ar packages. regular excuses among the ironic requests cajole fluffily blithely final requests. furiously express p',
        's are. furiously even pinto bea',
        'c, special dependencies around ',
        'e dolphins are furiously about the carefully ',
        ' foxes boost furiously along the carefully dogged tithes. slyly regular orbits according to the special epit',
    ]),
    ("9-strong-prefix-comma", ['pending, bold reques', 'pending, calm reques']),
    ("10-multiple-with-shared-prefix", [
        'prefix abc', 'prefix def', 'prefix a,b,c', 'prefix x,y,z'
    ]),
]


def ler_csv_single_col(path):
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def rows_to_cols(rows):
    if not rows:
        return {}
    return {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in rows[0].keys()}


def main():
    print("=== Sub-exp 05 — validar welding canonical bug `,` ===\n")

    # ---- Casos minimos ----
    print(">> Casos minimos (sub-exp 01)")
    case_ok = 0
    case_total = len(TEST_CASES)
    for name, strings in TEST_CASES:
        try:
            tcf = tcf_encode(strings)
            decoded = tcf_decode(tcf)
            rt = strings == decoded
        except Exception as e:
            print(f"  {name}: ERROR {e}")
            continue
        marker = "OK" if rt else "FAIL"
        if rt:
            case_ok += 1
        if not rt:
            print(f"  {name}: {marker}")
            print(f"    expected: {strings}")
            print(f"    decoded:  {decoded}")
        else:
            print(f"  {name}: {marker}")

    print(f"\nCasos: {case_ok}/{case_total}")

    # ---- D1-D9 M10 baseline ----
    print("\n>> D1-D9 M10 baseline (1523B esperado)")
    datasets_dir = ROOT / "datasets" / "synthetic"
    total_d1d9 = 0
    rt_d1d9 = 0
    for ds in D1_D9:
        values = ler_csv_single_col(datasets_dir / f"{ds}.csv")
        try:
            tcf = tcf_encode(values)
            decoded = tcf_decode(tcf)
            bytes_t = len(tcf.encode("utf-8"))
            rt = values == decoded
            total_d1d9 += bytes_t
            if rt:
                rt_d1d9 += 1
            print(f"  {ds:<25} {bytes_t:>4}B  RT={'OK' if rt else 'FAIL'}")
        except Exception as e:
            print(f"  {ds:<25} ERROR: {e}")
    print(f"  TOTAL D1-D9: {total_d1d9}B  RT={rt_d1d9}/{len(D1_D9)}")
    d1d9_match_m10 = (total_d1d9 == 1523)

    # ---- Adult Census + TPC-H RT ----
    print("\n>> Adult Census + TPC-H RT")
    rw_total = 0
    rw_pass = 0
    rw_bytes = 0
    reader = DatasetReader("adult-census")
    for vol in [1000, 5000]:
        rows = reader.rows("adult", limit=vol)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            try:
                tcf = tcf_encode(vals)
                decoded = tcf_decode(tcf)
                bytes_t = len(tcf.encode("utf-8"))
                rt = vals == decoded
                rw_total += 1
                if rt:
                    rw_pass += 1
                rw_bytes += bytes_t
                if not rt:
                    print(f"  adult-{vol}/{cname}: FAIL")
            except Exception as e:
                print(f"  adult-{vol}/{cname}: ERROR {e}")
                rw_total += 1
    reader.close()
    reader = DatasetReader("tpch-sf001")
    for table in ["region", "customer", "lineitem"]:
        rows = reader.rows(table, limit=5000)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            try:
                tcf = tcf_encode(vals)
                decoded = tcf_decode(tcf)
                bytes_t = len(tcf.encode("utf-8"))
                rt = vals == decoded
                rw_total += 1
                if rt:
                    rw_pass += 1
                rw_bytes += bytes_t
                if not rt:
                    print(f"  tpch.{table}-5k/{cname}: FAIL")
            except Exception as e:
                print(f"  tpch.{table}-5k/{cname}: ERROR {e}")
                rw_total += 1
    reader.close()
    print(f"  Real-world: {rw_pass}/{rw_total} RT, {rw_bytes:,}B total")

    # Veredito
    print(f"\n=== Veredito welding canonical Pacote 3 ===\n")
    print(f"Casos minimos sub-exp 01: {case_ok}/{case_total} "
          f"({'PASS' if case_ok == case_total else 'FAIL'})")
    print(f"D1-D9 M10 baseline 1523B: {'PRESERVADO' if d1d9_match_m10 else 'MUDOU'} "
          f"(atual {total_d1d9}B)")
    print(f"D1-D9 RT 100%: {rt_d1d9}/{len(D1_D9)}")
    print(f"Real-world RT 100%: {rw_pass}/{rw_total}")

    welding_ok = (case_ok == case_total and d1d9_match_m10
                  and rt_d1d9 == len(D1_D9) and rw_pass == rw_total)
    print(f"\n** WELDING PACOTE 3 {'CONFIRMED' if welding_ok else 'PROBLEMS'} **")

    # Report
    report = [
        "# Sub-exp 05 — validar welding canonical Pacote 3 (bug `,` em literais)",
        "",
        "## Status pre-validacao",
        "",
        "Fix aplicado em `src/tcf/composicional/syntax.py` linhas 435-442",
        "(comentario menciona 'Bug fix 2026-05-19 (ADR-0007)').",
        "ADR-0007 ainda status `proposed`. Roadmap H-FIX-01/02/03 aberta.",
        "",
        "Este sub-exp valida que welding esta funcional + sem regressao.",
        "",
        "## Casos minimos (sub-exp 01)",
        "",
        f"**{case_ok}/{case_total} OK** (era 7/10 pre-fix).",
        "",
        "Casos 5, 7, 10 (FAIL pre-fix) devem agora estar OK.",
        "",
        "## D1-D9 M10 baseline",
        "",
        f"Total D1-D9: **{total_d1d9}B** ({'== 1523B preservado' if d1d9_match_m10 else 'MUDOU'})",
        f"RT: {rt_d1d9}/{len(D1_D9)}",
        "",
        "## Adult Census + TPC-H",
        "",
        f"- 57 cols testadas",
        f"- RT: {rw_pass}/{rw_total}",
        f"- Bytes total: {rw_bytes:,}",
        "",
        "## Veredito",
        "",
        f"- Casos minimos: {'OK' if case_ok == case_total else 'FAIL'}",
        f"- D1-D9 baseline: {'OK' if d1d9_match_m10 else 'FAIL'}",
        f"- D1-D9 RT 100%: {'OK' if rt_d1d9 == len(D1_D9) else 'FAIL'}",
        f"- Real-world RT 100%: {'OK' if rw_pass == rw_total else 'FAIL'}",
        "",
        f"**WELDING PACOTE 3: {'CONFIRMED' if welding_ok else 'PROBLEMS'}**",
        "",
    ]

    out = THIS / "result.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out}")


if __name__ == "__main__":
    main()
