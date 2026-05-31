"""Pre stage heuristic: detect_cadence.

Welded from dirty lab `09-auto-detect-cadence-heuristic/auto_pre.py`
+ refino 2026-05-19 (lab `2026-05-19-h-da-09b-refino-real-world/`,
ADR-0008) — adicionou regra 2 (numeric+high-cardinality) que
captura 8 HELP cases em real-world numericos perdidos antes.

Type-agnostic. Single-pass sobre primeiras N strings. Memoria O(N).
"""

from __future__ import annotations

from collections import OrderedDict

from tcf.core.online import lcp_len, lcs_len


def _is_numeric_string(v: str) -> bool:
    """Aceita int, float, negativos. Rejeita empty."""
    if not v:
        return False
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


def detect_cadence(strings: list[str],
                    n_sample: int = 5,
                    threshold: float = 0.7,
                    numeric_card_threshold: float = 0.5) -> tuple[bool, dict]:
    """Detecta se strings tem cadencia estrutural.

    Regra 1 (wrapper+counter pattern):
    - lengths uniformes nas primeiras n_sample strings
    - LCP+LCS / length >= threshold pra cada par consecutivo

    Regra 2 (numeric high-cardinality, adicionada em ADR-0008):
    - todas primeiras 20 strings sao numericas
    - cardinalidade (unicas/total) > numeric_card_threshold

    Retorna (detectou, info) — info contem rule_hit + detalhes.
    """
    info = {
        "n_strings_total": len(strings),
        "n_sample": min(n_sample, len(strings)),
        "threshold": threshold,
        "numeric_card_threshold": numeric_card_threshold,
        "rule_hit": None,
    }

    if len(strings) < 2:
        info["reason"] = "muito poucas strings (<2)"
        return False, info

    sample = strings[:min(n_sample, len(strings))]
    lengths = [len(s) for s in sample]
    info["lengths"] = lengths
    uniform_length = (len(set(lengths)) == 1) and lengths[0] > 0

    # ---- Regra 1: wrapper+counter ----
    if uniform_length:
        L = lengths[0]
        ratios = []
        for i in range(1, len(sample)):
            a, b = sample[i - 1], sample[i]
            lcp = lcp_len(a, b)
            lcs = lcs_len(a, b)
            ratio = (lcp + lcs) / L
            ratios.append({"pair": i, "lcp": lcp, "lcs": lcs,
                           "ratio": round(ratio, 3)})
        info["lcp_lcs_ratios"] = ratios
        if ratios and all(r["ratio"] >= threshold for r in ratios):
            avg = sum(r["ratio"] for r in ratios) / len(ratios)
            info["rule_hit"] = "1-uniform-length-high-lcp-lcs"
            info["reason"] = f"L={L}, all ratios >= {threshold} (avg={avg:.2f})"
            return True, info

    # ---- Regra 2: numeric high-cardinality (ADR-0008) ----
    # Cardinalidade computada em strings completas (nao so' sample)
    seen = OrderedDict()
    for v in strings:
        seen[v] = True
    n_unicas = len(seen)
    cardinality = n_unicas / len(strings)
    info["n_unicas"] = n_unicas
    info["cardinality"] = round(cardinality, 3)

    # Numeric check em primeiras 20 strings (sample maior pra reduzir false
    # positive em datasets com prefixo numerico mas conteudo nao-numerico)
    check_sample = strings[:min(20, len(strings))]
    n_numeric = sum(1 for v in check_sample if _is_numeric_string(v))
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
