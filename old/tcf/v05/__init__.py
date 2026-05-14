"""TCF v0.5 — Tabular Compact Format, regra unificada.

Formato fechado nas mesas dirty de 2026-05-07..2026-05-09.
Especificacao em:
  experiments/lab/dirty/2026-05-09-gramatica-densidade/04-gramatica-formal.md

Esta implementacao comeca com SRDM (sort + RLE + dict + auto-discrim),
que eh o subset minimo da gramatica. Extensoes (A, delta, P, L', K, I, Pi)
serao adicionadas em fases subsequentes.
"""
from __future__ import annotations

from .flags import Flags, DEFAULT_FLAGS
from .decoder import decode
from .encoder import encode

__all__ = ["Flags", "DEFAULT_FLAGS", "decode", "encode"]
