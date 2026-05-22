"""ColumnFeatures — pre-pass unificado de features de coluna.

Calcula features basicas em 1 passada O(N) sobre values:
- n_rows, n_unicas
- avg_len, cardinality
- is_numeric (sample check)
- sample (primeiras N strings)

Heuristicas downstream (detect_min_len, detect_cadence, futuras
detect_X de naturezas pre-tx) recebem ColumnFeatures imutavel e
escolhem comportamento. Reduz duplicacao + permite reuso.

Conexoes:
- ADR-0010 (auto-detect min_len) — usa ColumnFeatures
- ADR-0008 (detect_cadence) — quando weldar canonical, usara' ColumnFeatures
- H-DA-11c — motivacao desta unificacao

Welded 2026-05-22 (T-CODE-H-DA-11c).
"""

from __future__ import annotations

from dataclasses import dataclass


def _is_numeric_string(v: str) -> bool:
    """Aceita int, float, negativos. Rejeita empty."""
    if not v:
        return False
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class ColumnFeatures:
    """Features imutaveis extraidas de uma coluna de strings.

    Computado por `analyze_column(values)` em 1 passada O(N).
    """
    n_rows: int
    n_unicas: int
    avg_len: float
    cardinality: float
    is_numeric: bool
    sample: tuple[str, ...]  # tuple pra ser hashable (dataclass frozen)


def analyze_column(values: list[str], sample_size: int = 20) -> ColumnFeatures:
    """Calcula features basicas de uma coluna em 1 passada.

    Args:
        values: lista de strings da coluna (com possiveis duplicatas)
        sample_size: tamanho do sample pra check is_numeric (default 20)

    Returns:
        ColumnFeatures imutavel.

    Edge cases:
        - values vazio: retorna features zerados, is_numeric=False
        - is_numeric: True so' se TODAS as strings do sample parsam float
    """
    n = len(values)
    if n == 0:
        return ColumnFeatures(
            n_rows=0, n_unicas=0, avg_len=0.0,
            cardinality=0.0, is_numeric=False, sample=(),
        )

    n_unicas = len(set(values))
    avg_len = sum(len(v) for v in values) / n
    sample = tuple(values[:min(sample_size, n)])
    is_num = all(_is_numeric_string(v) for v in sample) if sample else False

    return ColumnFeatures(
        n_rows=n,
        n_unicas=n_unicas,
        avg_len=avg_len,
        cardinality=n_unicas / n,
        is_numeric=is_num,
        sample=sample,
    )
