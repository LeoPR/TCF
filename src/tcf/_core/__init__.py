"""tcf._core — aceleradores compilados OPCIONAIS (Cython).

Cada modulo aqui tem fallback pure-Python no codigo canonical de src/tcf.
Se a extensao compilada nao estiver presente (install sem compilador), o
import falha silenciosamente e o pure-Python e' usado — output byte-identico.

Atual:
- detect.pyx -> _detect_compositions (H-PERF-06-v2 Fase B, ADR-0020).
  Fallback: M8AVirtualRefsSyntax._detect_compositions em composicional/syntax.py.

Build: best-effort durante `pip install` (hatch_build.py); ou local via
`python -m build` / extensao compilada in-place.
"""
