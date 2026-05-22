"""Auto-detect min_len por coluna (canonical, ADR-0010, H-DA-11).

Pre-pass leve sobre values pra decidir `min_len` otimo. Heuristica v3
(decision tree shallow em avg_len + cardinality + is_numeric) capturou
99.5% do oracle real-world em Adult+TPC-H (sub-exp
`experiments/lab/dirty/2026-05-21-h-da-11-auto-min-len/02-heuristica-v1/`).

Gating `n >= 100`: datasets pequenos (D1-D9, exemplos sinteticos) usam
default ml=3 — preserva M9 baseline EXATO (1615B).

Custo: 1 passada O(N) sobre values pra avg_len + set + sample.

Welded canonical 2026-05-22 (apos validacao prototype EXP-010 em
sub-exp 04). Backward compat: output bytes-canonical IDENTICO pra
D1-D9 (n<100 fallback); diferente pra colunas >=100 rows (esperado e
desejado — ganho ~9% real-world weighted).
"""

from __future__ import annotations


def _is_numeric_string(v: str) -> bool:
    """Aceita int, float, negativos. Rejeita empty."""
    if not v:
        return False
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


def detect_min_len(values: list[str], n_threshold: int = 100) -> int:
    """Detecta min_len otimo via heuristica v3 + gating por n_rows.

    Retorna int em {3, 4, 5, 6}.
    - n < n_threshold: retorna 3 (preserva M9 baseline)
    - n >= n_threshold: heuristica v3 (avg_len + cardinality + is_numeric)

    Empirico: captura 99.5% do oracle real-world (9.87% / 9.92% weighted
    em Adult+TPC-H 58 colunas).
    """
    n = len(values)
    if n < n_threshold:
        return 3

    avg_len = sum(len(v) for v in values) / n
    n_unicas = len(set(values))
    card = n_unicas / n
    sample = values[:min(20, n)]
    is_num = all(_is_numeric_string(v) for v in sample) if sample else False

    # Heuristica v3 (decision tree shallow)
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
