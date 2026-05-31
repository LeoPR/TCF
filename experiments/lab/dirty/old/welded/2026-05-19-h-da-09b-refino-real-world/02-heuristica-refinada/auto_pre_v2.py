"""Heuristica refinada (v2) de detect_cadence pra real-world.

Adiciona regra: numeric + high cardinality → enable hint.
Mantem regra existente: uniform_length + LCP+LCS >= threshold → enable.
"""

from __future__ import annotations

from tcf.core.online import lcp_len, lcs_len


def is_numeric_string(v: str) -> bool:
    """Aceita int, float, negativos. Rejeita empty."""
    if not v:
        return False
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


def detect_cadence_v2(strings: list[str],
                        n_sample: int = 5,
                        threshold: float = 0.7,
                        numeric_card_threshold: float = 0.5) -> tuple[bool, dict]:
    """Heuristica refinada — v2 (2026-05-19).

    Regra 1: lengths uniformes + LCP+LCS >= threshold (catches
             wrapper+counter patterns como D9 @@@KEY=valueX@@@)

    Regra 2 (NOVA): numeric + cardinality > numeric_card_threshold
             (catches numeric high-card columns como fnlwgt, prices,
             keys)

    Retorna (detectou, info).
    """
    info = {
        "n_strings": len(strings),
        "threshold": threshold,
        "numeric_card_threshold": numeric_card_threshold,
        "rule_hit": None,
    }

    if len(strings) < 2:
        info["reason"] = "muito poucas strings"
        return False, info

    sample = strings[:min(n_sample, len(strings))]
    lengths = [len(s) for s in sample]
    info["lengths"] = lengths
    uniform_length = (len(set(lengths)) == 1) and lengths[0] > 0

    # Regra 1: wrapper+counter pattern
    if uniform_length:
        L = lengths[0]
        ratios = []
        for i in range(1, len(sample)):
            a, b = sample[i - 1], sample[i]
            ratios.append((lcp_len(a, b) + lcs_len(a, b)) / L)
        info["lcp_lcs_ratios"] = [round(r, 3) for r in ratios]
        info["avg_lcp_lcs"] = round(sum(ratios) / len(ratios), 3) if ratios else 0
        if ratios and min(ratios) >= threshold:
            info["rule_hit"] = "1-uniform-length-high-lcp-lcs"
            info["reason"] = f"uniform_length={L}, all LCP+LCS >= {threshold}"
            return True, info

    # Regra 2 (NOVA): numeric + high cardinality
    # Avalia em strings unicas pra cardinalidade
    from collections import OrderedDict
    seen = OrderedDict()
    for v in strings:
        seen[v] = True
    n_unicas = len(seen)
    cardinality = n_unicas / len(strings) if strings else 0
    info["n_unicas"] = n_unicas
    info["cardinality"] = round(cardinality, 3)

    # Check numeric em sample (rapido) + algumas amostras
    check_sample = strings[:min(20, len(strings))]
    n_numeric = sum(1 for v in check_sample if is_numeric_string(v))
    is_numeric_col = (n_numeric == len(check_sample))
    info["is_numeric"] = is_numeric_col

    if is_numeric_col and cardinality > numeric_card_threshold:
        info["rule_hit"] = "2-numeric-high-cardinality"
        info["reason"] = (
            f"numeric, cardinality={cardinality:.3f} > {numeric_card_threshold}"
        )
        return True, info

    info["reason"] = "nenhuma regra acionou"
    return False, info
