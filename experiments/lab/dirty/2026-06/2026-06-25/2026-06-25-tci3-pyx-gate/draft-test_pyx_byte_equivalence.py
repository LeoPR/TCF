"""RASCUNHO T-CI-3 — gate byte-canonical do caminho Cython compilado.
NAO em tests/ ainda (inspecao do owner). Pre-req: o enabler de 1 linha no
syntax.py (ver draft-syntax-enabler.md). Skip gracioso se accel=False (CI sem
toolchain) -> nao quebra o ambiente pure-Python.
"""
import csv, glob, os
import pytest
from tcf import encode
from tcf.composicional.syntax import M8AVirtualRefsSyntax as M

pytestmark = pytest.mark.skipif(
    not M._detect_compositions_accelerated,
    reason="extensao Cython nao compilada (accel=False) — gate so' onde ha .pyd",
)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def _load(path):
    with open(path, encoding="utf-8") as f:
        r = csv.reader(f); hdr = next(r); cols = {h: [] for h in hdr}
        for row in r:
            for h, v in zip(hdr, row): cols[h].append(v)
    return cols


def _encode_with(detect_fn, data):
    orig = M._detect_compositions
    M._detect_compositions = detect_fn
    try:
        return encode(data)
    finally:
        M._detect_compositions = orig


@pytest.mark.parametrize("path", sorted(glob.glob(os.path.join(
    ROOT, "datasets", "synthetic", "*.csv"))))
def test_pyx_byte_equivalente(path):
    """Cython (.pyd) e pure-Python produzem bytes IDENTICOS (ADR-0020)."""
    cols = _load(path)
    if not cols or not next(iter(cols.values())):
        pytest.skip("dataset vazio")
    cy = M._detect_compositions          # ativo (cython, pois accel=True)
    py = M._detect_compositions_py        # ENABLER: pure-Python salvo no syntax.py
    assert _encode_with(cy, cols) == _encode_with(py, cols)
