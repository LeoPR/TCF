"""T-CI-3 — gate byte-canonical do caminho Cython COMPILADO (ADR-0020).

`src/tcf/_core/detect.pyx` (acelerador opcional) e o fallback pure-Python DEVEM
produzir bytes IDENTICOS. A suite normal roda accel=False (sem `.pyd`) e NAO cobre
isto — um espelho `.pyx` divergente passaria tudo localmente e quebraria so' onde a
extensao esta' compilada (wheel/CI). Este gate compara os DOIS caminhos no MESMO
processo e roda SO' onde a extensao compilou (skip gracioso senao).

Enabler: `M8AVirtualRefsSyntax._detect_compositions_py` (salvo em syntax.py ANTES do
override). Cobertura: datasets sinteticos + fixtures real-world (committadas em
datasets/samples/, regime n_tam_est>=3) + inputs aleatorios.
"""
from __future__ import annotations

import csv
import glob
import random
from pathlib import Path

import pytest

from tcf import encode
from tcf.composicional.syntax import M8AVirtualRefsSyntax as M

pytestmark = pytest.mark.skipif(
    not M._detect_compositions_accelerated,
    reason="extensao Cython nao compilada (accel=False) — gate so' com o .pyd presente",
)

ROOT = Path(__file__).resolve().parent.parent
_CY = M._detect_compositions          # cython (ativo, accel=True)
_PY = M._detect_compositions_py        # pure-Python (enabler)


def _encode_with(detect_fn, data):
    orig = M._detect_compositions
    M._detect_compositions = detect_fn
    try:
        return encode(data)
    finally:
        M._detect_compositions = orig


def _assert_equiv(data):
    cy = _encode_with(_CY, data)
    py = _encode_with(_PY, data)
    assert cy == py, "Cython (.pyx) != pure-Python — divergencia byte-canonical (ADR-0020)"


def _load_multi(path: str) -> dict[str, list[str]]:
    with open(path, encoding="utf-8") as f:
        r = csv.reader(f)
        hdr = next(r)
        cols: dict[str, list[str]] = {h: [] for h in hdr}
        for row in r:
            for h, v in zip(hdr, row):
                cols[h].append(v)
    return cols


# --- sinteticos (multi-col) ---
@pytest.mark.parametrize(
    "path", sorted(glob.glob(str(ROOT / "datasets" / "synthetic" / "*.csv")))
)
def test_synthetic(path):
    cols = _load_multi(path)
    if not cols or not next(iter(cols.values())):
        pytest.skip("dataset vazio")
    _assert_equiv(cols)


# --- real-world (single-col free-text, regime n_tam_est>=3; fixtures committadas) ---
@pytest.mark.parametrize(
    "rel",
    [
        "online-retail/description-2k.csv",
        "online-retail/stockcode-2k.csv",
        "tpch-sf001/lcomment-2k.csv",
    ],
)
def test_real_world(rel):
    path = ROOT / "datasets" / "samples" / rel
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        next(r)  # header
        values = [row[0] for row in r if row]
    _assert_equiv(values)


# --- inputs aleatorios (estressa entradas fora dos datasets fixos) ---
def _rand_col(rng: random.Random, n: int, kind: str) -> list[str]:
    if kind == "words":
        return [
            "".join(rng.choice("abcdefghij") for _ in range(rng.randint(1, 12)))
            for _ in range(n)
        ]
    if kind == "digits":
        return [
            "".join(rng.choice("0123456789") for _ in range(rng.randint(1, 15)))
            for _ in range(n)
        ]
    alpha = "abc0123.-/ "  # mixto: letras, digitos, pontuacao, espaco
    return [
        "".join(rng.choice(alpha) for _ in range(rng.randint(0, 20)))
        for _ in range(n)
    ]


@pytest.mark.parametrize("seed", range(8))
def test_random(seed):
    rng = random.Random(seed)
    kind = rng.choice(["words", "digits", "mixed"])
    _assert_equiv(_rand_col(rng, rng.randint(10, 400), kind))
