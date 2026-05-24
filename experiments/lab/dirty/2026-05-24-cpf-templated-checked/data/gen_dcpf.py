"""Gerador de datasets D-CPF sinteticos pra dirty lab.

Reprodutivel (seed=42). Gera 4 CSVs:
- D-CPF-uniform: 1k CPFs validos formato NNN.NNN.NNN-DD, aleatorios
- D-CPF-clustered: 1k CPFs com clustering administrativo (10 prefixos x 100)
- D-CPF-mixed: 1k mistos (50% formatados, 50% sem mascara)
- D-CPF-corrupt: 1k com ~5% corruptos (4 tipos de erro)

Uso:
    python gen_dcpf.py
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

SEED = 42
N = 1000

OUTPUT_DIR = Path(__file__).parent


def calc_check_digit(digits: list[int], weights: range) -> int:
    """Calcula 1 digito verificador de CPF via mod-11 com pesos."""
    s = sum(d * w for d, w in zip(digits, weights))
    rem = (s * 10) % 11
    return 0 if rem == 10 else rem


def gen_cpf_digits() -> list[int]:
    """Gera 11 digitos de CPF valido (9 corpo + 2 check)."""
    digits = [random.randint(0, 9) for _ in range(9)]
    digits.append(calc_check_digit(digits, range(10, 1, -1)))
    digits.append(calc_check_digit(digits, range(11, 1, -1)))
    return digits


def fmt_cpf_masked(digits: list[int]) -> str:
    s = ''.join(str(d) for d in digits)
    return f"{s[:3]}.{s[3:6]}.{s[6:9]}-{s[9:]}"


def fmt_cpf_unmasked(digits: list[int]) -> str:
    return ''.join(str(d) for d in digits)


def gen_uniform(n: int) -> list[str]:
    """1k CPFs validos uniformes aleatorios, formatados."""
    return [fmt_cpf_masked(gen_cpf_digits()) for _ in range(n)]


def gen_clustered(n: int, n_clusters: int = 10) -> list[str]:
    """1k CPFs com clustering: 10 prefixos x 100 CPFs cada.

    Cada cluster compartilha os 3 primeiros digitos (simulando mesmo
    escritorio/familia/lote administrativo). Restantes aleatorios mas
    com check digit recalculado.
    """
    per_cluster = n // n_clusters
    out: list[str] = []
    for _ in range(n_clusters):
        prefix = [random.randint(0, 9) for _ in range(3)]
        for _ in range(per_cluster):
            rest = [random.randint(0, 9) for _ in range(6)]
            digits = prefix + rest
            digits.append(calc_check_digit(digits, range(10, 1, -1)))
            digits.append(calc_check_digit(digits, range(11, 1, -1)))
            out.append(fmt_cpf_masked(digits))
    # Caso n nao seja multiplo, completa com uniformes
    while len(out) < n:
        out.append(fmt_cpf_masked(gen_cpf_digits()))
    return out


def gen_mixed(n: int) -> list[str]:
    """50% formatados, 50% sem mascara — embaralhado."""
    out: list[str] = []
    for i in range(n):
        digits = gen_cpf_digits()
        if i % 2 == 0:
            out.append(fmt_cpf_masked(digits))
        else:
            out.append(fmt_cpf_unmasked(digits))
    random.shuffle(out)
    return out


def corrupt_check(s: str) -> str:
    """Troca ultimo digito verificador (gera check invalido)."""
    digits = list(s)
    # Encontrar ultimo digito
    for i in range(len(digits) - 1, -1, -1):
        if digits[i].isdigit():
            d = int(digits[i])
            digits[i] = str((d + 1) % 10)
            return ''.join(digits)
    return s


def corrupt_format(s: str) -> str:
    """Troca `.` ou `-` por separador estranho."""
    return s.replace('.', ',').replace('-', '/')


def corrupt_chars(s: str) -> str:
    """Substitui 1 digito por letra."""
    digits = list(s)
    positions = [i for i, c in enumerate(digits) if c.isdigit()]
    if not positions:
        return s
    pos = random.choice(positions)
    digits[pos] = random.choice('XYZ')
    return ''.join(digits)


def corrupt_length(s: str) -> str:
    """Trunca 1 char (length wrong)."""
    return s[:-1] if len(s) > 0 else s


def gen_corrupt(n: int, corrupt_rate: float = 0.05) -> list[str]:
    """1k CPFs validos com ~5% corruptos (4 tipos rotativos)."""
    out: list[str] = []
    corruptors = [corrupt_check, corrupt_format, corrupt_chars, corrupt_length]
    for i in range(n):
        s = fmt_cpf_masked(gen_cpf_digits())
        if random.random() < corrupt_rate:
            c = corruptors[i % len(corruptors)]
            s = c(s)
        out.append(s)
    return out


def write_csv(path: Path, values: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['cpf'])
        for v in values:
            w.writerow([v])


def main():
    random.seed(SEED)

    uniform = gen_uniform(N)
    write_csv(OUTPUT_DIR / "D-CPF-uniform.csv", uniform)

    random.seed(SEED)
    clustered = gen_clustered(N)
    write_csv(OUTPUT_DIR / "D-CPF-clustered.csv", clustered)

    random.seed(SEED)
    mixed = gen_mixed(N)
    write_csv(OUTPUT_DIR / "D-CPF-mixed.csv", mixed)

    random.seed(SEED)
    corrupt = gen_corrupt(N)
    write_csv(OUTPUT_DIR / "D-CPF-corrupt.csv", corrupt)

    # Stats simples
    for name, vals in [
        ("uniform", uniform),
        ("clustered", clustered),
        ("mixed", mixed),
        ("corrupt", corrupt),
    ]:
        unique = len(set(vals))
        sample = vals[:3]
        print(f"D-CPF-{name}: {len(vals)} rows, {unique} unique, sample={sample}")


if __name__ == "__main__":
    main()
