"""Roundtrip TCF v0.5: encode -> decode -> compara com fonte.

Para cada cenario:
  1. Carrega/sintetiza dados (fonte)
  2. Encoda em CSV (referencia visual)
  3. Encoda em TCF v0.5 SRDM
  4. Decoda TCF v0.5
  5. Compara dados decodados com fonte (roundtrip)
  6. Mostra outputs lado a lado e bytes

Saida: ./outputs-roundtrip/ com:
  {scenario}/source.json     dados originais
  {scenario}/source.csv      versao CSV (ref humana)
  {scenario}/encoded.tcf     output do encoder TCF v0.5
"""
from __future__ import annotations
import csv
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
OUT = HERE / "outputs-roundtrip"
OUT.mkdir(exist_ok=True)
random.seed(42)


def encode_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()),
                        lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def to_columns(rows: list[dict]) -> dict[str, list[str]]:
    if not rows:
        return {}
    cols = list(rows[0].keys())
    out = {c: [] for c in cols}
    for r in rows:
        for c in cols:
            out[c].append(str(r.get(c, "")))
    return out


def compare_columns(decoded: dict[str, list], source_cols: dict[str, list]) -> tuple[bool, str]:
    """Compara dois dicts coluna-a-coluna. Retorna (ok, mensagem)."""
    if set(decoded.keys()) != set(source_cols.keys()):
        return False, f"chaves diferentes: decoded={set(decoded.keys())} source={set(source_cols.keys())}"
    for c in source_cols:
        # Normaliza: sort por chaves (sort foi aplicado em TCF mas nao em fonte)
        # Para roundtrip robusto, comparamos como multiset de tuplas-de-row
        pass
    # Compara como multiset de tuplas (linhas)
    cols = list(source_cols.keys())
    n = len(source_cols[cols[0]])
    src_rows = sorted(tuple(source_cols[c][i] for c in cols) for i in range(n))
    dec_rows = sorted(tuple(decoded[c][i] for c in cols) for i in range(n))
    if src_rows != dec_rows:
        # Mostra primeira diferenca
        for i, (s, d) in enumerate(zip(src_rows, dec_rows)):
            if s != d:
                return False, f"linha {i}: source={s} != decoded={d}"
        return False, f"len diferente: {len(src_rows)} vs {len(dec_rows)}"
    return True, "ok"


# ---------------------------------------------------------------------------
# Cenarios
# ---------------------------------------------------------------------------

def S1_simple_strings():
    """6 rows, 2 colunas (uma string com repetições, outra string única)."""
    return [
        {"comprador": "Ana",    "produto": "Abacaxi"},
        {"comprador": "Bruno",  "produto": "Banana"},
        {"comprador": "Ana",    "produto": "Cereja"},
        {"comprador": "Carlos", "produto": "Abacaxi"},
        {"comprador": "Bruno",  "produto": "Banana"},
        {"comprador": "Ana",    "produto": "Banana"},
    ]


def S2_with_int_col():
    """Mesma S1 + coluna qty (int) para testar discrim marked auto."""
    return [
        {"comprador": "Ana",    "produto": "Abacaxi", "qty": 2},
        {"comprador": "Bruno",  "produto": "Banana",  "qty": 1},
        {"comprador": "Ana",    "produto": "Cereja",  "qty": 3},
        {"comprador": "Carlos", "produto": "Abacaxi", "qty": 1},
        {"comprador": "Bruno",  "produto": "Banana",  "qty": 2},
        {"comprador": "Ana",    "produto": "Banana",  "qty": 5},
    ]


def S3_categorical_500():
    """500 rows com categoricas que repetem muito."""
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
    """Real: TPC-H supplier 100 rows (via Shaper)."""
    from data_sources import load_dataset
    tables, _ = load_dataset("canonical:tpch-sf001",
                              volume=100, seed=42, schema=["supplier"])
    rows = tables.get("supplier", [])
    # Simplifica: poucas colunas
    return [{"s_suppkey": r["s_suppkey"],
             "s_name": r["s_name"][:20],
             "s_nationkey": r["s_nationkey"]} for r in rows]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_scenario(name: str, rows: list[dict], show_full_output: bool = False):
    print("=" * 84)
    print(f"[{name}] {len(rows)} rows × {len(rows[0]) if rows else 0} cols")
    print("=" * 84)

    scenario_dir = OUT / name
    scenario_dir.mkdir(exist_ok=True)

    # 1. Salva fonte
    (scenario_dir / "source.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    # 2. Salva CSV (ref humana)
    csv_text = encode_csv(rows)
    (scenario_dir / "source.csv").write_text(csv_text, encoding="utf-8")

    # 3. Encoda em TCF v0.5
    flags = Flags(S=True, R=True, D=True, M=True)
    tcf_text = encode(rows, flags=flags)
    (scenario_dir / "encoded.tcf").write_text(tcf_text, encoding="utf-8")

    # 4. Decoda
    try:
        decoded = decode(tcf_text)
        decode_ok = True
        decode_err = None
    except Exception as e:
        decoded = {}
        decode_ok = False
        decode_err = f"{type(e).__name__}: {e}"

    # 5. Compara
    if decode_ok:
        source_cols = to_columns(rows)
        rt_ok, rt_msg = compare_columns(decoded, source_cols)
    else:
        rt_ok, rt_msg = False, f"decode falhou: {decode_err}"

    # 6. Reporta
    b_csv = len(csv_text.encode("utf-8"))
    b_tcf = len(tcf_text.encode("utf-8"))
    delta_pct = (b_tcf / b_csv - 1) * 100 if b_csv else 0
    sign = "+" if delta_pct >= 0 else ""

    print(f"\n  bytes:")
    print(f"    csv:  {b_csv:>7}")
    print(f"    tcf:  {b_tcf:>7}  ({sign}{delta_pct:.1f}% vs csv)")
    print(f"\n  roundtrip: {'OK' if rt_ok else 'FAIL — ' + rt_msg}")

    # Mostra sample de output
    if show_full_output or len(rows) <= 10:
        print(f"\n  --- CSV (fonte) ---")
        for line in csv_text.splitlines()[:12]:
            print(f"    {line}")
        if len(csv_text.splitlines()) > 12:
            print(f"    ... ({len(csv_text.splitlines())-12} linhas a mais)")

        print(f"\n  --- TCF v0.5 (encoded) ---")
        for line in tcf_text.splitlines()[:25]:
            print(f"    {line}")
        if len(tcf_text.splitlines()) > 25:
            print(f"    ... ({len(tcf_text.splitlines())-25} linhas a mais)")
    else:
        # Apenas as primeiras N linhas do TCF
        print(f"\n  --- TCF v0.5 (primeiras 15 linhas) ---")
        for line in tcf_text.splitlines()[:15]:
            print(f"    {line}")
        print(f"    ... ({len(tcf_text.splitlines())-15} linhas a mais)")

    return {
        "name": name,
        "n_rows": len(rows),
        "n_cols": len(rows[0]) if rows else 0,
        "bytes_csv": b_csv,
        "bytes_tcf": b_tcf,
        "delta_pct": delta_pct,
        "roundtrip_ok": rt_ok,
        "roundtrip_msg": rt_msg,
    }


def main():
    print("\n" + "=" * 84)
    print("TCF v0.5 SRDM — Roundtrip + Visualizacao")
    print("=" * 84)

    results = []
    results.append(run_scenario("S1-simple-strings", S1_simple_strings(),
                                  show_full_output=True))
    results.append(run_scenario("S2-with-int-col", S2_with_int_col(),
                                  show_full_output=True))
    results.append(run_scenario("S3-categorical-500", S3_categorical_500()))
    try:
        results.append(run_scenario("S4-tpch-supplier-100", S4_tpch_supplier_100()))
    except Exception as e:
        print(f"\n[skip] S4 falhou: {type(e).__name__}: {e}")

    # ---- Sintese ----
    print("\n" + "=" * 84)
    print("Sintese")
    print("=" * 84)
    print(f"\n  {'cenario':<26} {'rows':>5} {'csv B':>7} {'tcf B':>7} "
          f"{'delta':>9} {'roundtrip':>10}")
    print(f"  {'-'*26} {'-'*5} {'-'*7} {'-'*7} {'-'*9} {'-'*10}")
    for r in results:
        sign = "+" if r["delta_pct"] >= 0 else ""
        rt = "OK" if r["roundtrip_ok"] else "FAIL"
        print(f"  {r['name']:<26} {r['n_rows']:>5} {r['bytes_csv']:>7} "
              f"{r['bytes_tcf']:>7} {sign}{r['delta_pct']:>+7.1f}% {rt:>10}")

    # ---- Salva ----
    summary = {"experiment": "EXP-004-roundtrip-v05", "scenarios": results}
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n  Outputs em: {OUT}")
    print(f"  Para inspecao manual: source.json + source.csv + encoded.tcf por cenario")


if __name__ == "__main__":
    main()
