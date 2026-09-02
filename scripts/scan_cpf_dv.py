"""scan_cpf_dv.py: varre os arquivos VERSIONADOS atras de CPF com DV valido.

O criterio do T-QA-8 diz que nenhum artefato publicado contem CPF com digito
verificador valido, e ate' 2026-09-02 esse criterio era cumprido por convencao, sem
nada que o verificasse. Este script e' o verificador; ele so' MEDE e reporta, nao
corrige nada.

Numeros de digito repetido (`111.111.111-11` e afins) sao sentinelas reconhecidas e
nao entram na conta: eles passam no DV mas nao colidem com pessoa nenhuma.

    python scripts/scan_cpf_dv.py            # resumo por arquivo
    python scripts/scan_cpf_dv.py --listar   # cada ocorrencia

Saida diferente de zero quando encontra algo, pra poder virar gate.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Formatado (`123.456.789-09`) ou cru (`12345678909`); o `-?`/`\.?` cobre os dois.
PADRAO = re.compile(r"\b(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})\b")


def digitos_verificadores(corpo9: str) -> str:
    """Os 2 DV do CPF, pelo algoritmo oficial (peso decrescente, resto 11)."""
    s = sum(int(corpo9[i]) * (10 - i) for i in range(9))
    d1 = 0 if s % 11 < 2 else 11 - s % 11
    corpo10 = corpo9 + str(d1)
    s = sum(int(corpo10[i]) * (11 - i) for i in range(10))
    d2 = 0 if s % 11 < 2 else 11 - s % 11
    return f"{d1}{d2}"


def versionados() -> list[str]:
    r = subprocess.run(["git", "ls-files", "-z"], cwd=RAIZ,
                       capture_output=True, check=True)
    return [f for f in r.stdout.decode("utf-8").split("\0") if f]


def varre() -> tuple[list[tuple[str, str]], int]:
    achados: list[tuple[str, str]] = []
    lidos = 0
    for rel in versionados():
        try:
            texto = (RAIZ / rel).read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeError):
            continue                                  # binario/ilegivel: nao e' texto publicado
        lidos += 1
        for m in PADRAO.finditer(texto):
            corpo = m.group(1) + m.group(2) + m.group(3)
            if len(set(corpo)) == 1:                  # sentinela, nao pessoa
                continue
            if digitos_verificadores(corpo) == m.group(4):
                achados.append((rel, m.group(0)))
    return achados, lidos


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--listar", action="store_true",
                    help="imprime cada ocorrencia, nao so' o total por arquivo")
    args = ap.parse_args(argv)

    achados, lidos = varre()
    print(f"arquivos versionados lidos: {lidos}")
    print(f"CPF com DV valido (fora os de digito repetido): {len(achados)}")
    if args.listar:
        for rel, s in achados:
            print(f"  {rel}: {s}")
    else:
        for rel, n in Counter(rel for rel, _ in achados).most_common():
            print(f"  {n:>5}  {rel}")
    return 1 if achados else 0


if __name__ == "__main__":
    sys.exit(main())
