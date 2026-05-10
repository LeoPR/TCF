"""EXP-006 — Flag P (Affix-DICT) em datasets com identificadores estruturados.

Compara TCF v0.5 SRDM vs SRDMP em 4 cenarios com prefixos claros:
  C1: codigo PED-NNNN (prefixo `PED-2026-`)
  C2: TPC-H supplier name (`Supplier#000000NNN`)
  C3: URLs com path comum (`https://api.example.com/v1/...`)
  C4: emails clusterizados (sufixo `@dominio.com` — espera nao ativar prefix)

Para cada:
  - SRDM (sem flag P)
  - SRDMP (com flag P, auto-detect prefix)
  - csv-naive + gzip (referencia)

Roundtrip OK em todos requerido.

Saida: ./outputs/<C>/ com fontes + variantes + .gz
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

from tcf.v05 import encode as tcf_encode, decode as tcf_decode, Flags

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)
random.seed(42)


def csv_encode(rows):
    if not rows:
        return ""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()),
                        lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def gz(text: str) -> bytes:
    return gzip.compress(text.encode("utf-8"), compresslevel=9)


def normalize(rows):
    if not rows:
        return []
    cols = list(rows[0].keys())
    return sorted(tuple(str(r.get(c, "")) for c in cols) for r in rows)


def roundtrip_tcf(rows, flags):
    text = tcf_encode(rows, flags=flags)
    decoded = tcf_decode(text)
    if not decoded:
        return False
    cols = list(decoded.keys())
    n = len(decoded[cols[0]])
    decoded_rows = [{c: decoded[c][i] for c in cols} for i in range(n)]
    return normalize(rows) == normalize(decoded_rows)


# ---------------------------------------------------------------------------
# Cenarios
# ---------------------------------------------------------------------------

def C1_codigo_PED():
    """100 codigos PED-2026-NNNN com prefixo claro."""
    return [
        {"codigo": f"PED-2026-{i:04d}",
         "valor": round(random.uniform(10, 999), 2),
         "status": random.choice(["pago", "pendente", "cancelado"])}
        for i in range(100)
    ]


def C2_tpch_supplier():
    """50 supplier do TPC-H (s_name = 'Supplier#NNNNNNNNN')."""
    from data_sources import load_dataset
    tables, _ = load_dataset("canonical:tpch-sf001",
                              volume=50, seed=42, schema=["supplier"])
    rows = tables.get("supplier", [])
    return [{"s_name": r["s_name"],
             "s_nationkey": r["s_nationkey"],
             "s_acctbal": r["s_acctbal"]} for r in rows]


def C3_urls():
    """80 URLs com prefixo de API comum."""
    base = "https://api.example.com/v1"
    return [
        {"endpoint": f"{base}/users/{i:03d}/profile",
         "metodo": random.choice(["GET", "POST", "PUT"]),
         "status_code": random.choice([200, 201, 404, 500])}
        for i in range(80)
    ]


def C4_emails():
    """100 emails em 2 dominios — espera afixo nao ativar (prefix nao eh comum)."""
    out = []
    for i in range(50):
        out.append({"email": f"user{i:03d}@gmail.com",
                     "ativo": random.choice(["true", "false"])})
    for i in range(50):
        out.append({"email": f"contact{i:03d}@company.com",
                     "ativo": random.choice(["true", "false"])})
    random.shuffle(out)
    return out


def C5_misturado():
    """Misto: codigo com prefixo + nome unico + categoria com repeticao."""
    cats = ["TIPO_A", "TIPO_B", "TIPO_C"]
    return [
        {"codigo": f"INV-2026-{i:05d}",
         "cliente_nome": f"Cliente_{random.randint(1,30):03d}",
         "categoria": random.choice(cats),
         "valor": round(random.uniform(100, 9999), 2)}
        for i in range(150)
    ]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_scenario(name: str, rows: list[dict]):
    print("=" * 92)
    print(f"[{name}] {len(rows)} rows × {len(rows[0]) if rows else 0} cols")
    print("=" * 92)

    out_dir = OUT / name
    out_dir.mkdir(exist_ok=True)

    csv_text = csv_encode(rows)
    (out_dir / "source.csv").write_text(csv_text, encoding="utf-8")
    b_csv = len(csv_text.encode("utf-8"))
    b_csv_gz = len(gz(csv_text))

    # SRDM (sem P)
    flags_srdm = Flags(S=True, R=True, D=True, M=True)
    text_srdm = tcf_encode(rows, flags=flags_srdm)
    (out_dir / "tcf-SRDM.tcf").write_text(text_srdm, encoding="utf-8")
    b_srdm = len(text_srdm.encode("utf-8"))
    b_srdm_gz = len(gz(text_srdm))

    # SRDMP (com P)
    flags_srdmp = Flags(S=True, R=True, D=True, M=True, P=True)
    text_srdmp = tcf_encode(rows, flags=flags_srdmp)
    (out_dir / "tcf-SRDMP.tcf").write_text(text_srdmp, encoding="utf-8")
    b_srdmp = len(text_srdmp.encode("utf-8"))
    b_srdmp_gz = len(gz(text_srdmp))

    # Roundtrip
    rt_srdm = roundtrip_tcf(rows, flags_srdm)
    rt_srdmp = roundtrip_tcf(rows, flags_srdmp)

    # Diffs
    p_vs_no_p = (b_srdmp / b_srdm - 1) * 100
    p_vs_no_p_gz = (b_srdmp_gz / b_srdm_gz - 1) * 100
    p_vs_csv = (b_srdmp / b_csv - 1) * 100
    p_vs_csv_gz = (b_srdmp_gz / b_csv_gz - 1) * 100

    print(f"\n  bytes:")
    print(f"    csv:           {b_csv:>7}     csv+gz: {b_csv_gz:>7}")
    print(f"    tcf SRDM:      {b_srdm:>7}     SRDM+gz: {b_srdm_gz:>7}")
    print(f"    tcf SRDMP:     {b_srdmp:>7}     SRDMP+gz: {b_srdmp_gz:>7}")
    print(f"\n  ganhos:")
    print(f"    SRDMP vs SRDM (texto):  {p_vs_no_p:+.1f}%")
    print(f"    SRDMP vs SRDM (gzip):   {p_vs_no_p_gz:+.1f}%")
    print(f"    SRDMP vs CSV (texto):   {p_vs_csv:+.1f}%")
    print(f"    SRDMP vs CSV (gzip):    {p_vs_csv_gz:+.1f}%")
    print(f"\n  roundtrip SRDM:  {'OK' if rt_srdm else 'FAIL'}")
    print(f"  roundtrip SRDMP: {'OK' if rt_srdmp else 'FAIL'}")

    # Mostra header da SRDMP (so pra ver afixos detectados)
    print(f"\n  --- SRDMP header (primeiras linhas) ---")
    for line in text_srdmp.splitlines()[:8]:
        print(f"    {line}")

    return {
        "name": name,
        "n_rows": len(rows),
        "n_cols": len(rows[0]) if rows else 0,
        "bytes": {
            "csv": b_csv, "csv_gz": b_csv_gz,
            "SRDM": b_srdm, "SRDM_gz": b_srdm_gz,
            "SRDMP": b_srdmp, "SRDMP_gz": b_srdmp_gz,
        },
        "P_vs_noP_text_pct": p_vs_no_p,
        "P_vs_noP_gz_pct": p_vs_no_p_gz,
        "P_vs_csv_text_pct": p_vs_csv,
        "P_vs_csv_gz_pct": p_vs_csv_gz,
        "roundtrip_SRDM": rt_srdm,
        "roundtrip_SRDMP": rt_srdmp,
    }


def main():
    print("\n" + "=" * 92)
    print("EXP-006 — Flag P (Affix-DICT) em identificadores estruturados")
    print("=" * 92)

    results = []
    results.append(run_scenario("C1-codigo-PED", C1_codigo_PED()))
    try:
        results.append(run_scenario("C2-tpch-supplier", C2_tpch_supplier()))
    except Exception as e:
        print(f"\n[skip C2] {type(e).__name__}: {e}")
    results.append(run_scenario("C3-urls", C3_urls()))
    results.append(run_scenario("C4-emails", C4_emails()))
    results.append(run_scenario("C5-misturado", C5_misturado()))

    # Sintese
    print("\n" + "=" * 92)
    print("Sintese — Flag P efeito")
    print("=" * 92)
    print(f"\n  {'cenario':<22} {'SRDM':>7} {'SRDMP':>7} {'P vs SRDM':>11} "
          f"{'SRDM+gz':>8} {'SRDMP+gz':>9} {'P+gz vs noP+gz':>15}")
    print(f"  {'-'*22} {'-'*7} {'-'*7} {'-'*11} {'-'*8} {'-'*9} {'-'*15}")
    for r in results:
        b = r["bytes"]
        print(f"  {r['name']:<22} {b['SRDM']:>7} {b['SRDMP']:>7} "
              f"{r['P_vs_noP_text_pct']:>+10.1f}% "
              f"{b['SRDM_gz']:>8} {b['SRDMP_gz']:>9} "
              f"{r['P_vs_noP_gz_pct']:>+14.1f}%")

    avg_text = sum(r["P_vs_noP_text_pct"] for r in results) / len(results)
    avg_gz = sum(r["P_vs_noP_gz_pct"] for r in results) / len(results)
    print(f"\n  Avg P vs SRDM (texto): {avg_text:+.2f}%")
    print(f"  Avg P vs SRDM (gzip):  {avg_gz:+.2f}%")

    # Salva
    summary = {"experiment": "EXP-006", "scenarios": results,
                "avg_P_vs_noP_text_pct": avg_text,
                "avg_P_vs_noP_gz_pct": avg_gz}
    (OUT / "results.json").write_text(json.dumps(summary, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
