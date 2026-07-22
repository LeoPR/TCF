"""theolib — engenhoca da teoria de cardinalidade. Mede o trade do owner:
  RÁPIDO guiado-por-estrutura (RLE de valor-inteiro, sem afixo) vs PLENO (OBAT/HCC do TCF).
+ medidas de FORÇA de cardinalidade (multiplicidade, largura do valor, g3-error da FD). NÃO toca src/tcf.
"""
from __future__ import annotations
import sys
from collections import Counter, defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]      # .../TCF (repo root)
sys.path.insert(0, str(_ROOT / "src"))
from tcf import encode          # noqa: E402


# ---- estratégia RÁPIDA: RLE de valor-inteiro (adjacente), SEM tokenizar afixo ----
def rle_only(values: list) -> tuple[str, int]:
    out, i = [], 0
    while i < len(values):
        j = i
        while j < len(values) and values[j] == values[i]:
            j += 1
        run = j - i
        out.append(f"*{run}|{values[i]}" if run > 1 else str(values[i]))
        i = j
    text = "\n".join(out) + "\n"
    return text, len(text.encode())


# ---- estratégia PLENA: OBAT/HCC do TCF ----
def full_tcf(values: list) -> tuple[str, int]:
    text = encode([str(v) for v in values])
    return text, len(text.encode())


# ---- medidas de FORÇA de cardinalidade ----
def multiplicity(parent: list) -> float:
    """linhas por valor-pai distinto (tamanho médio de run/grupo). 1.0 = não repete (fraca)."""
    d = len(set(parent))
    return len(parent) / d if d else 0.0


def value_width(parent: list) -> float:
    return sum(len(str(x)) for x in set(parent)) / max(1, len(set(parent)))


def g3(a: list, b: list) -> float:
    """g3-error de A→B (Kivinen&Mannila): fração mínima de linhas a remover p/ FD passar exata."""
    groups = defaultdict(Counter)
    for x, y in zip(a, b):
        groups[x][y] += 1
    keep = sum(max(c.values()) for c in groups.values())
    return (len(a) - keep) / len(a) if a else 0.0


def classify(a: list, b: list) -> str:
    nA, nB, nAB = len(set(a)), len(set(b)), len(set(zip(a, b)))
    ab, ba = nAB == nA, nAB == nB
    return "1:1" if ab and ba else "1:N" if ba else "N:1" if ab else "N:N"


def strength_label(mult: float, width: float, g3v: float) -> str:
    """Rótulo didático de força (heurístico, pra orientar — não é lei)."""
    if g3v > 0.0:
        return "QUASE (FD aproximada, g3>0)"
    if mult <= 1.2:
        return "FRACA (pai quase não repete → pouco a fatorar)"
    if mult >= 3 and width >= 8:
        return "FORTE (alta multiplicidade + valor largo)"
    return "MÉDIA"
