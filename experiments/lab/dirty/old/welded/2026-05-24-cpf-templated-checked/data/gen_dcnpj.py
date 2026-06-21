"""Gerador de datasets D-CNPJ sinteticos.

Mesma progressao dirty que D-CPF (etapas 1 + 3 + 4):
- D-CNPJ-uniform: 1k CNPJs uniformes formatados
- D-CNPJ-clustered: 1k com clustering (raiz 8 digitos compartilhada)
- D-CNPJ-mixed: 1k mistos (50% formatados / 50% unmasked)
- D-CNPJ-corrupt: 1k com 5% corruptos (4 mutacoes sistematicas)
- D-CNPJ-edge-single / -allsame / -allcorrupt
- D-CNPJ-extra-large10k / -extra-hostile

CNPJ: NN.NNN.NNN/NNNN-DD (12 digits body + 2 check; mod-11 dupla
com pesos diferentes de CPF).
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

SEED = 42
N = 1000

OUTPUT_DIR = Path(__file__).parent

# Pesos CNPJ (mod-11)
W1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
W2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]


def calc_check_cnpj(digits: list[int], weights: list[int]) -> int:
    s = sum(d * w for d, w in zip(digits, weights))
    rem = s % 11
    return 0 if rem < 2 else 11 - rem


def gen_cnpj_digits() -> list[int]:
    """Gera 14 digitos validos (12 corpo + 2 check)."""
    digits = [random.randint(0, 9) for _ in range(12)]
    digits.append(calc_check_cnpj(digits, W1))
    digits.append(calc_check_cnpj(digits, W2))
    return digits


def fmt_cnpj_masked(digits: list[int]) -> str:
    s = ''.join(str(d) for d in digits)
    return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"


def fmt_cnpj_unmasked(digits: list[int]) -> str:
    return ''.join(str(d) for d in digits)


def gen_uniform(n: int) -> list[str]:
    return [fmt_cnpj_masked(gen_cnpj_digits()) for _ in range(n)]


def gen_clustered(n: int, n_clusters: int = 10) -> list[str]:
    """Clustering: 10 raizes 8-digit (matriz), 100 filiais cada."""
    per_cluster = n // n_clusters
    out: list[str] = []
    for _ in range(n_clusters):
        root = [random.randint(0, 9) for _ in range(8)]
        for _ in range(per_cluster):
            filial = [random.randint(0, 9) for _ in range(4)]
            digits = root + filial
            digits.append(calc_check_cnpj(digits, W1))
            digits.append(calc_check_cnpj(digits, W2))
            out.append(fmt_cnpj_masked(digits))
    while len(out) < n:
        out.append(fmt_cnpj_masked(gen_cnpj_digits()))
    return out


def gen_mixed(n: int) -> list[str]:
    out: list[str] = []
    for i in range(n):
        digits = gen_cnpj_digits()
        if i % 2 == 0:
            out.append(fmt_cnpj_masked(digits))
        else:
            out.append(fmt_cnpj_unmasked(digits))
    random.shuffle(out)
    return out


def corrupt_check(s: str) -> str:
    digits = list(s)
    for i in range(len(digits) - 1, -1, -1):
        if digits[i].isdigit():
            d = int(digits[i])
            digits[i] = str((d + 1) % 10)
            return ''.join(digits)
    return s


def corrupt_format(s: str) -> str:
    return s.replace('.', ',').replace('-', '_').replace('/', '|')


def corrupt_chars(s: str) -> str:
    digits = list(s)
    positions = [i for i, c in enumerate(digits) if c.isdigit()]
    if not positions:
        return s
    pos = random.choice(positions)
    digits[pos] = random.choice('XYZ')
    return ''.join(digits)


def corrupt_length(s: str) -> str:
    return s[:-1] if len(s) > 0 else s


def gen_corrupt(n: int, corrupt_rate: float = 0.05) -> list[str]:
    out: list[str] = []
    corruptors = [corrupt_check, corrupt_format, corrupt_chars, corrupt_length]
    for i in range(n):
        s = fmt_cnpj_masked(gen_cnpj_digits())
        if random.random() < corrupt_rate:
            c = corruptors[i % len(corruptors)]
            s = c(s)
        out.append(s)
    return out


def write_csv(path: Path, values: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['cnpj'])
        for v in values:
            w.writerow([v])


def main():
    # Etapa 1 — ilustrativos
    random.seed(SEED)
    uniform = gen_uniform(N)
    write_csv(OUTPUT_DIR / "D-CNPJ-uniform.csv", uniform)

    random.seed(SEED)
    clustered = gen_clustered(N)
    write_csv(OUTPUT_DIR / "D-CNPJ-clustered.csv", clustered)

    random.seed(SEED)
    mixed = gen_mixed(N)
    write_csv(OUTPUT_DIR / "D-CNPJ-mixed.csv", mixed)

    random.seed(SEED)
    corrupt = gen_corrupt(N)
    write_csv(OUTPUT_DIR / "D-CNPJ-corrupt.csv", corrupt)

    # Etapa 3 — bordas
    random.seed(SEED)
    write_csv(OUTPUT_DIR / "D-CNPJ-edge-single.csv", gen_uniform(1))

    random.seed(SEED)
    same = gen_uniform(1)[0]
    write_csv(OUTPUT_DIR / "D-CNPJ-edge-allsame.csv", [same] * N)

    random.seed(SEED)
    all_corrupt = gen_corrupt(N, corrupt_rate=1.0)
    write_csv(OUTPUT_DIR / "D-CNPJ-edge-allcorrupt.csv", all_corrupt)

    # Etapa 4 — extrapolacoes
    random.seed(SEED)
    large = gen_uniform(10000)
    write_csv(OUTPUT_DIR / "D-CNPJ-extra-large10k.csv", large)

    random.seed(SEED)
    hostile = (
        gen_uniform(250)
        + [v.replace('.', '').replace('/', '').replace('-', '') for v in gen_uniform(250)]
        + gen_corrupt(250, corrupt_rate=1.0)
        + ['' for _ in range(250)]
    )
    random.seed(SEED)
    random.shuffle(hostile)
    write_csv(OUTPUT_DIR / "D-CNPJ-extra-hostile.csv", hostile)

    for name, vals in [
        ("uniform", uniform),
        ("clustered", clustered),
        ("mixed", mixed),
        ("corrupt", corrupt),
        ("edge-single", gen_uniform(1)),
        ("edge-allsame", [same] * N),
        ("edge-allcorrupt", all_corrupt),
        ("extra-large10k", large),
        ("extra-hostile", hostile),
    ]:
        unique = len(set(vals))
        sample = vals[:2]
        print(f"D-CNPJ-{name}: {len(vals)} rows, {unique} unique, sample={sample}")


if __name__ == "__main__":
    main()
