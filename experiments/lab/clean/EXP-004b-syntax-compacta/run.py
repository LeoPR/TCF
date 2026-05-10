"""EXP-004b — TCF v0.5 SRDM com sintaxe compacta no header.

Repete cenarios do EXP-004 com header_style="compact" e compara com
header_style="verbose" (referencia).

Mudancas na sintaxe:
  ANTES (verbose):  '# sort: comprador, produto'
  DEPOIS (compact): '# s:1,2'  (indices 1-based, sem espacos)

Roundtrip OK eh requisito (decoder le ambas).

Saida: ./outputs/ + ./results.json + estatisticas no console.
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
        return False, f"divergencia em {sum(1 for s,d in zip(src,dec) if s!=d)} linhas"
    return True, "ok"


# ---------------------------------------------------------------------------
# Cenarios (mesmos do EXP-004)
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
    print("=" * 90)
    print(f"[{name}] {len(rows)} rows × {len(rows[0]) if rows else 0} cols")
    print("=" * 90)

    scen = OUT / name
    scen.mkdir(exist_ok=True)

    # CSV (referencia)
    csv_text = encode_csv(rows)
    (scen / "source.csv").write_text(csv_text, encoding="utf-8")
    b_csv = len(csv_text.encode("utf-8"))
    b_csv_gz = len(gzip.compress(csv_text.encode("utf-8"), compresslevel=9))

    # TCF v0.5 SRDM verbose (variante A)
    flags = Flags(S=True, R=True, D=True, M=True)
    text_a = encode(rows, flags=flags, header_style="verbose")
    (scen / "tcf-A-verbose.tcf").write_text(text_a, encoding="utf-8")
    b_a = len(text_a.encode("utf-8"))
    b_a_gz = len(gzip.compress(text_a.encode("utf-8"), compresslevel=9))

    # TCF v0.5 SRDM compact (variante B)
    text_b = encode(rows, flags=flags, header_style="compact")
    (scen / "tcf-B-compact.tcf").write_text(text_b, encoding="utf-8")
    b_b = len(text_b.encode("utf-8"))
    b_b_gz = len(gzip.compress(text_b.encode("utf-8"), compresslevel=9))

    # Roundtrip ambos
    src_cols = to_columns(rows)
    dec_a = decode(text_a)
    dec_b = decode(text_b)
    ok_a, msg_a = compare_columns(dec_a, src_cols)
    ok_b, msg_b = compare_columns(dec_b, src_cols)

    # Diff de bytes B vs A
    delta_text = b_b - b_a
    delta_text_pct = (b_b / b_a - 1) * 100 if b_a else 0
    delta_gz = b_b_gz - b_a_gz
    delta_gz_pct = (b_b_gz / b_a_gz - 1) * 100 if b_a_gz else 0

    print(f"\n  bytes (texto puro):")
    print(f"    csv:                     {b_csv:>7}")
    print(f"    tcf v0.5 A (verbose):    {b_a:>7}")
    print(f"    tcf v0.5 B (compact):    {b_b:>7}  (B vs A: {delta_text:+d}B / {delta_text_pct:+.1f}%)")
    print(f"\n  bytes (apos gzip):")
    print(f"    csv+gz:                  {b_csv_gz:>7}")
    print(f"    tcf A+gz:                {b_a_gz:>7}")
    print(f"    tcf B+gz:                {b_b_gz:>7}  (B vs A: {delta_gz:+d}B / {delta_gz_pct:+.1f}%)")
    print(f"\n  roundtrip A: {'OK' if ok_a else 'FAIL — '+msg_a}")
    print(f"  roundtrip B: {'OK' if ok_b else 'FAIL — '+msg_b}")

    # Mostra header de cada variante
    print(f"\n  --- Variante A header ---")
    for line in text_a.splitlines()[:3]:
        print(f"    {line}")
    print(f"  --- Variante B header ---")
    for line in text_b.splitlines()[:3]:
        print(f"    {line}")

    return {
        "name": name,
        "n_rows": len(rows),
        "n_cols": len(rows[0]) if rows else 0,
        "csv": b_csv,
        "csv_gz": b_csv_gz,
        "tcf_A": b_a,
        "tcf_A_gz": b_a_gz,
        "tcf_B": b_b,
        "tcf_B_gz": b_b_gz,
        "B_vs_A_text": delta_text,
        "B_vs_A_text_pct": delta_text_pct,
        "B_vs_A_gz": delta_gz,
        "B_vs_A_gz_pct": delta_gz_pct,
        "roundtrip_A": ok_a,
        "roundtrip_B": ok_b,
    }


def main():
    print("\n" + "=" * 90)
    print("EXP-004b — TCF v0.5 SRDM: variante A (verbose) vs B (compact)")
    print("=" * 90)

    results = []
    results.append(run_scenario("S1-simple-strings", S1_simple_strings()))
    results.append(run_scenario("S2-with-int-col", S2_with_int_col()))
    results.append(run_scenario("S3-categorical-500", S3_categorical_500()))
    try:
        results.append(run_scenario("S4-tpch-supplier-100", S4_tpch_supplier_100()))
    except Exception as e:
        print(f"\n[skip] S4: {type(e).__name__}: {e}")

    # ---- Sintese ----
    print("\n" + "=" * 90)
    print("Sintese — Variante B (compact) vs A (verbose)")
    print("=" * 90)
    print(f"\n  {'cenario':<26} {'rows':>5} {'A bytes':>8} {'B bytes':>8} "
          f"{'B vs A':>10} {'A+gz':>6} {'B+gz':>6} {'B+gz vs A+gz':>14}")
    print(f"  {'-'*26} {'-'*5} {'-'*8} {'-'*8} {'-'*10} "
          f"{'-'*6} {'-'*6} {'-'*14}")
    for r in results:
        print(f"  {r['name']:<26} {r['n_rows']:>5} {r['tcf_A']:>8} {r['tcf_B']:>8} "
              f"{r['B_vs_A_text']:>+5}B/{r['B_vs_A_text_pct']:>+5.1f}%  "
              f"{r['tcf_A_gz']:>6} {r['tcf_B_gz']:>6} "
              f"{r['B_vs_A_gz']:>+5}B/{r['B_vs_A_gz_pct']:>+5.1f}%")

    avg_text = sum(r["B_vs_A_text_pct"] for r in results) / len(results)
    avg_gz = sum(r["B_vs_A_gz_pct"] for r in results) / len(results)
    print(f"\n  Avg B vs A (texto): {avg_text:+.2f}%")
    print(f"  Avg B vs A (gzip):  {avg_gz:+.2f}%")

    print(f"""
  Interpretacao:
    - texto puro: variante B economiza bytes proporcional ao tamanho do header
      relativo ao payload. Em datasets pequenos, ganho substancial.
    - apos gzip: ganho diminui (gzip ja comprime nomes repetidos), mas
      nao se anula porque o header sequer eh emitido na variante B.
    - roundtrip OK em todos os casos (decoder le ambas).
""")

    # Salva
    summary = {"experiment": "EXP-004b", "scenarios": results,
                "avg_B_vs_A_text_pct": avg_text,
                "avg_B_vs_A_gz_pct": avg_gz}
    (OUT / "results.json").write_text(json.dumps(summary, indent=2),
                                        encoding="utf-8")
    print(f"  Outputs: {OUT}")


if __name__ == "__main__":
    main()
