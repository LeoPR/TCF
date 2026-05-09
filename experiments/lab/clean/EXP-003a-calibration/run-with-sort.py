"""EXP-003a (extensao) — CSV naive vs CSV ordenado + gzip.

Pergunta: o sort sozinho (sem qualquer formato TCF) ja da vantagem
para gzip? Ou seja, a economia que vimos em TCF compact/smart vem
do sort ou do formato colunar?

Testa em cada dataset:
  1. CSV naive (ordem original) + gzip
  2. CSV sorted (por coluna com cardinality baixa) + gzip

Heuristica do sort: escolhe coluna com `cardinality < N/2` que reduz
mais runs (igual best_sort_col do EXP-003b).
"""
from __future__ import annotations
import csv
import io
import gzip
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "eval"))

from data_sources import load_dataset

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
random.seed(42)


# ---------------------------------------------------------------------------
# Mesmos 5 datasets do run.py
# ---------------------------------------------------------------------------

def get_datasets():
    out = []

    tables, _ = load_dataset("canonical:tpch-sf001",
                              volume=100, seed=42, schema=["supplier"])
    out.append(("tpch-supplier-100", tables.get("supplier", [])))

    tables, _ = load_dataset("canonical:adult-census",
                              volume=1000, seed=42, schema=["adult"])
    out.append(("adult-1k", tables.get("adult", [])))

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
    out.append(("categorical-heavy", rows))

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
    out.append(("time-series", rows))

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
    out.append(("mixed-relational", rows))

    return out


# ---------------------------------------------------------------------------
# Encoders
# ---------------------------------------------------------------------------

def encode_csv(rows):
    if not rows:
        return ""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()),
                        lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def count_runs(values):
    if not values:
        return 0
    runs = 1
    for i in range(1, len(values)):
        if values[i] != values[i - 1]:
            runs += 1
    return runs


def best_sort_col(rows):
    """Coluna com cardinality < N/2 que mais reduz runs."""
    if not rows:
        return None
    n = len(rows)
    candidates = []
    for col in rows[0].keys():
        values = [str(r[col]) for r in rows]
        cardinality = len(set(values))
        if cardinality > n / 2 or cardinality < 2:
            continue
        sorted_runs = count_runs(sorted(values))
        unsorted_runs = count_runs(values)
        gain = unsorted_runs - sorted_runs
        candidates.append((col, gain, cardinality))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[1], x[2]))
    return candidates[0][0]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 92)
    print("EXP-003a (extensao) — CSV naive vs CSV ordenado + gzip")
    print("=" * 92)

    print(f"\n  {'dataset':<24} {'sort_by':<14} {'csv':>7} {'csv+gz':>8} "
          f"{'csv-srt':>8} {'srt+gz':>8} "
          f"{'srt vs naive':>13} {'srt+gz vs csv+gz':>17}")
    print(f"  {'-'*24} {'-'*14} {'-'*7} {'-'*8} {'-'*8} {'-'*8} "
          f"{'-'*13} {'-'*17}")

    results = []
    for name, rows in get_datasets():
        if not rows:
            continue

        sort_col = best_sort_col(rows)
        if sort_col is None:
            sort_col_disp = "(none)"
            rows_sorted = rows
        else:
            sort_col_disp = sort_col
            rows_sorted = sorted(rows, key=lambda r: str(r[sort_col]))

        text_naive = encode_csv(rows)
        text_sorted = encode_csv(rows_sorted)

        b_naive = len(text_naive.encode("utf-8"))
        b_sorted = len(text_sorted.encode("utf-8"))

        gz_naive = len(gzip.compress(text_naive.encode("utf-8"), compresslevel=9))
        gz_sorted = len(gzip.compress(text_sorted.encode("utf-8"), compresslevel=9))

        diff_text = (b_sorted / b_naive - 1) * 100
        diff_gz = (gz_sorted / gz_naive - 1) * 100

        sign1 = "+" if diff_text >= 0 else ""
        sign2 = "+" if diff_gz >= 0 else ""

        print(f"  {name:<24} {sort_col_disp:<14} {b_naive:>7} {gz_naive:>8} "
              f"{b_sorted:>8} {gz_sorted:>8} "
              f"{sign1}{diff_text:>+11.2f}% {sign2}{diff_gz:>+15.2f}%")

        # Salva csv sorted no disco para inspecao
        (RESULTS / f"{name}-csv-sorted.csv").write_text(text_sorted, encoding="utf-8")
        (RESULTS / f"{name}-csv-sorted.csv.gz").write_bytes(
            gzip.compress(text_sorted.encode("utf-8"), compresslevel=9))

        results.append({
            "dataset": name,
            "sort_col": sort_col,
            "bytes_csv_naive": b_naive,
            "bytes_csv_sorted": b_sorted,
            "bytes_csv_naive_gz": gz_naive,
            "bytes_csv_sorted_gz": gz_sorted,
            "diff_text_pct": diff_text,
            "diff_gz_pct": diff_gz,
        })

    # ---- Sintese ----
    print("\n" + "=" * 92)
    print("Sintese")
    print("=" * 92)

    avg_text = sum(r["diff_text_pct"] for r in results) / len(results)
    avg_gz = sum(r["diff_gz_pct"] for r in results) / len(results)

    print(f"\n  CSV ordenado vs CSV naive (texto puro):  avg={avg_text:+.2f}%")
    print(f"  Apos gzip:                                avg={avg_gz:+.2f}%")
    print()

    print("  Interpretacao:")
    print("    - texto puro: idem bytes (sort nao muda tamanho do CSV)")
    print("    - apos gzip: sort cria runs contiguos -> gzip aproveita")
    print()

    # ---- Implicacao para HP-T1 ----
    print("=" * 92)
    print("Implicacao para HP-T1 (revisita)")
    print("=" * 92)
    print()
    print("  Compara com resultados do EXP-003b:")
    print()
    print(f"  {'dataset':<24} {'csv-srt+gz':>12} {'compact+gz':>12} "
          f"{'smart+gz':>12} {'srt~comp?':>12} {'srt~smart?':>12}")
    print(f"  {'-'*24} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")

    # Le results do EXP-003b se existir
    exp_003b_path = HERE.parent / "EXP-003b-tcf-vs-gzip" / "results" / "results.json"
    if exp_003b_path.exists():
        exp_003b = json.loads(exp_003b_path.read_text(encoding="utf-8"))
        b003b = {r["dataset"]: r["bytes"] for r in exp_003b["results"]}

        for r in results:
            ds = r["dataset"]
            if ds not in b003b:
                continue
            srt_gz = r["bytes_csv_sorted_gz"]
            comp_gz = b003b[ds]["tcf_compact_gz"]
            smart_gz = b003b[ds]["tcf_smart_gz"]
            srt_vs_comp = (srt_gz / comp_gz - 1) * 100
            srt_vs_smart = (srt_gz / smart_gz - 1) * 100
            sign1 = "+" if srt_vs_comp >= 0 else ""
            sign2 = "+" if srt_vs_smart >= 0 else ""
            print(f"  {ds:<24} {srt_gz:>12} {comp_gz:>12} {smart_gz:>12} "
                  f"{sign1}{srt_vs_comp:>+10.1f}% {sign2}{srt_vs_smart:>+10.1f}%")
        print()
        print("  Se 'srt~comp' proximo de 0%: sort SOZINHO ja iguala TCF compact")
        print("    -> overhead estrutural do TCF compact eh quase irrelevante")
        print("  Se 'srt~smart' proximo de 0%: sort SOZINHO ja iguala TCF smart")
        print("    -> Propostas E/H/I nao agregam mais que sort + gzip puro")
    else:
        print("  (run EXP-003b primeiro para comparativo completo)")

    # ---- Salva ----
    out = {
        "experiment": "EXP-003a-extension-csv-sorted",
        "results": results,
        "summary": {
            "avg_diff_text_pct": avg_text,
            "avg_diff_gz_pct": avg_gz,
        },
    }
    (RESULTS / "results-with-sort.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(f"\n  Resultados: {RESULTS / 'results-with-sort.json'}")


if __name__ == "__main__":
    main()
