"""Synthetic data generators v2 — realistic distributions and types.

============================================================================
**STATUS: LEGACY / POOR-REFERENCE**

Este modulo gera dados sinteticos minimalistas (Ana, Bruno, Caneta) que
foram usados como baseline nos experimentos preliminares do projeto
(findings F30-F103 registrados em docs/article/07-results.md).

Em 2026-04-10 decidimos usar DATASETS CANONICOS como base principal:
  - TPC-H SF=0.01        (datasets/canonical/tpch-sf001/)
  - Adult Census (UCI)   (datasets/canonical/adult-census/)

Este arquivo continua existindo porque:
  1. E usado pelos tests existentes (roundtrip, compression benchmark)
  2. E comparacao com papers que usam dados "pobres" similares
  3. Preserva a historia dos experimentos legacy

**NAO use este modulo para novos experimentos cientificos.**
Use os datasets canonicos via `scripts/dataset_reader.py`.

Ver: docs/research-notes/2026-04-10-critical-review.md
     datasets/poor-reference/retail-sales-synthetic/README.md
============================================================================

Improvements over v1:
  - Realistic cardinality ratios (customer:order 1:5-1:20, inspired by TPC-H)
  - Date column (essential: ~10% of enterprise data)
  - Quantity and unit price separate (more realistic than single vl)
  - Boolean column (active/inactive status)
  - Nullable values (missing data, ~5% null rate)
  - Zipf distribution verified (s=1.0 for customers, s=0.7 for products)
  - Configurable type mix to test different data profiles

Generators:
  retail_sales  — e-commerce with realistic ratios and types
  sensor_logs   — IoT time-series with high repetition
  survey_wide   — many columns, Likert scale, sparse

Returns (tables, metadata) compatible with _write_fixture() and encode().

References:
  Gray et al. (1994) "Quickly Generating Billion-Record Synthetic Databases"
  TPC-H schema: customer:order 1:10, order:lineitem 1:4
"""

from __future__ import annotations
import random
from datetime import date, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Name pools (expanded)
# ---------------------------------------------------------------------------

_NAMES = [
    "Ana", "Bruno", "Carla", "Diego", "Elisa", "Felipe", "Gabriela",
    "Henrique", "Isabela", "Joao", "Karen", "Lucas", "Mariana", "Nicolas",
    "Paula", "Rafael", "Sofia", "Thiago", "Vitoria", "William",
    "Alice", "Bernardo", "Camila", "Daniel", "Eduarda", "Fernando",
    "Giovana", "Hugo", "Iris", "Jorge", "Larissa", "Mateus",
    "Natalia", "Oscar", "Patricia", "Ricardo", "Sandra", "Tomas",
    "Ursula", "Vinicius", "Xavier", "Yasmin", "Zeca", "Adriana",
    "Beatriz", "Cesar", "Debora", "Emanuel", "Flavia", "Guilherme",
    "Amanda", "Roberto", "Juliana", "Pedro", "Renata", "Gustavo",
    "Fernanda", "Marcos", "Tatiana", "Andre", "Monica", "Paulo",
    "Cristina", "Sergio", "Angela", "Rodrigo", "Lucia", "Marcelo",
    "Simone", "Carlos", "Vanessa", "Eduardo", "Priscila", "Leonardo",
]

_PRODUCTS = [
    "Caneta", "Caderno", "Borracha", "Lapis", "Marca-texto",
    "Apontador", "Regua", "Cola", "Tesoura", "Grampeador",
    "Clips", "Post-it", "Pasta", "Envelope", "Fita-adesiva",
    "Calculadora", "Agenda", "Bloco-notas", "Carimbo", "Perfurador",
    "Fichario", "Elastico", "Barbante", "Etiqueta", "Papel-A4",
    "Toner", "Cartucho", "Mouse", "Teclado", "Monitor",
    "Impressora", "Mochila", "Estojo", "Lapiseira", "Pincel",
    "Quadro-branco", "Apagador", "Giz", "Livro", "Dicionario",
]

_CATEGORIES = [
    "Escritorio", "Escolar", "Informatica", "Papelaria", "Organizacao",
]

_CITIES = [
    "Sao Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba",
    "Porto Alegre", "Salvador", "Brasilia", "Fortaleza",
    "Recife", "Manaus", "Goiania", "Campinas",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _zipf_weights(n: int, s: float = 1.0) -> list[float]:
    """Zipf distribution weights: frequency ~ 1/rank^s."""
    return [1.0 / (i + 1) ** s for i in range(n)]


def _gen_dates(rng: random.Random, n: int, start: str = "2024-01-01",
               end: str = "2024-12-31") -> list[str]:
    """Generate n random dates between start and end."""
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end)
    delta = (d1 - d0).days
    return [(d0 + timedelta(days=rng.randint(0, delta))).isoformat() for _ in range(n)]


# ---------------------------------------------------------------------------
# Retail Sales — realistic e-commerce (inspired by TPC-H)
# ---------------------------------------------------------------------------

def retail_sales(
    n_orders: int = 200,
    n_customers: int | None = None,
    n_products: int = 20,
    items_per_order: tuple[int, int] = (1, 4),
    seed: int = 42,
    null_rate: float = 0.05,
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Realistic retail sales dataset.

    Ratios (inspired by TPC-H):
      customers = n_orders / 10 (default, ~1:10 ratio)
      items per order = 1-4 (default)

    Tables: clientes(id, nome, cidade, ativo),
            produtos(id, nome, categoria, preco),
            vendas(id_cliente, id_produto, dt, qtd, preco_unit, total)
    """
    rng = random.Random(seed)

    if n_customers is None:
        n_customers = max(5, n_orders // 10)

    # --- Customers ---
    names = list(_NAMES)
    if n_customers > len(names):
        for i in range(n_customers - len(names)):
            names.append(f"{rng.choice(_NAMES[:20])}-{i + 1}")
    rng.shuffle(names)

    clientes = []
    for i in range(n_customers):
        ativo = "true" if rng.random() > 0.15 else "false"
        cidade = rng.choice(_CITIES)
        clientes.append({
            "id": str(i + 1),
            "nome": names[i],
            "cidade": cidade,
            "ativo": ativo,
        })

    # --- Products ---
    prods = list(_PRODUCTS)
    if n_products > len(prods):
        for i in range(n_products - len(prods)):
            prods.append(f"Produto-{i + 1}")
    rng.shuffle(prods)

    produtos = []
    for i in range(n_products):
        cat = rng.choice(_CATEGORIES)
        preco = round(rng.uniform(0.50, 80.00), 2)
        produtos.append({
            "id": str(100 + i),
            "nome": prods[i],
            "categoria": cat,
            "preco": str(preco),
        })

    # --- Orders/Items ---
    customer_weights = _zipf_weights(n_customers, s=1.0)
    product_weights = _zipf_weights(n_products, s=0.7)
    dates = _gen_dates(rng, n_orders)

    vendas = []
    for order_idx in range(n_orders):
        cid = rng.choices([c["id"] for c in clientes], weights=customer_weights, k=1)[0]
        n_items = rng.randint(*items_per_order)
        dt = dates[order_idx]

        for _ in range(n_items):
            pid = rng.choices([p["id"] for p in produtos], weights=product_weights, k=1)[0]
            preco_unit = float(next(p["preco"] for p in produtos if p["id"] == pid))
            qtd = rng.randint(1, 10)
            total = round(preco_unit * qtd * rng.uniform(0.95, 1.05), 2)

            row: dict[str, str] = {
                "id_cliente": cid,
                "id_produto": pid,
                "dt": dt,
                "qtd": str(qtd),
                "preco_unit": str(preco_unit),
                "total": str(total),
            }

            # Nullable: randomly null out some non-essential fields
            if rng.random() < null_rate:
                row["preco_unit"] = ""

            vendas.append(row)

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


# ---------------------------------------------------------------------------
# Sensor Logs — IoT time-series (high repetition)
# ---------------------------------------------------------------------------

def sensor_logs(
    n_readings: int = 1000,
    n_sensors: int = 10,
    seed: int = 42,
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """IoT sensor readings — very high repetition on sensor_id and status.

    Tables: sensores(id, tipo, localizacao),
            leituras(id_sensor, dt, valor, status)
    """
    rng = random.Random(seed)

    tipos = ["temperatura", "umidade", "pressao", "luminosidade", "vibracao"]
    locais = ["Sala-A", "Sala-B", "Deposito", "Externo", "Laboratorio"]
    status_opts = ["OK", "WARN", "ERROR"]
    status_weights = [80, 15, 5]

    sensores = []
    for i in range(n_sensors):
        sensores.append({
            "id": str(i + 1),
            "tipo": tipos[i % len(tipos)],
            "localizacao": locais[i % len(locais)],
        })

    dates = _gen_dates(rng, n_readings)
    sensor_weights = _zipf_weights(n_sensors, s=0.5)

    leituras = []
    for i in range(n_readings):
        sid = rng.choices([s["id"] for s in sensores], weights=sensor_weights, k=1)[0]
        tipo = next(s["tipo"] for s in sensores if s["id"] == sid)
        base = {"temperatura": 22, "umidade": 60, "pressao": 1013, "luminosidade": 500, "vibracao": 0.5}
        valor = round(base.get(tipo, 50) + rng.gauss(0, 5), 2)
        status = rng.choices(status_opts, weights=status_weights, k=1)[0]

        leituras.append({
            "id_sensor": sid,
            "dt": dates[i],
            "valor": str(valor),
            "status": status,
        })

    tables = {"sensores": sensores, "leituras": leituras}
    metadata = {
        "sensores": "sensores.csv#id",
        "leituras": "leituras.csv#sensores=id_sensor",
    }
    return tables, metadata


# ---------------------------------------------------------------------------
# Survey Wide — many columns, Likert, sparse
# ---------------------------------------------------------------------------

def survey_wide(
    n_respondents: int = 100,
    n_questions: int = 20,
    seed: int = 42,
    null_rate: float = 0.10,
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Wide survey dataset — many columns, Likert 1-5, sparse.

    Tables: respondentes(id, nome, faixa_etaria),
            respostas (one row per respondent, columns q1..qN)
    """
    rng = random.Random(seed)

    faixas = ["18-25", "26-35", "36-45", "46-55", "56+"]
    faixa_weights = [15, 30, 25, 20, 10]

    respondentes = []
    names = list(_NAMES)
    rng.shuffle(names)
    for i in range(n_respondents):
        nm = names[i % len(names)]
        if i >= len(names):
            nm = f"{nm}-{i // len(names)}"
        respondentes.append({
            "id": str(i + 1),
            "nome": nm,
            "faixa_etaria": rng.choices(faixas, weights=faixa_weights, k=1)[0],
        })

    # Normal-ish Likert distribution (center-biased)
    likert_weights = [5, 15, 25, 35, 20]

    respostas = []
    for resp in respondentes:
        row: dict[str, str] = {"id_respondente": resp["id"]}
        for q in range(1, n_questions + 1):
            if rng.random() < null_rate:
                row[f"q{q}"] = ""
            else:
                row[f"q{q}"] = rng.choices(["1", "2", "3", "4", "5"], weights=likert_weights, k=1)[0]
        respostas.append(row)

    tables = {"respondentes": respondentes, "respostas": respostas}
    metadata = {
        "respondentes": "respondentes.csv#id",
        "respostas": "respostas.csv#respondentes=id_respondente",
    }
    return tables, metadata
