"""Dataset loaders para o lab.

Cada dataset retorna list[dict] com tipos nativos Python (nao str).
"""
from __future__ import annotations
from typing import Callable


# ---------------------------------------------------------------------------
# MICRO — 5 linhas, 4 colunas, mistura de tipos
# Para validar pipeline e ver overhead constante
# ---------------------------------------------------------------------------

def load_micro() -> list[dict]:
    """5 rows, 4 cols (id INT, name STR, age INT, active BOOL).

    Inclui repeticoes (age=30 aparece 2x, active=True 3x) para RLE
    acionar quando encoder suporta.
    """
    return [
        {"id": 1, "name": "Alice", "age": 30, "active": True},
        {"id": 2, "name": "Bob",   "age": 25, "active": False},
        {"id": 3, "name": "Carol", "age": 31, "active": True},
        {"id": 4, "name": "David", "age": 25, "active": True},
        {"id": 5, "name": "Eve",   "age": 30, "active": False},
    ]


# ---------------------------------------------------------------------------
# SMALL — 20 linhas, 5 colunas — variacao MICRO + mais variabilidade
# ---------------------------------------------------------------------------

def load_small() -> list[dict]:
    """20 rows, 5 cols com mais variabilidade que MICRO."""
    return [
        {"id": i, "region": ["N","S","E","W"][i % 4],
         "value": i * 1.5, "qty": (i % 3) + 1,
         "tag": ["alpha","beta","gamma"][i % 3]}
        for i in range(1, 21)
    ]


# ---------------------------------------------------------------------------
# CATEGORICAL_HEAVY — 100 linhas, dominado por categoricos low-cardinality
# Cenario MAX para TCF (RLE+DICT brilham)
# ---------------------------------------------------------------------------

def load_categorical_heavy() -> list[dict]:
    """100 rows com 6 cols, dominantemente categoricos low-card.

    Distribuicao tipo Adult Census (sem precisar baixar).
    """
    import random
    rng = random.Random(42)  # deterministico
    sex_choices = ["M", "F"]
    workclass = ["Private", "Self-emp", "Gov", "Without-pay"]
    edu = ["HS-grad", "Some-college", "Bachelors", "Masters", "Doctorate"]
    classes = ["<=50K", ">50K"]

    rows = []
    for i in range(100):
        rows.append({
            "id": i + 1,
            "age": rng.randint(20, 65),
            "sex": sex_choices[rng.randint(0, 1)] if rng.random() > 0.4 else "M",
            "workclass": workclass[rng.randint(0, 3)],
            "education": edu[rng.randint(0, 4)],
            # 76% baixa renda, 24% alta — espelha Adult Census
            "class": classes[0] if rng.random() < 0.76 else classes[1],
        })
    return rows


# ---------------------------------------------------------------------------
# WIDE_RANDOM — adverso para TCF (sem repeticao para RLE explorar)
# ---------------------------------------------------------------------------

def load_wide_random() -> list[dict]:
    """100 rows × 10 cols com valores aleatorios float — adverso para TCF."""
    import random
    rng = random.Random(42)
    return [
        {f"col_{j}": round(rng.gauss(50, 15), 3) for j in range(10)} | {"id": i}
        for i in range(1, 101)
    ]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

DATASETS: dict[str, Callable[[], list[dict]]] = {
    "micro": load_micro,
    "small": load_small,
    "categorical_heavy": load_categorical_heavy,
    "wide_random": load_wide_random,
}


def load_dataset(name: str) -> list[dict]:
    """Carrega um dataset pelo nome registrado."""
    if name not in DATASETS:
        raise ValueError(f"Unknown dataset {name!r}. Available: {sorted(DATASETS)}")
    return DATASETS[name]()


def describe(name: str) -> dict:
    """Retorna metadata sobre um dataset (n_rows, n_cols, types)."""
    rows = load_dataset(name)
    if not rows:
        return {"name": name, "n_rows": 0, "n_cols": 0}
    cols = list(rows[0].keys())
    types = {c: type(rows[0][c]).__name__ for c in cols}
    return {
        "name": name,
        "n_rows": len(rows),
        "n_cols": len(cols),
        "columns": cols,
        "types": types,
    }
