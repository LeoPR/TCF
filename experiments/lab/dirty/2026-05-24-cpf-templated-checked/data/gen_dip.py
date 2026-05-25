"""Gerador de datasets D-IP (IPv4) sinteticos.

IPv4 difere de CPF/CNPJ em 2 dimensoes:
- Sem check digit
- Slots de comprimento variavel (cada octeto 0-255 = 1 a 3 digitos)

Categoria conceitual: TCU-NoCheckVarLength (sibling de
TCU-CheckedFixedLength que cobre CPF/CNPJ).

Sub-variantes a testar:
- D-IP-uniform: 1k IPs aleatorios sem estrutura
- D-IP-subnet: 1k em 10 subredes /24 (100 IPs cada, ultimo octeto 0-99)
  -> testa SlotBehavior delta (cadence no ultimo octeto)
- D-IP-mixed: 50% canonical / 50% com leading zeros (192.168.001.001)
- D-IP-corrupt: 5% com 4 tipos (out_of_range, format, chars, length)
- Edges + extra (mesma progressao dirty)
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

SEED = 42
N = 1000

OUTPUT_DIR = Path(__file__).parent


def gen_octet() -> int:
    return random.randint(0, 255)


def fmt_ip_canonical(octets: list[int]) -> str:
    return '.'.join(str(o) for o in octets)


def fmt_ip_padded(octets: list[int]) -> str:
    """Com leading zeros: 192.168.001.001"""
    return '.'.join(f"{o:03d}" for o in octets)


def gen_uniform(n: int) -> list[str]:
    """1k IPs aleatorios sem estrutura."""
    return [fmt_ip_canonical([gen_octet() for _ in range(4)]) for _ in range(n)]


def gen_subnet(n: int, n_subnets: int = 10) -> list[str]:
    """10 subredes /24 com 100 IPs cada (ultimo octeto 0-99).

    Testa hipotese: ultimo octeto delta-aware (TCU-Delta sub-categoria).
    HCC seq-RLE deveria detectar cadence aqui mesmo sem pre-tx.
    """
    per_subnet = n // n_subnets
    out: list[str] = []
    for _ in range(n_subnets):
        prefix = [gen_octet() for _ in range(3)]
        for i in range(per_subnet):
            octets = prefix + [i]  # ultimo octeto 0..per_subnet-1
            out.append(fmt_ip_canonical(octets))
    while len(out) < n:
        out.append(fmt_ip_canonical([gen_octet() for _ in range(4)]))
    return out


def gen_mixed(n: int) -> list[str]:
    """50% canonical / 50% padded com leading zeros."""
    out: list[str] = []
    for i in range(n):
        octets = [gen_octet() for _ in range(4)]
        if i % 2 == 0:
            out.append(fmt_ip_canonical(octets))
        else:
            out.append(fmt_ip_padded(octets))
    random.shuffle(out)
    return out


# === Corruption types ===

def corrupt_range(s: str) -> str:
    """Substitui ultimo octeto por valor > 255 (e.g., 999)."""
    parts = s.split('.')
    if len(parts) == 4:
        parts[-1] = str(random.randint(256, 999))
        return '.'.join(parts)
    return s


def corrupt_format(s: str) -> str:
    """Troca `.` por separador estranho."""
    return s.replace('.', ',')


def corrupt_chars(s: str) -> str:
    """Insere letra em um octeto."""
    parts = s.split('.')
    if not parts:
        return s
    idx = random.randint(0, len(parts) - 1)
    if parts[idx]:
        pos = random.randint(0, len(parts[idx]) - 1)
        parts[idx] = parts[idx][:pos] + random.choice('XYZ') + parts[idx][pos+1:]
    return '.'.join(parts)


def corrupt_length(s: str) -> str:
    """Trunca ultimo octeto (3.4 octetos)."""
    parts = s.split('.')
    if len(parts) == 4:
        return '.'.join(parts[:3])
    return s


def gen_corrupt(n: int, corrupt_rate: float = 0.05) -> list[str]:
    out: list[str] = []
    corruptors = [corrupt_range, corrupt_format, corrupt_chars, corrupt_length]
    for i in range(n):
        s = fmt_ip_canonical([gen_octet() for _ in range(4)])
        if random.random() < corrupt_rate:
            c = corruptors[i % len(corruptors)]
            s = c(s)
        out.append(s)
    return out


def write_csv(path: Path, values: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['ip'])
        for v in values:
            w.writerow([v])


def main():
    # Etapa 1 — ilustrativos
    random.seed(SEED)
    uniform = gen_uniform(N)
    write_csv(OUTPUT_DIR / "D-IP-uniform.csv", uniform)

    random.seed(SEED)
    subnet = gen_subnet(N)
    write_csv(OUTPUT_DIR / "D-IP-subnet.csv", subnet)

    random.seed(SEED)
    mixed = gen_mixed(N)
    write_csv(OUTPUT_DIR / "D-IP-mixed.csv", mixed)

    random.seed(SEED)
    corrupt = gen_corrupt(N)
    write_csv(OUTPUT_DIR / "D-IP-corrupt.csv", corrupt)

    # Etapa 3 — bordas
    random.seed(SEED)
    write_csv(OUTPUT_DIR / "D-IP-edge-single.csv", gen_uniform(1))

    random.seed(SEED)
    same = gen_uniform(1)[0]
    write_csv(OUTPUT_DIR / "D-IP-edge-allsame.csv", [same] * N)

    random.seed(SEED)
    all_corrupt = gen_corrupt(N, corrupt_rate=1.0)
    write_csv(OUTPUT_DIR / "D-IP-edge-allcorrupt.csv", all_corrupt)

    # Etapa 4 — extrapolacoes
    random.seed(SEED)
    large = gen_uniform(10000)
    write_csv(OUTPUT_DIR / "D-IP-extra-large10k.csv", large)

    random.seed(SEED)
    hostile = (
        gen_uniform(200)
        + gen_subnet(200, n_subnets=5)
        + [fmt_ip_padded([gen_octet() for _ in range(4)]) for _ in range(200)]
        + gen_corrupt(200, corrupt_rate=1.0)
        + ['' for _ in range(100)]
        + ['2001:db8::1', '::1', 'fe80::1234'] * 33 + ['']  # IPv6 misturado
    )
    random.seed(SEED)
    random.shuffle(hostile)
    write_csv(OUTPUT_DIR / "D-IP-extra-hostile.csv", hostile[:1000])

    for name, vals in [
        ("uniform", uniform),
        ("subnet", subnet),
        ("mixed", mixed),
        ("corrupt", corrupt),
        ("edge-single", gen_uniform(1)),
        ("edge-allsame", [same] * N),
        ("edge-allcorrupt", all_corrupt),
        ("extra-large10k", large),
        ("extra-hostile", hostile[:1000]),
    ]:
        unique = len(set(vals))
        sample = vals[:2]
        print(f"D-IP-{name}: {len(vals)} rows, {unique} unique, sample={sample}")


if __name__ == "__main__":
    main()
