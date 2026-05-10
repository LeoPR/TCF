"""EXP-004c — TCF v0.5 com header shebang `#TCF.5 SRDM`.

Repete os mesmos 4 cenarios do EXP-004 e EXP-004b para padronizar.
A diferenca eh apenas no header — espremer cada bit:

  A (verbose): `# TCF v0.5 SRDM`             14B + flags
  B (compact): `# TCF v0.5 SRDM` + `# s:1,2` (header v0.5 igual A,
               apenas sort compacto)
  C (shebang): `#TCF.5 SRDM`                 10B + flags

Le os outputs A e B armazenados nos respectivos EXPs e gera novos
em C, comparando.

Saida: ./outputs/ + ./results.json
"""
from __future__ import annotations
import csv
import gzip
import io
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "eval"))

from tcf.v05 import encode, decode, Flags

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)
random.seed(42)


def encode_csv(rows):
    if not rows:
        return ""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()),
                        lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def to_columns(rows):
    if not rows:
        return {}
    cols = list(rows[0].keys())
    out = {c: [] for c in cols}
    for r in rows:
        for c in cols:
            out[c].append(str(r.get(c, "")))
    return out


def compare_columns(decoded, source_cols):
    if set(decoded.keys()) != set(source_cols.keys()):
        return False, "chaves diferentes"
    cols = list(source_cols.keys())
    n = len(source_cols[cols[0]])
    src = sorted(tuple(source_cols[c][i] for c in cols) for i in range(n))
    dec = sorted(tuple(decoded[c][i] for c in cols) for i in range(n))
    if src != dec:
        return False, "divergencia"
    return True, "ok"


# ---------------------------------------------------------------------------
# Variantes de header (re-implementadas localmente para comparativo)
# ---------------------------------------------------------------------------

def encode_variant_A(rows):
    """Header verbose: '# TCF v0.5 SRDM' + '# sort: col1, col2'."""
    text_c = encode(rows, flags=Flags(S=True, R=True, D=True, M=True),
                     header_style="verbose")
    # Como o encoder agora emite shebang nativo, simulamos a A localmente:
    # substitui a 1a linha
    lines = text_c.splitlines()
    if lines and lines[0].startswith("#TCF"):
        # Converte '#TCF.5 SRDM' -> '# TCF v0.5 SRDM'
        flag_part = lines[0].split(" ", 1)[1] if " " in lines[0] else ""
        lines[0] = f"# TCF v0.5 {flag_part}".rstrip()
    return "\n".join(lines) + "\n"


def encode_variant_B(rows):
    """Header com '# TCF v0.5' antigo + sort compacto '# s:1,2'."""
    text_c = encode(rows, flags=Flags(S=True, R=True, D=True, M=True),
                     header_style="compact")
    lines = text_c.splitlines()
    if lines and lines[0].startswith("#TCF"):
        flag_part = lines[0].split(" ", 1)[1] if " " in lines[0] else ""
        lines[0] = f"# TCF v0.5 {flag_part}".rstrip()
    return "\n".join(lines) + "\n"


def encode_variant_C(rows):
    """Header shebang nativo (default atual)."""
    return encode(rows, flags=Flags(S=True, R=True, D=True, M=True),
                   header_style="compact")


# ---------------------------------------------------------------------------
# Cenarios
# ---------------------------------------------------------------------------

def S1_simple_strings():
    return [
        {"comprador": "Ana",    "produto": "Abacaxi"},
        {"comprador": "Bruno",  "produto": "Banana"},
        {"comprador": "Ana",    "produto": "Cereja"},
        {"comprador": "Carlos", "produto": "Abacaxi"},
        {"comprador": "Bruno",  "produto": "Banana"},
        {"comprador": "Ana",    "produto": "Banana"},
    ]


def S2_with_int_col():
    return [
        {"comprador": "Ana",    "produto": "Abacaxi", "qty": 2},
        {"comprador": "Bruno",  "produto": "Banana",  "qty": 1},
        {"comprador": "Ana",    "produto": "Cereja",  "qty": 3},
        {"comprador": "Carlos", "produto": "Abacaxi", "qty": 1},
        {"comprador": "Bruno",  "produto": "Banana",  "qty": 2},
        {"comprador": "Ana",    "produto": "Banana",  "qty": 5},
    ]


def S3_categorical_500():
    statuses = ["pago", "pendente", "cancelado", "ok"]
    categorias = ["A", "B", "C", "D"]
    cidades = ["SP", "RJ", "BH", "POA", "REC"]
    rows = []
    for i in range(500):
        rows.append({
            "id": i + 1,
            "status": random.choice(statuses),
            "categoria": random.choice(categorias),
            "cidade": random.choice(cidades),
        })
    return rows


def S4_tpch_supplier_100():
    from data_sources import load_dataset
    tables, _ = load_dataset("canonical:tpch-sf001",
                              volume=100, seed=42, schema=["supplier"])
    rows = tables.get("supplier", [])
    return [{"s_suppkey": r["s_suppkey"],
             "s_name": r["s_name"][:20],
             "s_nationkey": r["s_nationkey"]} for r in rows]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_scenario(name: str, rows: list[dict]):
    print("=" * 96)
    print(f"[{name}] {len(rows)} rows × {len(rows[0]) if rows else 0} cols")
    print("=" * 96)

    scen = OUT / name
    scen.mkdir(exist_ok=True)

    csv_text = encode_csv(rows)
    (scen / "source.csv").write_text(csv_text, encoding="utf-8")
    b_csv = len(csv_text.encode("utf-8"))
    b_csv_gz = len(gzip.compress(csv_text.encode("utf-8"), compresslevel=9))

    text_a = encode_variant_A(rows)
    text_b = encode_variant_B(rows)
    text_c = encode_variant_C(rows)

    (scen / "tcf-A-verbose.tcf").write_text(text_a, encoding="utf-8")
    (scen / "tcf-B-mid.tcf").write_text(text_b, encoding="utf-8")
    (scen / "tcf-C-shebang.tcf").write_text(text_c, encoding="utf-8")

    b_a = len(text_a.encode("utf-8"))
    b_b = len(text_b.encode("utf-8"))
    b_c = len(text_c.encode("utf-8"))

    b_a_gz = len(gzip.compress(text_a.encode("utf-8"), compresslevel=9))
    b_b_gz = len(gzip.compress(text_b.encode("utf-8"), compresslevel=9))
    b_c_gz = len(gzip.compress(text_c.encode("utf-8"), compresslevel=9))

    # Roundtrip C apenas (decoder so le novo formato agora)
    src = to_columns(rows)
    ok_c, msg_c = compare_columns(decode(text_c), src)

    # Diffs
    c_vs_a_text_pct = (b_c / b_a - 1) * 100
    c_vs_b_text_pct = (b_c / b_b - 1) * 100
    c_vs_a_gz_pct = (b_c_gz / b_a_gz - 1) * 100
    c_vs_b_gz_pct = (b_c_gz / b_b_gz - 1) * 100

    print(f"\n  bytes (texto puro):")
    print(f"    csv:                    {b_csv:>7}")
    print(f"    A (verbose, '# TCF v0.5 ' + sort verbose):  {b_a:>7}")
    print(f"    B (verbose v0.5 + sort compact):            {b_b:>7}  ({(b_b/b_a-1)*100:+.1f}% vs A)")
    print(f"    C (shebang '#TCF.5' + sort compact):        {b_c:>7}  "
          f"({c_vs_a_text_pct:+.1f}% vs A, {c_vs_b_text_pct:+.1f}% vs B)")
    print(f"\n  bytes (apos gzip):")
    print(f"    csv+gz: {b_csv_gz}  A+gz: {b_a_gz}  B+gz: {b_b_gz}  C+gz: {b_c_gz}")
    print(f"    C+gz vs A+gz: {c_vs_a_gz_pct:+.1f}%   C+gz vs B+gz: {c_vs_b_gz_pct:+.1f}%")
    print(f"\n  roundtrip C: {'OK' if ok_c else 'FAIL — ' + msg_c}")

    # Headers lado a lado
    print(f"\n  --- A header ---")
    for line in text_a.splitlines()[:3]:
        print(f"    {line}  ({len(line.encode())}B)")
    print(f"  --- B header ---")
    for line in text_b.splitlines()[:3]:
        print(f"    {line}  ({len(line.encode())}B)")
    print(f"  --- C header ---")
    for line in text_c.splitlines()[:3]:
        print(f"    {line}  ({len(line.encode())}B)")

    return {
        "name": name,
        "n_rows": len(rows),
        "n_cols": len(rows[0]) if rows else 0,
        "bytes": {
            "csv": b_csv, "csv_gz": b_csv_gz,
            "A": b_a, "A_gz": b_a_gz,
            "B": b_b, "B_gz": b_b_gz,
            "C": b_c, "C_gz": b_c_gz,
        },
        "C_vs_A_text_pct": c_vs_a_text_pct,
        "C_vs_A_gz_pct": c_vs_a_gz_pct,
        "C_vs_B_text_pct": c_vs_b_text_pct,
        "C_vs_B_gz_pct": c_vs_b_gz_pct,
        "roundtrip_C": ok_c,
    }


def main():
    print("\n" + "=" * 96)
    print("EXP-004c — TCF v0.5 SRDM: variantes A (verbose) / B (mid) / C (shebang)")
    print("=" * 96)

    results = []
    results.append(run_scenario("S1-simple-strings", S1_simple_strings()))
    results.append(run_scenario("S2-with-int-col", S2_with_int_col()))
    results.append(run_scenario("S3-categorical-500", S3_categorical_500()))
    try:
        results.append(run_scenario("S4-tpch-supplier-100", S4_tpch_supplier_100()))
    except Exception as e:
        print(f"\n[skip] S4: {type(e).__name__}: {e}")

    # ---- Sintese ----
    print("\n" + "=" * 96)
    print("Sintese")
    print("=" * 96)
    print(f"\n  {'cenario':<26} {'A':>6} {'B':>6} {'C':>6} {'C vs A':>9} {'C vs B':>9} "
          f"{'A+gz':>6} {'C+gz':>6} {'C+gz vs A+gz':>14}")
    print(f"  {'-'*26} {'-'*6} {'-'*6} {'-'*6} {'-'*9} {'-'*9} "
          f"{'-'*6} {'-'*6} {'-'*14}")
    for r in results:
        b = r["bytes"]
        print(f"  {r['name']:<26} {b['A']:>6} {b['B']:>6} {b['C']:>6} "
              f"{r['C_vs_A_text_pct']:>+8.1f}% {r['C_vs_B_text_pct']:>+8.1f}% "
              f"{b['A_gz']:>6} {b['C_gz']:>6} {r['C_vs_A_gz_pct']:>+13.1f}%")

    avg_text_a = sum(r["C_vs_A_text_pct"] for r in results) / len(results)
    avg_text_b = sum(r["C_vs_B_text_pct"] for r in results) / len(results)
    avg_gz_a = sum(r["C_vs_A_gz_pct"] for r in results) / len(results)
    avg_gz_b = sum(r["C_vs_B_gz_pct"] for r in results) / len(results)

    print(f"\n  Avg C vs A (texto): {avg_text_a:+.2f}%")
    print(f"  Avg C vs B (texto): {avg_text_b:+.2f}%")
    print(f"  Avg C vs A (gzip):  {avg_gz_a:+.2f}%")
    print(f"  Avg C vs B (gzip):  {avg_gz_b:+.2f}%")

    # Salva
    summary = {
        "experiment": "EXP-004c",
        "scenarios": results,
        "avg_C_vs_A_text_pct": avg_text_a,
        "avg_C_vs_B_text_pct": avg_text_b,
        "avg_C_vs_A_gz_pct": avg_gz_a,
        "avg_C_vs_B_gz_pct": avg_gz_b,
    }
    (OUT / "results.json").write_text(json.dumps(summary, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
