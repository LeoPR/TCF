"""Roda os testes de contrato do `scripts/bench_perf` dentro da suíte principal.

Eles vivem em `scripts/bench_perf/tests/`, e o pytest da raiz coleta só `tests/`. Por isso o
instrumento que dá base ao `.9` precisa estar aqui: quebrando, a suíte e a CI ficam vermelhas.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from bench_perf.tests import test_contrato as CONTRATO  # noqa: E402


@pytest.mark.parametrize("teste", CONTRATO._todos_testes(), ids=lambda t: t.__name__)
def test_contrato_bench_perf(teste):
    teste()
