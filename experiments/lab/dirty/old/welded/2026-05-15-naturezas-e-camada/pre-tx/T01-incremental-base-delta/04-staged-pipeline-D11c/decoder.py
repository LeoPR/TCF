"""Decoder do pipeline em 3 estagios.

Inverte na ordem reversa:
1. Identifica (a partir da primeira linha do input — mesmo
   processo do encoder)
2. Deoptimiza escalas (stage C reverse) -> deltas em dias
3. Denormaliza (stage B reverse) -> datas reconstruidas
"""

from __future__ import annotations

import stage_a_identify
import stage_b_normalize
import stage_c_optimize


def decode(stage_c_output: list[str]) -> tuple[list[str], dict]:
    """Decodifica saida do estagio C de volta a linhas originais.

    Retorna (linhas, meta) — meta e' re-identificado da primeira
    linha (que sempre carrega a base original).
    """
    if not stage_c_output:
        return [], {"type": "unknown", "format": None, "granularity": None}

    meta = stage_a_identify.identify(stage_c_output[:1])
    stage_b_form = stage_c_optimize.deoptimize_scales(stage_c_output, meta)
    linhas = stage_b_normalize.denormalize_from_unit(stage_b_form, meta)
    return linhas, meta
