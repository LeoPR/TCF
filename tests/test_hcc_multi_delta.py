"""Tests HCC seq-RLE multi-delta fix (ADR-0016, T-CODE-HCC-MULTI-DELTA-FIX).

Bug #2 sub-exp 14: compare_for_seq rejeitava [0,0,0,1] mesmo
estruturalmente compativel.

Fix: aceita multi-run com 1 valor non-zero (resto 0). Marker novo
formato `*N+d1,d2,...|template` (CSV). M10 compat preservado pra
casos uniform delta.
"""

from __future__ import annotations

import pytest

from tcf import encode, decode
from tcf.composicional.hcc_seqrle import (
    compare_for_seq, compact_body, expand_seq_marker, shift_escape_digits,
    _is_uniform_delta,
)


class TestCompareForSeq:
    """Multi-delta detection (Bug #2 fix)."""

    def test_uniform_delta_returns_list(self):
        # Old M10 behavior: single delta -> agora retorna lista
        delta = compare_for_seq("\\10", "\\11")
        assert delta == [1]  # uniform [1] = todos runs com delta 1

    def test_multi_run_with_invariant_prefix_now_accepted(self):
        """Bug #2 fix: pares com prefix invariante + suffix incrementing."""
        a = "\\125.\\114.\\71.\\1"
        b = "\\125.\\114.\\71.\\2"
        deltas = compare_for_seq(a, b)
        assert deltas == [0, 0, 0, 1]

    def test_multi_run_same_delta_all(self):
        # Todos runs com mesmo delta (uniform multi-run)
        # Hipotetico: prefix tambem incrementing
        a = "\\1.\\1"
        b = "\\2.\\2"
        deltas = compare_for_seq(a, b)
        assert deltas == [1, 1]

    def test_all_zero_rejected(self):
        delta = compare_for_seq("\\10.\\20", "\\10.\\20")  # identicas
        assert delta is None

    def test_multiple_non_zero_rejected_fase_2(self):
        # [1, 2] -> 2 non-zero diferentes -> Fase 2 reject
        a = "\\10.\\20"
        b = "\\11.\\22"
        deltas = compare_for_seq(a, b)
        assert deltas is None


class TestUniformDeltaHelper:
    def test_uniform_single_non_zero(self):
        assert _is_uniform_delta([1]) == 1
        assert _is_uniform_delta([1, 1]) == 1
        assert _is_uniform_delta([5, 5, 5]) == 5

    def test_mixed_not_uniform(self):
        assert _is_uniform_delta([0, 0, 0, 1]) is None
        assert _is_uniform_delta([1, 0, 1]) is None

    def test_all_zero_not_uniform(self):
        assert _is_uniform_delta([0, 0, 0]) is None


class TestShiftEscapeDigits:
    def test_single_int_compat(self):
        # M10 compat: int delta -> apply to all runs
        result = shift_escape_digits("\\10.\\20", 1)
        assert result == "\\11.\\21"

    def test_list_per_run_delta(self):
        # ADR-0016: list delta -> per-run
        result = shift_escape_digits("\\10.\\20", [1, 0])
        assert result == "\\11.\\20"

    def test_list_multi_run_mixed(self):
        result = shift_escape_digits("\\125.\\114.\\71.\\1", [0, 0, 0, 1])
        assert result == "\\125.\\114.\\71.\\2"


class TestExpandSeqMarker:
    def test_m10_single_delta_compat(self):
        # M10 format `*N+delta|template` ainda funciona
        out = expand_seq_marker("*3+1|\\10")
        assert out == ["\\10", "\\11", "\\12"]

    def test_adr0016_multi_delta(self):
        # Novo formato `*N+d1,d2,d3,d4|template`
        out = expand_seq_marker("*3+0,0,0,1|\\125.\\114.\\71.\\1")
        assert out == [
            "\\125.\\114.\\71.\\1",
            "\\125.\\114.\\71.\\2",
            "\\125.\\114.\\71.\\3",
        ]

    def test_count_zero_returns_template_only(self):
        out = expand_seq_marker("*1+1|\\5")
        assert out == ["\\5"]


class TestCompactBodyMarkerEmit:
    def test_uniform_emits_m10_single_format(self):
        # 3 lines com uniform delta -> marker single (M10 compat)
        body = ["\\10", "\\11", "\\12"]
        compacted, info = compact_body(body)
        assert len(compacted) == 1
        # M10 format: `*N+delta|template` (sem virgula)
        assert ',' not in compacted[0].split('|')[0]
        assert compacted[0] == "*3+1|\\10"

    def test_multi_delta_emits_csv_format(self):
        # 3 lines com prefix invariante + suffix incrementing
        body = [
            "\\125.\\114.\\71.\\1",
            "\\125.\\114.\\71.\\2",
            "\\125.\\114.\\71.\\3",
        ]
        compacted, info = compact_body(body)
        assert len(compacted) == 1
        # CSV format: `*N+d1,d2,d3,d4|template`
        marker = compacted[0]
        head = marker.split('|')[0]
        assert ',' in head
        assert marker == "*3+0,0,0,1|\\125.\\114.\\71.\\1"


class TestRTRoundTripMultiDelta:
    def test_round_trip_basic_multi_delta(self):
        body = [
            "\\125.\\114.\\71.\\1",
            "\\125.\\114.\\71.\\2",
            "\\125.\\114.\\71.\\3",
        ]
        compacted, _ = compact_body(body)
        # Expand back
        for line in compacted:
            expanded = expand_seq_marker(line)
            if expanded is not None:
                assert expanded == body


class TestEndToEndIPSubnetWithoutNature:
    """Bug #2 fix: D-IP-subnet sem nature comprimme dramaticamente."""

    def test_d_ip_subnet_1000_dramatically_compressed(self):
        """Sub-exp 14 reportava 117% ratio; fix esperado leva pra <5%."""
        from pathlib import Path
        import csv

        ds = (Path(__file__).resolve().parent.parent /
              "experiments/lab/dirty/2026-05-24-cpf-templated-checked/"
              "data/D-IP-subnet.csv")
        if not ds.exists():
            pytest.skip("D-IP-subnet.csv nao disponivel")
        with ds.open(encoding="utf-8") as f:
            r = csv.reader(f)
            next(r)
            ips = [row[0] for row in r if row]
        assert len(ips) == 1000

        text = encode(ips)
        n_bytes = len(text.encode("utf-8"))
        raw_bytes = sum(len(v.encode("utf-8")) for v in ips) + len(ips)
        ratio = n_bytes / raw_bytes * 100

        # Esperado: ratio <= 10% (vs 117% pre-fix)
        # Medicao real: ~4.18%
        assert ratio < 10, (
            f"D-IP-subnet 1000 sem nature: esperado ratio < 10%, "
            f"got {ratio:.2f}% ({n_bytes}B/{raw_bytes}B). "
            f"Bug #2 fix pode ter regredido."
        )

        # RT obrigatorio
        decoded = decode(text)
        assert decoded == ips, "RT FAIL no D-IP-subnet 1000"

    def test_d17a_invariant_preserved(self):
        """Regression: D17a 322B INVARIANT preservado pos-fix."""
        from pathlib import Path
        import csv

        ds = (Path(__file__).resolve().parent.parent /
              "datasets/synthetic/D17a-multi-column-mixed.csv")
        with ds.open(encoding="utf-8") as f:
            r = csv.reader(f)
            header = next(r)
            cols = {h: [] for h in header}
            for row in r:
                for h, v in zip(header, row):
                    cols[h].append(v)
        text = encode(cols)
        assert len(text.encode("utf-8")) == 322
