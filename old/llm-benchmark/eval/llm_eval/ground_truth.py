"""Ground truth computation — always derived from source CSVs, never hardcoded.

Usage:
    from llm_eval.ground_truth import compute, VL_LIST

    gt = compute(Path("data/"))
    print(gt["sum_vl"])   # 217.55
"""

from __future__ import annotations
import csv
from collections import Counter
from pathlib import Path
from typing import Any


def _load(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def compute(data_dir: Path) -> dict[str, Any]:
    """Compute all ground truth values from source CSVs.

    Returns a flat dict of question_key → expected_value.
    All float values rounded to 4 decimal places.
    """
    pessoas  = {r["id"]: r["nome"] for r in _load(data_dir / "pessoas.csv")}
    produtos = {r["id"]: r["nome"] for r in _load(data_dir / "produtos.csv")}
    vendas   = _load(data_dir / "vendas.csv")

    vl = [float(r["vl"]) for r in vendas]
    n  = len(vendas)

    # ── Aggregates on vl ──────────────────────────────────────────────
    sum_vl  = round(sum(vl), 4)
    avg_vl  = round(sum_vl / n, 4)
    max_vl  = max(vl)
    min_vl  = min(vl)

    # ── Count/filter by pessoa name ───────────────────────────────────
    count_by_pessoa: dict[str, int] = {}
    sum_by_pessoa:   dict[str, float] = {}
    for r in vendas:
        nome = pessoas.get(r["id_pessoa"], r["id_pessoa"])
        count_by_pessoa[nome] = count_by_pessoa.get(nome, 0) + 1
        sum_by_pessoa[nome]   = round(sum_by_pessoa.get(nome, 0.0) + float(r["vl"]), 4)

    # ── Produto frequency ─────────────────────────────────────────────
    prod_counter = Counter(r["id_produto"] for r in vendas)
    top_prod_id, top_prod_count = prod_counter.most_common(1)[0]
    top_prod_name = produtos.get(top_prod_id, top_prod_id)

    # ── Distinct people who bought ────────────────────────────────────
    distinct_pessoas = len({r["id_pessoa"] for r in vendas})

    # ── Top spender ───────────────────────────────────────────────────
    top_spender_name = max(sum_by_pessoa, key=sum_by_pessoa.__getitem__)
    top_spender_total = sum_by_pessoa[top_spender_name]

    return {
        # Layer 0 / Layer 2 — arithmetic aggregates
        "sum_vl":   sum_vl,
        "avg_vl":   avg_vl,
        "max_vl":   max_vl,
        "min_vl":   min_vl,
        "count":    n,

        # Layer 2 — FK-dependent (scalar lookups for specific question templates)
        "count_by_pessoa":  count_by_pessoa,   # {"Ana": 3, "Bruno": 2, ...} full dict
        "sum_by_pessoa":    sum_by_pessoa,      # {"Ana": 8.7, ...} full dict
        "count_ana":  count_by_pessoa.get("Ana", 0),   # scalar for q6
        "sum_ana":    sum_by_pessoa.get("Ana", 0.0),   # scalar for q7
        "top_product_name": top_prod_name,      # "Caneta"
        "top_product_id":   top_prod_id,        # "22"
        "top_product_count": top_prod_count,    # 5
        "count_distinct_pessoa": distinct_pessoas,  # 27
        "top_spender_name":  top_spender_name,
        "top_spender_total": top_spender_total,

        # Layer 1 — decode reference
        "vl_values": vl,        # ordered list of 41 floats
        "vl_sum":    sum_vl,    # alias — used by score_decode
    }


def vl_plain_list(data_dir: Path) -> str:
    """Return space-separated vl values for math_control prompts."""
    vendas = _load(data_dir / "vendas.csv")
    return " ".join(r["vl"] for r in vendas)
