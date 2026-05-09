"""EXP-003a — Calibracao CSV + compressor generico.

Estabelece referencia base de quanto gzip/brotli/zstd ganham sobre
CSV em datasets variados. Pre-requisito para EXP-003b (HP-T1).

Uso:
    python run.py
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
sys.path.insert(0, str(ROOT / "experiments" / "lab"))

from framework.compressors import get_compressor, list_compressors

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
random.seed(42)


# ---------------------------------------------------------------------------
# Datasets — 5 perfis diferentes
# ---------------------------------------------------------------------------

def D_tpch_supplier_100() -> tuple[str, list[dict]]:
    """TPC-H supplier real, 100 rows."""
    from data_sources import load_dataset
    tables, _ = load_dataset("canonical:tpch-sf001",
                              volume=100, seed=42, schema=["supplier"])
    rows = tables.get("supplier", [])
    return "tpch-supplier-100", rows


def D_adult_1k() -> tuple[str, list[dict]]:
    """Adult Census, 1000 rows."""
    from data_sources import load_dataset
    tables, _ = load_dataset("canonical:adult-census",
                              volume=1000, seed=42, schema=["adult"])
    rows = tables.get("adult", [])
    return "adult-1k", rows


def D_categorical_heavy() -> tuple[str, list[dict]]:
    """Sintetico: muitas categoricas com repeticao."""
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
            "valor": round(random.uniform(10, 999), 2),
            "qtd": random.randint(1, 10),
            "ativo": random.choice([True, False]),
        })
    return "categorical-heavy", rows


def D_time_series() -> tuple[str, list[dict]]:
    """Sintetico: datas + valores numericos."""
    from datetime import date, timedelta
    base = date(2026, 1, 1)
    rows = []
    for i in range(500):
        d = base + timedelta(days=i)
        rows.append({
            "data": d.isoformat(),
            "temperatura": round(20 + random.gauss(0, 5), 1),
            "umidade": round(60 + random.gauss(0, 10), 1),
            "pressao": round(1013 + random.gauss(0, 5), 2),
            "vento": round(random.uniform(0, 30), 1),
        })
    return "time-series", rows


def D_mixed_relational() -> tuple[str, list[dict]]:
    """Sintetico: schema relacional simulado em 1 tabela (denormalizado)."""
    nomes = [f"Cliente_{i:03d}" for i in range(50)]
    produtos = [f"Prod-{i:03d}" for i in range(20)]
    rows = []
    for i in range(800):
        rows.append({
            "pedido_id": i + 1,
            "cliente_id": random.randint(1, 50),
            "cliente_nome": random.choice(nomes),
            "produto_id": random.randint(1, 20),
            "produto_nome": random.choice(produtos),
            "qtd": random.randint(1, 5),
            "valor_unit": round(random.uniform(5, 500), 2),
            "status": random.choice(["pago", "pendente", "cancelado"]),
        })
    return "mixed-relational", rows


# ---------------------------------------------------------------------------
# Encoder CSV (LF puro, sem bug)
# ---------------------------------------------------------------------------

def encode_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()),
                        lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_compress(comp_name: str, data: bytes) -> tuple[int, str]:
    """Tenta comprimir; retorna (bytes_finais, status)."""
    try:
        comp = get_compressor(comp_name)
        compressed = comp.compress(data, level=comp.default_level)
        return len(compressed), "ok"
    except ImportError as e:
        return -1, f"missing: {e}"
    except Exception as e:
        return -1, f"error: {type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 84)
    print("EXP-003a — Calibracao: CSV + compressor generico")
    print("=" * 84)

    datasets = [
        D_tpch_supplier_100,
        D_adult_1k,
        D_categorical_heavy,
        D_time_series,
        D_mixed_relational,
    ]

    compressors = ["none", "gzip", "brotli", "zstd"]

    print(f"\n  Compressores disponiveis: {list_compressors()}")
    print(f"  Datasets: {len(datasets)}")
    print()

    print(f"  {'dataset':<24} {'rows':>5} {'cols':>5} "
          f"{'csv':>8} {'gzip':>10} {'brotli':>10} {'zstd':>10}")
    print(f"  {'-'*24} {'-'*5} {'-'*5} "
          f"{'-'*8} {'-'*10} {'-'*10} {'-'*10}")

    results = []
    for ds_factory in datasets:
        try:
            name, rows = ds_factory()
        except Exception as e:
            print(f"  [skip] {ds_factory.__name__}: {type(e).__name__}: {e}")
            continue

        if not rows:
            print(f"  [skip] {name}: empty")
            continue

        n_rows = len(rows)
        n_cols = len(rows[0])
        csv_text = encode_csv(rows)
        csv_bytes = csv_text.encode("utf-8")
        b_csv = len(csv_bytes)

        row_data = {
            "dataset": name,
            "n_rows": n_rows,
            "n_cols": n_cols,
            "bytes_csv": b_csv,
            "compressors": {},
        }

        # Cabecalho
        line = f"  {name:<24} {n_rows:>5} {n_cols:>5} {b_csv:>8}"

        for comp_name in compressors:
            if comp_name == "none":
                continue
            b_comp, status = safe_compress(comp_name, csv_bytes)
            if b_comp > 0:
                ratio = b_comp / b_csv
                gain_pct = (1 - ratio) * 100
                line += f"  {b_comp:>5}/{gain_pct:>3.0f}%"
                row_data["compressors"][comp_name] = {
                    "bytes": b_comp,
                    "ratio": ratio,
                    "gain_pct": gain_pct,
                    "status": "ok",
                }
            else:
                line += f"  {'(skip)':>10}"
                row_data["compressors"][comp_name] = {
                    "bytes": None,
                    "status": status,
                }

        print(line)
        results.append(row_data)

        # Salva CSV original para referencia
        (RESULTS / f"{name}-csv.csv").write_bytes(csv_bytes)

    # ---- Sintese ----
    print("\n" + "=" * 84)
    print("Sintese: ganho medio por compressor")
    print("=" * 84)

    for comp_name in ["gzip", "brotli", "zstd"]:
        gains = []
        for r in results:
            c = r["compressors"].get(comp_name, {})
            if c.get("status") == "ok":
                gains.append(c["gain_pct"])
        if gains:
            avg = sum(gains) / len(gains)
            mn = min(gains)
            mx = max(gains)
            print(f"  {comp_name:<10}  N={len(gains)}  "
                  f"min={mn:.0f}%  avg={avg:.0f}%  max={mx:.0f}%")
        else:
            print(f"  {comp_name:<10}  (nao instalado ou todos falharam)")

    # ---- Conclusao ----
    print("\n" + "=" * 84)
    print("Avaliacao do criterio de pivot")
    print("=" * 84)
    gzip_gains = [r["compressors"].get("gzip", {}).get("gain_pct")
                   for r in results
                   if r["compressors"].get("gzip", {}).get("status") == "ok"]
    if gzip_gains:
        avg_gzip = sum(gzip_gains) / len(gzip_gains)
        if avg_gzip < 5:
            print(f"  gzip ganho medio: {avg_gzip:.1f}% — BAIXO")
            print(f"  PIVOT: revisar datasets, talvez muito pequenos/aleatorios")
        elif avg_gzip > 50:
            print(f"  gzip ganho medio: {avg_gzip:.1f}% — ALTO")
            print(f"  HP-T1 fica decisiva: TCF precisa MUITO superar gzip")
        else:
            print(f"  gzip ganho medio: {avg_gzip:.1f}% — INTERMEDIARIO")
            print(f"  Continuar para EXP-003b normalmente")

    # ---- Salva resultados em JSON ----
    out = {
        "experiment": "EXP-003a-calibration",
        "datasets": results,
    }
    (RESULTS / "results.json").write_text(json.dumps(out, indent=2),
                                            encoding="utf-8")
    print(f"\n  Arquivos: {RESULTS}")
    print(f"  results.json reproduzivel salvo")


if __name__ == "__main__":
    main()
