"""Decoder self-contained — recebe APENAS path do .tcf, sem hint externo.

Demonstra que o arquivo .tcf carrega tudo que e' necessario pra
reconstruir as linhas originais. Algoritmo TCF + pre-tx logic =
conhecimento compartilhado (como gunzip).

Auto-deducao:
- Stage A re-identifica natureza pela primeira linha do TCF-decodificado
- Stage C inverso parse escalas
- Stage B inverso aplica deltas

Usado como ferramenta de auditoria no sub-exp 10 — cada dataset
roda este decoder pra validar self-containment.

Uso como modulo:
    from self_contained_decoder import decode_self_contained
    linhas, meta = decode_self_contained("path/to/file.tcf")

Uso CLI:
    python self_contained_decoder.py path/to/file.tcf
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[7]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(THIS))

from tcf import decode as tcf_decode  # noqa: E402

import stage_a_identify  # noqa: E402
import stage_b_normalize  # noqa: E402
import stage_c_optimize  # noqa: E402


def decode_self_contained(tcf_path) -> tuple[list[str], dict]:
    """Decoder principal — recebe APENAS path do .tcf.

    Returns:
        (linhas_reconstruidas, meta_inferido)
    """
    tcf_text = Path(tcf_path).read_text(encoding="utf-8")
    pretx_out = tcf_decode(tcf_text)
    if not pretx_out:
        return [], {"type": "empty"}
    meta = stage_a_identify.identify(pretx_out[:1])
    b_form = stage_c_optimize.deoptimize_scales(pretx_out, meta)
    linhas = stage_b_normalize.denormalize_from_unit(b_form, meta)
    return linhas, meta


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python self_contained_decoder.py <path-to-tcf-file>")
        sys.exit(1)
    tcf_path = sys.argv[1]
    lines, meta = decode_self_contained(tcf_path)
    print(json.dumps({
        "input_path": str(tcf_path),
        "meta_auto_detected": meta,
        "n_lines": len(lines),
        "lines": lines,
    }, indent=2, ensure_ascii=False))
