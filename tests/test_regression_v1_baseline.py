"""Suite de regressao byte-canonical pra v1.0 baseline.

Snapshot byte-count + RT pra datasets-chave. Qualquer mudanca em
src/tcf/ que mude um byte aqui = regressao. Bytes documentados em:

    experiments/lab/dirty/2026-05-27-baseline-consolidado/METRICS.md

Estrategia (Beizer 1995 — characteristic outputs):
- D1-D9: 9 datasets sinteticos single-col (M10 baseline = 1523B total)
- D17a: 1 dataset sintetico multi-col (322B INVARIANT)

Datasets reais (Adult, TPC-H, wine, beijing, retail) NAO sao baseline
formal aqui — variam com fonte externa (Z:/). Suite separada em
test_real_world_snapshots.py (skip se Z: indisponivel).
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tcf import encode, decode


ROOT = Path(__file__).resolve().parent.parent
DATASETS = ROOT / "datasets" / "synthetic"


D1_D9_BYTES_FROZEN = {
    "D1-emails-simples":    118,
    "D2-emails-quote-id":   166,
    "D3-stress-substring":  177,
    "D4-caos-mix":          113,
    "D5-padroes-multiplos": 281,
    "D6-poucos-em-ruido":   287,
    "D7-aninhamento":       215,
    "D8-cabeca-cauda":      100,
    "D9-frequencia-alta":    66,
}

D1_D9_TOTAL = 1523  # sum acima

D17A_INVARIANT = 322


def _load_single_col(name: str) -> list[str]:
    with (DATASETS / f"{name}.csv").open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def _load_multi_col(name: str) -> dict[str, list[str]]:
    with (DATASETS / f"{name}.csv").open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for row in r:
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


class TestD1D9ByteCanonical:
    """D1-D9 cada um com snapshot frozen."""

    @pytest.mark.parametrize("name,expected_bytes", list(D1_D9_BYTES_FROZEN.items()))
    def test_byte_count_matches_snapshot(self, name, expected_bytes):
        values = _load_single_col(name)
        text = encode(values)
        actual = len(text.encode("utf-8"))
        assert actual == expected_bytes, (
            f"{name}: esperado {expected_bytes}B, obteve {actual}B "
            f"(regressao byte-canonical — atualizar snapshot OU investigar src/tcf)"
        )

    @pytest.mark.parametrize("name", list(D1_D9_BYTES_FROZEN.keys()))
    def test_round_trip(self, name):
        values = _load_single_col(name)
        text = encode(values)
        assert decode(text) == values, f"RT broken em {name}"

    def test_d1_d9_total_invariant(self):
        """Total D1-D9 = 1523B (baseline canonical M10)."""
        total = 0
        for name in D1_D9_BYTES_FROZEN:
            values = _load_single_col(name)
            text = encode(values)
            total += len(text.encode("utf-8"))
        assert total == D1_D9_TOTAL, (
            f"D1-D9 total mudou: esperado {D1_D9_TOTAL}B, obteve {total}B"
        )


class TestD17AInvariant:
    """D17a multi-col 322B INVARIANT (testado em 16 ADRs)."""

    def test_d17a_exact_322_bytes(self):
        cols = _load_multi_col("D17a-multi-column-mixed")
        text = encode(cols)
        actual = len(text.encode("utf-8"))
        assert actual == D17A_INVARIANT, (
            f"D17a 322B INVARIANT BROKEN: obteve {actual}B "
            f"(regressao critica — todos ADRs 0011-0016 preservaram este valor)"
        )

    def test_d17a_round_trip(self):
        cols = _load_multi_col("D17a-multi-column-mixed")
        text = encode(cols)
        assert decode(text) == cols
