"""Tests parallelism (T-CODE-ENCODER-MANAGER Fase 1).

Valida:
- Output byte-identico vs serial (paralelismo NAO muda bytes)
- D17a 322B INVARIANT preservado em modo parallel
- RT OK em parallel
- SideOutputs capturado per-col
- single-col list ignora parallel (no-op)
- dict 1-col threshold filtra (parallel_workers=0)
- N workers explicito respeitado
- parallel=True / parallel=N / parallel=False / parallel=0

Conexao:
- T-CODE-ENCODER-MANAGER Fase 1
- ADR-0014 (API unificada, parallel adicionado em sub-fase)
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tcf import encode, decode, SideOutputs


ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = ROOT / "datasets" / "synthetic"


def _ler_csv_multi(name: str) -> dict[str, list[str]]:
    with (DATASETS_DIR / f"{name}.csv").open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for row in r:
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


class TestParallelByteIdentical:
    """Output em parallel = output em serial (byte-identical)."""

    def test_d17a_parallel_true_identical_to_serial(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        text_serial = encode(table)
        text_parallel = encode(table, parallel=True)
        assert text_serial == text_parallel

    def test_d17a_parallel_2_identical_to_serial(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        text_serial = encode(table)
        text_p2 = encode(table, parallel=2)
        assert text_serial == text_p2

    def test_d17a_parallel_4_identical_to_serial(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        text_serial = encode(table)
        text_p4 = encode(table, parallel=4)
        assert text_serial == text_p4

    def test_d17a_total_bytes_invariant_in_parallel(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        text = encode(table, parallel=True)
        assert len(text.encode("utf-8")) == 322


class TestParallelRoundTrip:
    def test_rt_parallel(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        text = encode(table, parallel=True)
        assert decode(text) == table

    def test_rt_many_columns(self):
        table = {f"col{i}": [f"v{i}_{j}" for j in range(20)] for i in range(8)}
        text = encode(table, parallel=True)
        assert decode(text) == table


class TestParallelSideOutputs:
    def test_side_outputs_in_parallel_mode(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        side = SideOutputs()
        encode(table, side_outputs=side, parallel=True)
        assert side.multi_info is not None
        assert side.per_col is not None
        assert set(side.per_col.keys()) == {"timestamp", "id", "email", "categoria"}
        # Per-col side captado mesmo em workers
        assert side.per_col["timestamp"].column_features is not None
        assert side.per_col["timestamp"].cadence_detected is True
        assert side.per_col["timestamp"].body_bytes is not None

    def test_parallel_workers_reported_in_multi_info(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        side = SideOutputs()
        encode(table, side_outputs=side, parallel=2)
        assert side.multi_info["parallel_workers"] == 2

    def test_serial_mode_reports_zero_workers(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        side = SideOutputs()
        encode(table, side_outputs=side, parallel=False)
        assert side.multi_info["parallel_workers"] == 0


class TestParallelEdgeCases:
    def test_single_col_list_ignores_parallel(self):
        text = encode(["a", "b", "c"], parallel=True)
        assert decode(text) == ["a", "b", "c"]

    def test_dict_1col_does_not_parallelize(self):
        side = SideOutputs()
        encode({"x": ["1", "2"]}, parallel=True, side_outputs=side)
        # Threshold: 1 coluna nao vale paralelizar
        assert side.multi_info["parallel_workers"] == 0

    def test_parallel_zero_falls_back_to_serial(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        side = SideOutputs()
        text = encode(table, parallel=0, side_outputs=side)
        assert side.multi_info["parallel_workers"] == 0
        # Output ainda valido
        assert decode(text) == table

    def test_parallel_n_capped_to_n_cols(self):
        # parallel=10 com 4 cols => cap em 4
        table = _ler_csv_multi("D17a-multi-column-mixed")
        side = SideOutputs()
        encode(table, parallel=10, side_outputs=side)
        assert side.multi_info["parallel_workers"] == 4

    def test_parallel_default_is_false(self):
        # Sem argumento, parallel=False default
        table = _ler_csv_multi("D17a-multi-column-mixed")
        side = SideOutputs()
        encode(table, side_outputs=side)
        assert side.multi_info["parallel_workers"] == 0
