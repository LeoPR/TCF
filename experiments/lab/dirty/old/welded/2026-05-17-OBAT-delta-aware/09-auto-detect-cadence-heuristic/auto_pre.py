"""Pre stage heuristic: detect_cadence.

Type-agnostic. Single-pass. Observa primeiras N strings.

Retorna True se data parece ter cadencia (length uniforme + LCP+LCS
ratio alto entre pares consecutivos). False caso contrario.
"""

from __future__ import annotations

from tcf.core.online import lcp_len, lcs_len


def detect_cadence(strings: list[str],
                    n_sample: int = 5,
                    threshold: float = 0.7) -> tuple[bool, dict]:
    """Retorna (detectou, info).

    info contem detalhes pra inspecao/debug:
    - reason: motivo de True/False
    - sample_size: quantas strings analisadas
    - lengths: lengths das strings sample
    - lcp_lcs_ratios: ratios calculados
    """
    info = {
        "n_strings_total": len(strings),
        "n_sample": min(n_sample, len(strings)),
        "threshold": threshold,
    }

    if len(strings) < 2:
        info["reason"] = "muito poucas strings (<2)"
        return False, info

    sample = strings[:min(n_sample, len(strings))]
    info["sample"] = sample
    lengths = [len(s) for s in sample]
    info["lengths"] = lengths

    if len(set(lengths)) > 1:
        info["reason"] = f"lengths nao-uniformes: {lengths}"
        return False, info

    L = lengths[0]
    if L == 0:
        info["reason"] = "lengths zero"
        return False, info

    ratios = []
    for i in range(1, len(sample)):
        a, b = sample[i - 1], sample[i]
        lcp = lcp_len(a, b)
        lcs = lcs_len(a, b)
        ratio = (lcp + lcs) / L
        ratios.append({"pair": i, "lcp": lcp, "lcs": lcs, "ratio": round(ratio, 3)})
        if ratio < threshold:
            info["lcp_lcs_ratios"] = ratios
            info["reason"] = (
                f"par {i}: lcp+lcs={lcp+lcs}, ratio={ratio:.2f} < {threshold}"
            )
            return False, info

    info["lcp_lcs_ratios"] = ratios
    info["reason"] = f"todos ratios >= {threshold} (avg={sum(r['ratio'] for r in ratios)/len(ratios):.2f})"
    return True, info
