"""HCC optimizations v1 + v2 — zero-risk (no byte change esperado).

v1: _estimate_baseline_chars otimizado (counting direto).
v2: v1 + _build_trace/_build_rede em noop.

Usage:
  from hcc_opts import patch_v1, patch_v2, unpatch
  patch_v1()  # ou patch_v2()
  ...
  unpatch()
"""

from __future__ import annotations

# Lazy imports — modulo `tcf.composicional.syntax` deve estar disponivel
from tcf.composicional import syntax as _hcc

_originals = {}


def _estimate_baseline_chars_v1(self, sub, atom_count, comp_acc_k):
    """Conta caracteres direto, sem construir list+string."""
    n_est_val = atom_count + comp_acc_k + 1
    if n_est_val < 100:
        n_est = 2
    else:
        n_est = len(str(n_est_val))

    total = 0
    n_parts = 0
    L = len(sub)
    i = 0
    while i < L:
        v = sub[i]
        if v > 0:
            run_start = v
            run_end = v
            j = i + 1
            while j < L:
                vj = sub[j]
                if vj > 0 and vj == run_end + 1:
                    run_end = vj
                    j += 1
                else:
                    break
            if (j - i) >= 3:
                total += len(str(run_start)) + 2 + len(str(run_end))
                n_parts += 1
            else:
                for r in range(run_start, run_end + 1):
                    total += len(str(r))
                    n_parts += 1
            i = j
        else:
            total += n_est
            n_parts += 1
            i += 1
    return total + (n_parts - 1 if n_parts > 1 else 0)


def _build_trace_noop(self, *args, **kwargs):
    self._trace = []


def _build_rede_noop(self, *args, **kwargs):
    self._rede = []


def patch_v1():
    """Aplica so' v1: _estimate_baseline_chars otimizado."""
    cls = _hcc.M8AVirtualRefsSyntax
    _originals.clear()
    _originals['_estimate_baseline_chars'] = cls._estimate_baseline_chars
    cls._estimate_baseline_chars = _estimate_baseline_chars_v1


def patch_v2():
    """Aplica v1 + v2: skip _build_trace/_build_rede."""
    patch_v1()
    cls = _hcc.M8AVirtualRefsSyntax
    _originals['_build_trace'] = cls._build_trace
    _originals['_build_rede'] = cls._build_rede
    cls._build_trace = _build_trace_noop
    cls._build_rede = _build_rede_noop


def unpatch():
    cls = _hcc.M8AVirtualRefsSyntax
    for name, orig in _originals.items():
        setattr(cls, name, orig)
    _originals.clear()
