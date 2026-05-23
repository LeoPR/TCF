"""Detect cadence — heuristica pre-pass pra OBAT shape-preserve hint.

Welded canonical 2026-05-22 (T-CODE-PACOTE1-WELD-CANONICAL).
Origem: `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/auto_pre.py`
(welded 2026-05-17, refino real-world 2026-05-19 ADR-0008).

Heuristica 2-regras:
- Regra 1 (wrapper+counter): lengths uniformes nas primeiras N strings
  + LCP+LCS / length >= threshold em pares consecutivos
- Regra 2 (numeric high-cardinality, ADR-0008): todas primeiras 20
  strings sao numericas + cardinalidade > 0.5

Quando dispara, encoder usa `processar_with_hint(unicas, min_len,
prefer_shape_consistency=True)` em vez de `processar(unicas, min_len)`
canonical.

Refatorado pra usar ColumnFeatures (H-DA-11c). Versao canonical
recebe `analyze_column(values)` ja' calculada — evita recomputar
features basicas.
"""

from __future__ import annotations

from tcf.column_features import ColumnFeatures
from tcf.core.online import lcp_len, lcs_len


def detect_cadence_from_features(
    features: ColumnFeatures,
    strings_unicas: list[str],
    n_sample: int = 5,
    threshold: float = 0.7,
    numeric_card_threshold: float = 0.5,
) -> tuple[bool, dict]:
    """Detecta se coluna tem cadencia estrutural via 2 regras.

    Args:
        features: ColumnFeatures basico (avg_len, card, is_numeric, sample, ...)
        strings_unicas: unicas pra calcular LCP/LCS em pares consecutivos
        n_sample: tamanho sample regra 1 (lengths uniformes + LCP/LCS)
        threshold: limiar LCP+LCS / length na regra 1 (default 0.7)
        numeric_card_threshold: limiar cardinalidade regra 2 (default 0.5)

    Returns:
        (detectou, info) — info contem rule_hit + detalhes.
    """
    info: dict = {
        "n_strings_total": len(strings_unicas),
        "n_sample": min(n_sample, len(strings_unicas)),
        "threshold": threshold,
        "numeric_card_threshold": numeric_card_threshold,
        "rule_hit": None,
    }

    if len(strings_unicas) < 2:
        info["reason"] = "muito poucas strings (<2)"
        return False, info

    sample = strings_unicas[:min(n_sample, len(strings_unicas))]
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
    # Cardinalidade computada sobre values (rows) em ColumnFeatures
    info["cardinality"] = round(features.cardinality, 3)
    info["is_numeric"] = features.is_numeric

    if features.is_numeric and features.cardinality > numeric_card_threshold:
        info["rule_hit"] = "2-numeric-high-cardinality"
        info["reason"] = (
            f"numeric, cardinality={features.cardinality:.3f} "
            f"> {numeric_card_threshold}"
        )
        return True, info

    info["reason"] = "nenhuma regra acionou"
    return False, info
