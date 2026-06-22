"""Shim de compat — a implementação migrou pra `tcf.view` (A4, plano 0.8).

Re-exporta os símbolos públicos + o helper interno usado por labs. Caminho canônico:
`from tcf import view`. Ver src/tcf/view.py.
"""
from tcf.view import Filtered, LazyTCF, _idx_at, view  # noqa: F401

__all__ = ["LazyTCF", "Filtered", "view"]
