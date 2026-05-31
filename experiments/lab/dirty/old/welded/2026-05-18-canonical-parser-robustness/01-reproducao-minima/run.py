"""Sub-exp 01 — Reproducao minima do bug `,` em literais.

Usa canonical OBAT + HCC (src/tcf intocado). Para cada caso, encoda +
decoda, registra RT + body.

NAO modifica nada — so' diagnostica.
"""

from __future__ import annotations

import sys
import traceback
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar  # noqa: E402


def dedup_preserve_order(values):
    seen = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def test_case(name: str, rows: list[str]) -> dict:
    """Encode + decode 1 caso. Retorna dict com info."""
    try:
        unicas = dedup_preserve_order(rows)
        tokens, _ = processar(unicas, min_len=3)
        syn = M8AVirtualRefsSyntax()
        body = syn.encode(rows, unicas, tokens, "val")
        decoded = syn.decode(body)
        rt = (decoded == rows)
        return {
            "name": name,
            "rows": rows,
            "unicas": unicas,
            "body": body,
            "decoded": decoded,
            "rt": rt,
            "rt_status": "OK" if rt else "FAIL",
            "error": None,
        }
    except Exception as e:
        return {
            "name": name,
            "rows": rows,
            "unicas": dedup_preserve_order(rows) if rows else [],
            "body": None,
            "decoded": None,
            "rt": False,
            "rt_status": "ERROR",
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }


# ---------------------------------------------------------------------------
# Casos
# ---------------------------------------------------------------------------

CASES = [
    # 1 — comma sozinho
    ("1-single-string-with-comma", ["a,b"]),
    # 2 — comma no inicio
    ("2-comma-at-start", [",abc"]),
    # 3 — comma no fim
    ("3-comma-at-end", ["abc,"]),
    # 4 — multiplas commas
    ("4-multiple-commas", ["a,b,c"]),
    # 5 — prefixo + comma (HCC cria ref prefix)
    ("5-prefix-and-comma", ["abcXYZ", "abcXYZ,def"]),
    # 6 — sufixo + comma (HCC cria ref suf)
    ("6-comma-and-suffix", ["xyzABC", "def,xyzABC"]),
    # 7 — pref+lit(comma)+suf
    ("7-pref-lit-comma-suf", ["abcXYZ...endZZZ", "abcXYZ,def,endZZZ"]),
    # 8 — TPC-H pathological (do EXP-013)
    ("8-tpch-pathological", [
        "ar packages. regular excuses among the ironic requests cajole fluffily blithely final requests. furiously express p",
        "s are. furiously even pinto bea",
        "c, special dependencies around ",
        "e dolphins are furiously about the carefully ",
        " foxes boost furiously along the carefully dogged tithes. slyly regular orbits according to the special epit",
    ]),
    # 9 — simples com prefix forte
    ("9-strong-prefix-comma", ["pending, bold reques", "pending, calm reques"]),
    # 10 — combinando refs e commas
    ("10-multiple-with-shared-prefix",
        ["prefix abc", "prefix def", "prefix a,b,c", "prefix x,y,z"]),
]


def main():
    print("=== Sub-exp 01 — Reproducao minima bug `,` em literais ===\n")
    results = []
    for name, rows in CASES:
        r = test_case(name, rows)
        results.append(r)
        status = r["rt_status"]
        if status == "OK":
            print(f"  [OK]    {name}")
        elif status == "FAIL":
            print(f"  [FAIL]  {name}  -- decoded != original")
        else:
            print(f"  [ERROR] {name}  -- {r['error']}")

    # Write detailed result
    out = ["# Sub-exp 01 — Resultado", ""]
    out.append(f"**Total casos**: {len(results)}")
    pass_ = sum(1 for r in results if r["rt_status"] == "OK")
    fail = sum(1 for r in results if r["rt_status"] == "FAIL")
    err = sum(1 for r in results if r["rt_status"] == "ERROR")
    out.append(f"- OK: {pass_}")
    out.append(f"- FAIL: {fail}")
    out.append(f"- ERROR: {err}")
    out.append("")
    out.append("## Resumo")
    out.append("")
    out.append("| # | Caso | RT |")
    out.append("|---|---|---|")
    for r in results:
        out.append(f"| `{r['name']}` | {r['rt_status']} |")
    out.append("")
    out.append("## Detalhes por caso")
    out.append("")
    for r in results:
        out.append(f"### {r['name']}")
        out.append("")
        out.append(f"**Status**: {r['rt_status']}")
        out.append("")
        out.append("**Strings input**:")
        out.append("```")
        for s in r["rows"]:
            out.append(repr(s))
        out.append("```")
        out.append("")
        if r["body"] is not None:
            out.append("**Body emitido (canonical)**:")
            out.append("```")
            out.append(r["body"].rstrip('\n'))
            out.append("```")
            out.append("")
        if r["decoded"] is not None and r["rt_status"] == "FAIL":
            out.append("**Strings decodadas (DIFF)**:")
            out.append("```")
            for orig, dec in zip(r["rows"], r["decoded"]):
                marker = "OK" if orig == dec else "**DIFF**"
                out.append(f"{marker}  orig: {orig!r}")
                if orig != dec:
                    out.append(f"      dec:  {dec!r}")
            out.append("```")
            out.append("")
        if r["rt_status"] == "ERROR":
            out.append(f"**Erro**: `{r['error']}`")
            out.append("")
            out.append("```")
            out.append(r.get("traceback", ""))
            out.append("```")
            out.append("")

    write_path = THIS / "result.md"
    write_path.write_bytes("\n".join(out).encode("utf-8"))
    print(f"\nresult.md: {write_path}")


if __name__ == "__main__":
    main()
