"""Gera 4 datasets x 4 ordenacoes = 16 CSVs em data/.

Determinista por seed. Cada dataset tem N_unique x cardinalidade
diferente, e a presenca/ausencia de prefixo Patricia.
"""

import csv
import random
from pathlib import Path

BASE = Path(__file__).parent / "data"

NOMES_5 = ["Ana", "Bob", "Carlos", "Diana", "Edu"]

NOMES_40 = [
    "Alice", "Bruno", "Clara", "Daniel", "Erica",
    "Felipe", "Gabriela", "Hugo", "Iris", "Julio",
    "Karina", "Lucas", "Marina", "Nicolas", "Olivia",
    "Paulo", "Quirino", "Rafaela", "Samuel", "Tania",
    "Ulisses", "Valeria", "Wagner", "Xavier", "Yara",
    "Zenaide", "Antonio", "Beatriz", "Cesar", "Denise",
    "Eduardo", "Fabiana", "Gustavo", "Helena", "Igor",
    "Joana", "Kaique", "Leticia", "Marcio", "Nadia",
]

USR_5 = [f"USR{i:04d}" for i in range(1, 6)]
USR_20 = [f"USR{i:04d}" for i in range(1, 21)]
PRD_5 = [f"PRD{i:04d}" for i in range(1, 6)]

DATASETS = {
    "D1-baixa-card-sem-patricia": {
        "header": "nome",
        "unicos": NOMES_5,
        "n_total": 50,
    },
    "D2-alta-card-sem-patricia": {
        "header": "nome",
        "unicos": NOMES_40,
        "n_total": 100,
    },
    "D3-baixa-card-com-patricia": {
        "header": "codigo",
        "unicos": USR_5,
        "n_total": 50,
    },
    "D4-alta-card-com-patricia": {
        "header": "codigo",
        "unicos": USR_20 + PRD_5,
        "n_total": 100,
    },
}


def gerar_4_ordenacoes(unicos: list[str], n_total: int,
                       seed: int) -> dict[str, list[str]]:
    rnd = random.Random(seed)

    n_unique = len(unicos)
    base_count = n_total // n_unique
    extra = n_total % n_unique
    contagens = [base_count + (1 if i < extra else 0) for i in range(n_unique)]
    rnd.shuffle(contagens)

    bag: list[str] = []
    for valor, cnt in zip(unicos, contagens):
        bag.extend([valor] * cnt)

    # 1. ORIGINAL — shuffle leve, alguns runs por chance
    rnd_orig = random.Random(seed + 1)
    original = bag[:]
    rnd_orig.shuffle(original)

    # 2. SORTED — lex
    sorted_v = sorted(bag)

    # 3. RANDOM — shuffle profundo (re-shuffle)
    rnd_rand = random.Random(seed + 2)
    random_v = bag[:]
    for _ in range(3):
        rnd_rand.shuffle(random_v)

    # 4. AGRUPADO — runs maximos: todos iguais juntos
    rnd_agr = random.Random(seed + 3)
    grupos = list(set(bag))
    rnd_agr.shuffle(grupos)
    contagens_real = {v: bag.count(v) for v in set(bag)}
    agrupado = []
    for g in grupos:
        agrupado.extend([g] * contagens_real[g])

    return {
        "original": original,
        "sorted": sorted_v,
        "random": random_v,
        "agrupado": agrupado,
    }


def main():
    for nome, cfg in DATASETS.items():
        pasta = BASE / nome
        pasta.mkdir(parents=True, exist_ok=True)
        ords = gerar_4_ordenacoes(cfg["unicos"], cfg["n_total"], seed=42)
        for ord_nome, linhas in ords.items():
            path = pasta / f"{ord_nome}.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([cfg["header"]])
                for v in linhas:
                    writer.writerow([v])
            print(f"  {nome}/{ord_nome}.csv: {len(linhas)} linhas")


if __name__ == "__main__":
    main()
