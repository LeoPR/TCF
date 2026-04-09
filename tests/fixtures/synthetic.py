"""Synthetic data generators for compression benchmarks.

Each generator creates a realistic dataset with controlled parameters:
  - n_rows: number of transaction rows
  - n_fk_values: cardinality of FK columns (controls RLE potential)
  - seed: reproducibility

Returns (tables, metadata) ready for _write_fixture().

Datasets:
  crm_sales     — customers buy products (realistic e-commerce)
  service_logs  — status codes + categories (high FK repetition)
  survey        — Likert scale responses (very high value repetition)
  unique_ids    — all unique values (worst case for RLE)
"""

import random
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_FIRST_NAMES = [
    "Ana", "Bruno", "Carla", "Diego", "Elisa", "Felipe", "Gabriela",
    "Henrique", "Isabela", "Joao", "Karen", "Lucas", "Mariana", "Nicolas",
    "Paula", "Rafael", "Sofia", "Thiago", "Vitoria", "William",
    "Alice", "Bernardo", "Camila", "Daniel", "Eduarda", "Fernando",
    "Giovana", "Hugo", "Iris", "Jorge", "Larissa", "Mateus",
    "Natalia", "Oscar", "Patricia", "Ricardo", "Sandra", "Tomas",
    "Ursula", "Vinicius", "Xavier", "Yasmin", "Zeca", "Adriana",
    "Beatriz", "Cesar", "Debora", "Emanuel", "Flavia", "Guilherme",
]

_PRODUCTS = [
    "Caneta", "Caderno", "Borracha", "Lapis", "Marca-texto",
    "Apontador", "Regua", "Cola", "Tesoura", "Grampeador",
    "Clips", "Post-it", "Pasta", "Envelope", "Fita-adesiva",
    "Calculadora", "Agenda", "Bloco-notas", "Carimbo", "Perfurador",
    "Fichario", "Elastico", "Barbante", "Etiqueta", "Papel-A4",
    "Toner", "Cartucho", "Mouse", "Teclado", "Monitor",
]

_STATUS_CODES = ["OK", "WARN", "ERROR", "TIMEOUT", "RETRY"]

_CATEGORIES = [
    "Autenticacao", "Pagamento", "Consulta", "Relatorio",
    "Notificacao", "Sincronizacao", "Backup", "Importacao",
]

_LIKERT = ["1", "2", "3", "4", "5"]


def _pick_names(n: int, rng: random.Random) -> list[dict]:
    """Generate n unique person records."""
    names = list(_FIRST_NAMES)
    if n > len(names):
        # Generate extra names with suffixes
        extra = n - len(names)
        for i in range(extra):
            names.append(f"{rng.choice(_FIRST_NAMES)}{i+1}")
    rng.shuffle(names)
    return [{"id": str(i + 1), "nome": names[i]} for i in range(n)]


def _pick_products(n: int, rng: random.Random) -> list[dict]:
    """Generate n unique product records."""
    prods = list(_PRODUCTS)
    if n > len(prods):
        extra = n - len(prods)
        for i in range(extra):
            prods.append(f"Produto-{i+1}")
    rng.shuffle(prods)
    return [
        {
            "id": str(10 + i),
            "nome": prods[i],
            "preco_base": str(round(rng.uniform(0.50, 50.00), 2)),
        }
        for i in range(n)
    ]


# ─────────────────────────────────────────────────────────────────────────────
# CRM Sales — e-commerce style
# ─────────────────────────────────────────────────────────────────────────────

def crm_sales(
    n_rows: int = 200,
    n_customers: int = 20,
    n_products: int = 15,
    seed: int = 42,
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Simulated sales transactions.

    FK columns (id_cliente, id_produto) have controlled cardinality.
    More rows with fewer FK values = better RLE compression.
    """
    rng = random.Random(seed)

    clientes = _pick_names(n_customers, rng)
    produtos = _pick_products(n_products, rng)

    # Zipf-like distribution: some customers buy much more than others
    customer_weights = [1.0 / (i + 1) ** 0.8 for i in range(n_customers)]
    product_weights = [1.0 / (i + 1) ** 0.5 for i in range(n_products)]

    vendas = []
    for _ in range(n_rows):
        cid = rng.choices(
            [c["id"] for c in clientes], weights=customer_weights, k=1
        )[0]
        pid = rng.choices(
            [p["id"] for p in produtos], weights=product_weights, k=1
        )[0]
        base_price = float(next(p["preco_base"] for p in produtos if p["id"] == pid))
        qty = rng.randint(1, 5)
        vl = round(base_price * qty * rng.uniform(0.9, 1.1), 2)
        vendas.append({
            "id_cliente": cid,
            "id_produto": pid,
            "qtd": str(qty),
            "vl": str(vl),
        })

    tables = {
        "clientes": clientes,
        "produtos": produtos,
        "vendas": vendas,
    }
    metadata = {
        "clientes": "clientes.csv#id",
        "produtos": "produtos.csv#id",
        "vendas": "vendas.csv#clientes=id_cliente,produtos=id_produto",
    }
    return tables, metadata


# ─────────────────────────────────────────────────────────────────────────────
# Service Logs — high FK repetition
# ─────────────────────────────────────────────────────────────────────────────

def service_logs(
    n_rows: int = 500,
    seed: int = 42,
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Simulated service/API log entries.

    Very high repetition: only 5 status codes and 8 categories.
    Ideal for RLE compression.
    """
    rng = random.Random(seed)

    # Status distribution: OK dominates (realistic)
    status_weights = [60, 15, 10, 10, 5]  # OK, WARN, ERROR, TIMEOUT, RETRY

    logs = []
    for i in range(n_rows):
        status = rng.choices(_STATUS_CODES, weights=status_weights, k=1)[0]
        category = rng.choice(_CATEGORIES)
        duration_ms = round(rng.expovariate(1 / 200), 1)  # mean ~200ms
        logs.append({
            "status": status,
            "categoria": category,
            "duracao_ms": str(duration_ms),
        })

    tables = {"logs": logs}
    metadata = {"logs": "logs.csv"}
    return tables, metadata


# ─────────────────────────────────────────────────────────────────────────────
# Survey — Likert scale (extreme repetition)
# ─────────────────────────────────────────────────────────────────────────────

def survey_likert(
    n_respondents: int = 100,
    n_questions: int = 5,
    seed: int = 42,
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Simulated survey with Likert scale (1-5) responses.

    Each respondent answers all questions.
    Values are only 1-5 → extreme RLE potential on sorted columns.
    """
    rng = random.Random(seed)

    respondentes = _pick_names(n_respondents, rng)

    # Normal-ish distribution centered around 3-4
    likert_weights = [5, 15, 25, 35, 20]  # skewed towards 4

    respostas = []
    for resp in respondentes:
        for q in range(1, n_questions + 1):
            score = rng.choices(_LIKERT, weights=likert_weights, k=1)[0]
            respostas.append({
                "id_respondente": resp["id"],
                "pergunta": str(q),
                "nota": score,
            })

    tables = {
        "respondentes": respondentes,
        "respostas": respostas,
    }
    metadata = {
        "respondentes": "respondentes.csv#id",
        "respostas": "respostas.csv#respondentes=id_respondente",
    }
    return tables, metadata


# ─────────────────────────────────────────────────────────────────────────────
# Unique IDs — worst case for RLE
# ─────────────────────────────────────────────────────────────────────────────

def unique_data(
    n_rows: int = 200,
    seed: int = 42,
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Every value is unique — no repetition at all.

    Worst case for RLE: no compression possible.
    Control group to compare against high-repetition datasets.
    """
    rng = random.Random(seed)

    rows = []
    for i in range(n_rows):
        rows.append({
            "id": str(i + 1),
            "codigo": f"COD-{rng.randint(10000, 99999)}",
            "valor": str(round(rng.uniform(0.01, 999.99), 2)),
            "descricao": f"Item-{i+1}-{rng.randint(100,999)}",
        })

    tables = {"registros": rows}
    metadata = {"registros": "registros.csv#id"}
    return tables, metadata
