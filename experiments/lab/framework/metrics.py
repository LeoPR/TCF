"""Metricas comuns do lab — comparacao de rows + util.

`compare_rows(actual, expected)` faz comparacao tolerante a tipos
quando aplicavel (ex: int 30 vs str '30' depois de roundtrip CSV).
"""
from __future__ import annotations


def compare_rows(actual: list[dict], expected: list[dict],
                 tolerant_types: bool = True) -> tuple[bool, dict]:
    """Compara duas listas de dicts.

    Returns:
        (ok, diff): ok=True se equivalentes; diff descreve onde discordam.

    Se `tolerant_types=True`, considera 30 == "30" (encoder pode perder
    tipos no roundtrip, ex: CSV).
    """
    if len(actual) != len(expected):
        return False, {"reason": "length_mismatch",
                       "actual_len": len(actual),
                       "expected_len": len(expected)}

    diffs = []
    for i, (a, e) in enumerate(zip(actual, expected)):
        keys_a, keys_e = set(a), set(e)
        if keys_a != keys_e:
            diffs.append({
                "row": i, "reason": "key_mismatch",
                "missing": list(keys_e - keys_a),
                "extra":   list(keys_a - keys_e),
            })
            continue
        for k in keys_e:
            va, ve = a[k], e[k]
            if not _values_equal(va, ve, tolerant_types):
                diffs.append({
                    "row": i, "key": k,
                    "actual": va, "actual_type": type(va).__name__,
                    "expected": ve, "expected_type": type(ve).__name__,
                })
        if len(diffs) > 10:
            diffs.append({"reason": "truncated_at_10_diffs"})
            break

    if not diffs:
        return True, {}
    return False, {"reason": "value_mismatch", "diffs": diffs}


def _values_equal(a, b, tolerant_types: bool) -> bool:
    """True se a == b, com tolerancia opcional a tipos."""
    if a == b:
        return True
    if not tolerant_types:
        return False
    # Tolerancia: comparar como str
    if str(a) == str(b):
        return True
    # Tolerancia: numericos
    try:
        return float(a) == float(b)
    except (ValueError, TypeError):
        return False


def utf8_len(text: str) -> int:
    """Bytes em UTF-8 para um string."""
    return len(text.encode("utf-8"))
