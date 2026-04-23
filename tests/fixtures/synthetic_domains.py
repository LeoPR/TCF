"""Cross-domain synthetic fixtures for M3 generalization testing.

Mirrors the structure of `retail_sales` (2 dims + 1 fact with FK-by-name)
but in medical and financial domains. This lets M3 validate that H-TCF2
(schema-only prompt enables correct SQL generation) generalizes beyond
retail.

All fixtures return (tables, metadata) in the same format as
`retail_sales`, using string-encoded values for consistency with the
fixture framework.
"""
from __future__ import annotations
import random

from .synthetic_v2 import _NAMES, _zipf_weights, _gen_dates


# ---------------------------------------------------------------------------
# Medical domain
# ---------------------------------------------------------------------------

_ESPECIALIDADES = [
    "Clinica Geral", "Cardiologia", "Dermatologia", "Pediatria",
    "Ortopedia", "Ginecologia", "Psiquiatria", "Oftalmologia",
    "Endocrinologia", "Neurologia",
]

_GENEROS = ["F", "M", "O"]


def medical_consultations(
    n_orders: int = 200,
    n_customers: int | None = None,
    n_products: int = 20,
    items_per_order: tuple[int, int] = (1, 3),
    seed: int = 42,
    null_rate: float = 0.05,
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Medical consultations dataset.

    Tables: pacientes(id, nome, idade, genero),
            medicos(id, nome, especialidade, sala),
            consultas(id_paciente, id_medico, dt, duracao_min, custo)
    """
    rng = random.Random(seed)

    if n_customers is None:
        n_customers = max(5, n_orders // 10)

    # Pacientes
    names = list(_NAMES)
    if n_customers > len(names):
        for i in range(n_customers - len(names)):
            names.append(f"{rng.choice(_NAMES[:20])}-{i + 1}")
    rng.shuffle(names)

    pacientes = []
    for i in range(n_customers):
        pacientes.append({
            "id": str(i + 1),
            "nome": names[i],
            "idade": str(rng.randint(18, 85)),
            "genero": rng.choice(_GENEROS),
        })

    # Medicos (n_products used as count, semantic: "itens")
    med_names = list(_NAMES)
    rng.shuffle(med_names)
    medicos = []
    for i in range(n_products):
        medicos.append({
            "id": str(100 + i),
            "nome": f"Dr. {med_names[i % len(med_names)]}",
            "especialidade": rng.choice(_ESPECIALIDADES),
            "sala": str(rng.randint(101, 499)),
        })

    # Consultas
    pac_weights = _zipf_weights(n_customers, s=1.0)
    med_weights = _zipf_weights(n_products, s=0.7)
    dates = _gen_dates(rng, n_orders)

    consultas = []
    for oi in range(n_orders):
        pid = rng.choices([p["id"] for p in pacientes], weights=pac_weights, k=1)[0]
        n_items = rng.randint(*items_per_order)
        dt = dates[oi]
        for _ in range(n_items):
            mid = rng.choices([m["id"] for m in medicos], weights=med_weights, k=1)[0]
            duracao = rng.choice([15, 30, 45, 60])
            # custo: faixa realista R$ 80 - R$ 800
            custo = round(rng.uniform(80.0, 800.0), 2)
            row = {
                "id_paciente": pid,
                "id_medico": mid,
                "dt": dt,
                "duracao_min": str(duracao),
                "custo": str(custo),
            }
            if rng.random() < null_rate:
                row["duracao_min"] = ""
            consultas.append(row)

    tables = {
        "pacientes": pacientes,
        "medicos": medicos,
        "consultas": consultas,
    }
    metadata = {
        "pacientes": "pacientes.csv#id",
        "medicos": "medicos.csv#id",
        "consultas": "consultas.csv#pacientes=id_paciente,medicos=id_medico",
    }
    return tables, metadata


# ---------------------------------------------------------------------------
# Financial domain
# ---------------------------------------------------------------------------

_TIPOS_CONTA = ["Corrente", "Poupanca", "Investimento"]
_AGENCIAS = ["0001", "0125", "0348", "0572", "0812", "1005", "1347"]
_CATEGORIAS_FIN = [
    "Alimentacao", "Transporte", "Moradia", "Saude", "Educacao",
    "Lazer", "Vestuario", "Salario", "Investimento", "Transferencia",
    "Taxa", "Seguro", "Assinatura", "Doacao", "Imposto",
    "Comercio", "Servicos", "Viagem", "Combustivel", "Supermercado",
]
_TIPOS_TRANS = ["Entrada", "Saida"]


def financial_transactions(
    n_orders: int = 200,
    n_customers: int | None = None,
    n_products: int = 20,
    items_per_order: tuple[int, int] = (1, 3),
    seed: int = 42,
    null_rate: float = 0.05,
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Financial transactions dataset.

    Tables: contas(id, titular, tipo, agencia),
            categorias(id, nome, tipo),
            transacoes(id_conta, id_categoria, dt, descricao, valor)
    """
    rng = random.Random(seed)

    if n_customers is None:
        n_customers = max(5, n_orders // 10)

    titulares = list(_NAMES)
    if n_customers > len(titulares):
        for i in range(n_customers - len(titulares)):
            titulares.append(f"{rng.choice(_NAMES[:20])}-{i + 1}")
    rng.shuffle(titulares)

    contas = []
    for i in range(n_customers):
        contas.append({
            "id": str(i + 1),
            "titular": titulares[i],
            "tipo": rng.choice(_TIPOS_CONTA),
            "agencia": rng.choice(_AGENCIAS),
        })

    cat_names = list(_CATEGORIAS_FIN)
    rng.shuffle(cat_names)
    categorias = []
    for i in range(n_products):
        categorias.append({
            "id": str(100 + i),
            "nome": cat_names[i % len(cat_names)],
            "tipo": rng.choice(_TIPOS_TRANS),
        })

    conta_weights = _zipf_weights(n_customers, s=1.0)
    cat_weights = _zipf_weights(n_products, s=0.7)
    dates = _gen_dates(rng, n_orders)

    transacoes = []
    for oi in range(n_orders):
        acc_id = rng.choices([c["id"] for c in contas], weights=conta_weights, k=1)[0]
        n_items = rng.randint(*items_per_order)
        dt = dates[oi]
        for _ in range(n_items):
            cat_id = rng.choices([c["id"] for c in categorias], weights=cat_weights, k=1)[0]
            # valor: log-normal-ish — most small, some big
            valor = round(rng.uniform(5.0, 1500.0), 2)
            row = {
                "id_conta": acc_id,
                "id_categoria": cat_id,
                "dt": dt,
                "descricao": f"Trans-{oi}-{rng.randint(1000,9999)}",
                "valor": str(valor),
            }
            if rng.random() < null_rate:
                row["descricao"] = ""
            transacoes.append(row)

    tables = {
        "contas": contas,
        "categorias": categorias,
        "transacoes": transacoes,
    }
    metadata = {
        "contas": "contas.csv#id",
        "categorias": "categorias.csv#id",
        "transacoes": "transacoes.csv#contas=id_conta,categorias=id_categoria",
    }
    return tables, metadata
