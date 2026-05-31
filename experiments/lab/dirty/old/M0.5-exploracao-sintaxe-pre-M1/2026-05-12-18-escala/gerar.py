"""Gerador deterministico de datasets em escala para o exp 18.

4 familias do regime A do exp 17, em 3 tamanhos: N=50, 200, 1000.

Determinismo: nao usa random global. Cada string e funcao de
indices fixos.
"""

import csv
from pathlib import Path

BASE = Path(__file__).parent


def gerar_urls(n: int) -> list[str]:
    """3 recursos x N/3 IDs cada. Base URL comum."""
    base = "https://api.example.com/v1/"
    urls: list[str] = []
    per = n // 3
    resto = n - 3 * per
    for j in range(per + (1 if resto > 0 else 0)):
        urls.append(f"{base}users/{j:05d}/profile")
    for j in range(per + (1 if resto > 1 else 0)):
        urls.append(f"{base}orders/2026-{j:04d}/items")
    for j in range(per):
        cat = "abc"[j % 3]
        urls.append(f"{base}products/cat-{cat}/sku-{j:04d}")
    return urls[:n]


def gerar_iso(n: int) -> list[str]:
    """Timestamps espalhados em dias. Hora/minuto deterministicos."""
    ts: list[str] = []
    for i in range(n):
        day_offset = i // 30
        day = 1 + (day_offset % 28)
        month = 5 + (day_offset // 28) % 7
        hour = (i * 17) % 24
        minute = (i * 7) % 60
        ts.append(f"2026-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00Z")
    return ts


def gerar_ips(n: int) -> list[str]:
    """Sub-redes fixas x hosts variaveis."""
    subnets = [
        (192, 168, 1), (192, 168, 2), (192, 168, 3),
        (10, 0, 5), (10, 0, 6),
        (172, 16, 0), (172, 16, 1),
    ]
    ips: list[str] = []
    for i in range(n):
        a, b, c = subnets[i % len(subnets)]
        d = (i * 13 + 1) % 254 + 1
        ips.append(f"{a}.{b}.{c}.{d}")
    return ips


def gerar_codigos(n: int) -> list[str]:
    """4 prefixos x serial monotonico."""
    prefixos = ["PED", "INV", "REQ", "ORD"]
    codigos: list[str] = []
    for i in range(n):
        p = prefixos[i % len(prefixos)]
        s = i // len(prefixos) + 1
        codigos.append(f"{p}-2026-{s:05d}")
    return codigos


GERADORES = {
    "urls": (gerar_urls, "url"),
    "iso": (gerar_iso, "ts"),
    "ips": (gerar_ips, "ip"),
    "codigos": (gerar_codigos, "codigo"),
}

TAMANHOS = [50, 200, 1000]


def main():
    out = BASE / "data"
    out.mkdir(exist_ok=True)
    for nome, (fn, header) in GERADORES.items():
        for n in TAMANHOS:
            linhas = fn(n)
            assert len(linhas) == n, f"{nome} N={n}: gerou {len(linhas)}"
            path = out / f"{nome}-N{n:04d}.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow([header])
                for s in linhas:
                    w.writerow([s])
            print(f"Gerado {path.name}: {n} linhas, {len(set(linhas))} unicas")


if __name__ == "__main__":
    main()
