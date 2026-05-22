"""Auto-detect min_len por coluna (canonical, ADR-0010, H-DA-11).

Heuristica v3 (decision tree shallow em avg_len + cardinality + is_numeric)
capturou 99.5% do oracle real-world em Adult+TPC-H (sub-exp
`experiments/lab/dirty/2026-05-21-h-da-11-auto-min-len/02-heuristica-v1/`).

Gating `n >= 100`: datasets pequenos (D1-D9, exemplos sinteticos) usam
default ml=3 — preserva M9 baseline EXATO (1615B).

API:
- `detect_min_len_from_features(features, n_threshold=100)` — heuristica
  pura que recebe `ColumnFeatures` ja' calculada
- `detect_min_len(values, n_threshold=100)` — wrapper backward compat
  que chama `analyze_column(values)` internamente

Welded canonical 2026-05-22 (T-EXP-H-DA-11). Refatorado pra usar
ColumnFeatures unificado em 2026-05-22 (T-CODE-H-DA-11c).
"""

from __future__ import annotations

from tcf.column_features import ColumnFeatures, analyze_column


def detect_min_len_from_features(
    features: ColumnFeatures, n_threshold: int = 100
) -> int:
    """Detecta min_len otimo a partir de ColumnFeatures.

    Args:
        features: ColumnFeatures ja' calculada via analyze_column
        n_threshold: limite inferior de rows pra aplicar heuristica
            (default 100 — datasets menores usam ml=3 default, preserva
            M9 baseline)

    Returns:
        int em {3, 4, 5, 6}.

    Heuristica v3 (decision tree shallow):
        - n < n_threshold: 3 (gating)
        - card < 0.2: 3 (baixa-card seguro)
        - avg >= 25: 6 (long-form)
        - avg >= 8 + card >= 0.4: 6 (dates, mid-len high-card)
        - avg >= 5 + is_num + card >= 0.8: 6 (numeric high-card)
        - avg >= 12 + card >= 0.7: 5 (c_phone)
        - avg >= 3 + card >= 0.2: 4 (IDs sequenciais)
        - else: 3
    """
    if features.n_rows < n_threshold:
        return 3

    avg_len = features.avg_len
    card = features.cardinality
    is_num = features.is_numeric

    if card < 0.2:
        return 3
    if avg_len >= 25:
        return 6
    if avg_len >= 8 and card >= 0.4:
        return 6
    if avg_len >= 5 and is_num and card >= 0.8:
        return 6
    if avg_len >= 12 and card >= 0.7:
        return 5
    if avg_len >= 3 and card >= 0.2:
        return 4
    return 3


def detect_min_len(values: list[str], n_threshold: int = 100) -> int:
    """Backward-compat wrapper: analisa values e retorna min_len.

    Equivale a:
        detect_min_len_from_features(analyze_column(values), n_threshold)

    Mantido para callers que nao tem ColumnFeatures pre-computado.
    Para pipelines novos com multiplas heuristicas, preferir chamar
    `analyze_column(values)` uma vez e passar para cada
    `detect_X_from_features`.
    """
    return detect_min_len_from_features(analyze_column(values), n_threshold)
