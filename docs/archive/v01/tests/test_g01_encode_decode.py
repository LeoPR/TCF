"""G01 — Encode/Decode test suite: progressive complexity.

Chapters:
  Ch1  L0  Single column (no PK, no numeric)
  Ch2  L1  Key-value (PK + text)
  Ch3  L2  Numeric (integers and floats)
  Ch4  L3  Multi-type (text + int + float mixed)
  Ch5  L4  FK relationships (two tables)
  Ch6  L5  RLE compression (heavy repetition)
  Ch7  L6  Edge cases (zeros, negatives, large numbers)
  Ch8  Encoding variants (int_scaled, bins_16, FK modes)
  Ch9  TCF output structure (header, comments, syntax)
  Ch10 Stats and telemetry (include_stats, encode_with_report)

Each chapter tests:
  - Encode produces valid string
  - Decode recovers original data
  - Round-trip: encode → decode → compare with original
"""

import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tcf.encoder import encode, encode_with_report, EncoderConfig, EncodeReport
from tcf.decoder import decode
from tests.fixtures import (
    l0_single_column,
    l1_key_value,
    l2_numeric,
    l3_multi_type,
    l4_two_tables_fk,
    l5_rle_heavy,
    l6_edge_cases,
)


# =========================================================================
# Helpers
# =========================================================================

def _roundtrip(meta, data_dir, expected, config=None):
    """Encode → decode → compare with expected data."""
    tcf_text = encode(meta, data_dir, config=config)
    assert isinstance(tcf_text, str)
    assert len(tcf_text) > 0

    tables = decode(tcf_text)
    assert isinstance(tables, dict)

    return tcf_text, tables


def _compare_rows(got_rows, expected_rows, numeric_tol=0.0):
    """Compare decoded rows with expected, with optional numeric tolerance."""
    assert len(got_rows) == len(expected_rows), (
        f"Row count mismatch: got {len(got_rows)}, expected {len(expected_rows)}"
    )
    for i, (got, exp) in enumerate(zip(got_rows, expected_rows)):
        for key in exp:
            assert key in got, f"Row {i}: missing column '{key}'"
            g = got[key]
            e = exp[key]
            if numeric_tol > 0:
                try:
                    diff = abs(float(g) - float(e))
                    assert diff <= numeric_tol, (
                        f"Row {i}, col '{key}': {g} vs {e} (diff={diff} > tol={numeric_tol})"
                    )
                    continue
                except (ValueError, TypeError):
                    pass
            assert g == e, f"Row {i}, col '{key}': got {g!r}, expected {e!r}"


# =========================================================================
# Ch1 — L0: Single column (no PK, no numeric)
# =========================================================================

class TestCh1SingleColumn:
    """L0: simplest possible table — just names in one column."""

    def test_encode_produces_string(self):
        meta, data_dir, _ = l0_single_column()
        tcf = encode(meta, data_dir)
        assert isinstance(tcf, str)
        assert "frutas" in tcf

    def test_contains_table_header(self):
        meta, data_dir, _ = l0_single_column()
        tcf = encode(meta, data_dir)
        assert "## frutas n=3" in tcf

    def test_contains_column_values(self):
        meta, data_dir, _ = l0_single_column()
        tcf = encode(meta, data_dir)
        assert "Banana" in tcf
        assert "Maca" in tcf
        assert "Uva" in tcf

    def test_roundtrip_preserves_data(self):
        meta, data_dir, expected = l0_single_column()
        _, tables = _roundtrip(meta, data_dir, expected)
        assert "frutas" in tables
        _compare_rows(tables["frutas"], expected["frutas"])

    def test_row_count(self):
        meta, data_dir, expected = l0_single_column()
        _, tables = _roundtrip(meta, data_dir, expected)
        assert len(tables["frutas"]) == 3


# =========================================================================
# Ch2 — L1: Key-value (PK + text)
# =========================================================================

class TestCh2KeyValue:
    """L1: table with primary key + text column."""

    def test_pk_marked_with_key(self):
        meta, data_dir, _ = l1_key_value()
        tcf = encode(meta, data_dir)
        assert "id[key]:" in tcf

    def test_roundtrip_preserves_pk(self):
        meta, data_dir, expected = l1_key_value()
        _, tables = _roundtrip(meta, data_dir, expected)
        assert "cores" in tables
        ids = [r["id"] for r in tables["cores"]]
        assert ids == ["1", "2", "3"]

    def test_roundtrip_preserves_names(self):
        meta, data_dir, expected = l1_key_value()
        _, tables = _roundtrip(meta, data_dir, expected)
        nomes = [r["nome"] for r in tables["cores"]]
        assert nomes == ["Vermelho", "Azul", "Verde"]

    def test_row_count(self):
        meta, data_dir, expected = l1_key_value()
        _, tables = _roundtrip(meta, data_dir, expected)
        assert len(tables["cores"]) == 3


# =========================================================================
# Ch3 — L2: Numeric (integers and floats)
# =========================================================================

class TestCh3Numeric:
    """L2: table with integer and float numeric columns."""

    def test_numeric_values_in_output(self):
        meta, data_dir, _ = l2_numeric()
        tcf = encode(meta, data_dir)
        # Integers should be compact (70, not 70.0)
        assert "70" in tcf
        # Floats should be present
        assert "1.75" in tcf

    def test_roundtrip_integers(self):
        meta, data_dir, expected = l2_numeric()
        _, tables = _roundtrip(meta, data_dir, expected)
        pesos = [r["peso"] for r in tables["medidas"]]
        # Integers may come back as "70" or "70.0" — check numeric equivalence
        assert [float(p) for p in pesos] == [70, 85, 60, 90, 55]

    def test_roundtrip_floats(self):
        meta, data_dir, expected = l2_numeric()
        _, tables = _roundtrip(meta, data_dir, expected)
        alturas = [float(r["altura"]) for r in tables["medidas"]]
        assert alturas == [1.75, 1.80, 1.65, 1.92, 1.58]

    def test_row_count(self):
        meta, data_dir, expected = l2_numeric()
        _, tables = _roundtrip(meta, data_dir, expected)
        assert len(tables["medidas"]) == 5


# =========================================================================
# Ch4 — L3: Multi-type (text + int + float)
# =========================================================================

class TestCh4MultiType:
    """L3: table with mixed types in one table."""

    def test_all_columns_present(self):
        meta, data_dir, _ = l3_multi_type()
        tcf = encode(meta, data_dir)
        assert "nome:" in tcf
        assert "qtd:" in tcf
        assert "preco:" in tcf

    def test_roundtrip_text_column(self):
        meta, data_dir, expected = l3_multi_type()
        _, tables = _roundtrip(meta, data_dir, expected)
        nomes = [r["nome"] for r in tables["produtos"]]
        assert nomes == ["Caneta", "Caderno", "Borracha", "Lapis"]

    def test_roundtrip_int_column(self):
        meta, data_dir, expected = l3_multi_type()
        _, tables = _roundtrip(meta, data_dir, expected)
        qtds = [float(r["qtd"]) for r in tables["produtos"]]
        assert qtds == [100, 50, 200, 150]

    def test_roundtrip_float_column(self):
        meta, data_dir, expected = l3_multi_type()
        _, tables = _roundtrip(meta, data_dir, expected)
        precos = [float(r["preco"]) for r in tables["produtos"]]
        assert precos == [2.50, 12.90, 1.00, 0.75]


# =========================================================================
# Ch5 — L4: FK relationships (two tables)
# =========================================================================

class TestCh5ForeignKey:
    """L4: two tables with FK relationship."""

    def test_both_tables_in_output(self):
        meta, data_dir, _ = l4_two_tables_fk()
        tcf = encode(meta, data_dir)
        assert "## categorias" in tcf
        assert "## itens" in tcf

    def test_fk_column_present(self):
        meta, data_dir, _ = l4_two_tables_fk()
        tcf = encode(meta, data_dir)
        assert "id_categoria:" in tcf

    def test_sorted_fk_has_rle(self):
        meta, data_dir, _ = l4_two_tables_fk()
        tcf = encode(meta, data_dir)
        # id_categoria values [1,1,2,2,1] sorted = [1,1,1,2,2] → RLE "3:1 2:2"
        assert "id_categoria[sorted]:" in tcf

    def test_roundtrip_preserves_both_tables(self):
        meta, data_dir, expected = l4_two_tables_fk()
        _, tables = _roundtrip(meta, data_dir, expected)
        assert "categorias" in tables
        assert "itens" in tables
        assert len(tables["categorias"]) == 2
        assert len(tables["itens"]) == 5

    def test_roundtrip_fk_values(self):
        meta, data_dir, expected = l4_two_tables_fk()
        _, tables = _roundtrip(meta, data_dir, expected)
        fk_vals = [r["id_categoria"] for r in tables["itens"]]
        assert fk_vals == ["1", "1", "2", "2", "1"]

    def test_roundtrip_data_values(self):
        meta, data_dir, expected = l4_two_tables_fk()
        _, tables = _roundtrip(meta, data_dir, expected)
        items = [r["item"] for r in tables["itens"]]
        assert items == ["Caneta", "Grampeador", "Prato", "Copo", "Papel"]


# =========================================================================
# Ch6 — L5: RLE compression (heavy repetition)
# =========================================================================

class TestCh6RLE:
    """L5: data with lots of repetition — tests RLE compression."""

    def test_sorted_column_uses_rle(self):
        meta, data_dir, _ = l5_rle_heavy()
        tcf = encode(meta, data_dir)
        # id_loja sorted = [1,1,1,1,1,1,1,2,2,2] → "7:1 3:2"
        assert "id_loja[sorted]:" in tcf
        sorted_line = [l for l in tcf.splitlines() if "id_loja[sorted]:" in l][0]
        assert "7:1" in sorted_line
        assert "3:2" in sorted_line

    def test_rle_compression_ratio(self):
        meta, data_dir, _ = l5_rle_heavy()
        tcf = encode(meta, data_dir)
        sorted_line = [l for l in tcf.splitlines() if "id_loja[sorted]:" in l][0]
        # RLE should be shorter than expanded (10 values → 2 tokens)
        values_part = sorted_line.split(": ", 1)[1]
        tokens = values_part.split()
        assert len(tokens) <= 3  # "7:1 3:2" = 2 tokens

    def test_roundtrip_preserves_all_rows(self):
        meta, data_dir, expected = l5_rle_heavy()
        _, tables = _roundtrip(meta, data_dir, expected)
        assert len(tables["vendas_rep"]) == 10

    def test_roundtrip_preserves_fk_values(self):
        meta, data_dir, expected = l5_rle_heavy()
        _, tables = _roundtrip(meta, data_dir, expected)
        fk_vals = [r["id_loja"] for r in tables["vendas_rep"]]
        assert fk_vals == ["1", "1", "1", "1", "1", "2", "2", "2", "1", "1"]

    def test_roundtrip_preserves_numeric(self):
        meta, data_dir, expected = l5_rle_heavy()
        _, tables = _roundtrip(meta, data_dir, expected)
        vls = [float(r["vl"]) for r in tables["vendas_rep"]]
        expected_vls = [10, 20, 10, 30, 10, 20, 20, 30, 10, 10]
        assert vls == expected_vls


# =========================================================================
# Ch7 — L6: Edge cases
# =========================================================================

class TestCh7EdgeCases:
    """L6: zeros, negatives, large numbers."""

    def test_zero_value_preserved(self):
        meta, data_dir, expected = l6_edge_cases()
        _, tables = _roundtrip(meta, data_dir, expected)
        # valor "0.00" → compact "0" → decode "0" → float 0.0
        vals = [float(r["valor"]) for r in tables["dados"]]
        assert vals[0] == 0.0

    def test_negative_value_preserved(self):
        meta, data_dir, expected = l6_edge_cases()
        _, tables = _roundtrip(meta, data_dir, expected)
        vals = [float(r["valor"]) for r in tables["dados"]]
        assert vals[1] == -5.50

    def test_large_value_preserved(self):
        meta, data_dir, expected = l6_edge_cases()
        _, tables = _roundtrip(meta, data_dir, expected)
        vals = [float(r["valor"]) for r in tables["dados"]]
        assert vals[2] == 1000.99

    def test_small_value_preserved(self):
        meta, data_dir, expected = l6_edge_cases()
        _, tables = _roundtrip(meta, data_dir, expected)
        vals = [float(r["valor"]) for r in tables["dados"]]
        assert vals[3] == 0.01

    def test_negative_integer_preserved(self):
        meta, data_dir, expected = l6_edge_cases()
        _, tables = _roundtrip(meta, data_dir, expected)
        notas = [float(r["nota"]) for r in tables["dados"]]
        assert notas == [10, 0, 7, -3]

    def test_text_columns_preserved(self):
        meta, data_dir, expected = l6_edge_cases()
        _, tables = _roundtrip(meta, data_dir, expected)
        nomes = [r["nome"] for r in tables["dados"]]
        assert nomes == ["Joao", "Maria", "Jose", "Ana"]


# =========================================================================
# Ch8 — Encoding variants
# =========================================================================

class TestCh8Variants:
    """Encoding variants applied to L2 (numeric data)."""

    def test_int_scaled_roundtrip(self):
        meta, data_dir, expected = l2_numeric()
        cfg = EncoderConfig(numeric="int_scaled", int_scale=100)
        tcf_text, tables = _roundtrip(meta, data_dir, expected, config=cfg)
        # SCALE comment should be present
        assert "# SCALE factor=100" in tcf_text
        # Values should roundtrip within tolerance
        alturas = [float(r["altura"]) for r in tables["medidas"]]
        expected_alturas = [1.75, 1.80, 1.65, 1.92, 1.58]
        for got, exp in zip(alturas, expected_alturas):
            assert abs(got - exp) <= 0.01, f"{got} vs {exp}"

    def test_int_scaled_produces_integers_in_output(self):
        meta, data_dir, _ = l2_numeric()
        cfg = EncoderConfig(numeric="int_scaled", int_scale=100)
        tcf = encode(meta, data_dir, config=cfg)
        # altura 1.75 * 100 = 175 (integer in output)
        assert "175" in tcf

    def test_bins_roundtrip_approximate(self):
        meta, data_dir, expected = l2_numeric()
        cfg = EncoderConfig(numeric="bins_16", n_bins=8)
        tcf_text, tables = _roundtrip(meta, data_dir, expected, config=cfg)
        # BINS comment should be present
        assert "# BINS" in tcf_text
        # Values should be approximate (lossy)
        alturas = [float(r["altura"]) for r in tables["medidas"]]
        expected_alturas = [1.75, 1.80, 1.65, 1.92, 1.58]
        max_range = 1.92 - 1.58
        bin_width = max_range / 8
        for got, exp in zip(alturas, expected_alturas):
            assert abs(got - exp) <= bin_width, f"{got} vs {exp} (bin_width={bin_width})"

    def test_no_sorted_omits_sorted_columns(self):
        meta, data_dir, _ = l4_two_tables_fk()
        cfg = EncoderConfig(include_sorted=False)
        tcf = encode(meta, data_dir, config=cfg)
        assert "[sorted]" not in tcf.split("\n", 5)[-1]  # skip header comments

    def test_fk_dict_emits_dict_block(self):
        meta, data_dir, _ = l4_two_tables_fk()
        cfg = EncoderConfig(fk_mode="dict")
        tcf = encode(meta, data_dir, config=cfg)
        assert "## DICT" in tcf
        assert "1=Escritorio" in tcf
        assert "2=Cozinha" in tcf

    def test_fk_inline_resolves_names(self):
        meta, data_dir, _ = l4_two_tables_fk()
        cfg = EncoderConfig(fk_mode="inline")
        tcf = encode(meta, data_dir, config=cfg)
        assert "Escritorio" in tcf
        assert "Cozinha" in tcf
        # Original FK column name should be simplified
        assert "categoria:" in tcf  # id_categoria → categoria

    def test_fk_hint_emits_hint(self):
        meta, data_dir, _ = l4_two_tables_fk()
        cfg = EncoderConfig(fk_mode="hint")
        tcf = encode(meta, data_dir, config=cfg)
        assert "> id_categoria ref" in tcf


# =========================================================================
# Ch9 — TCF output structure
# =========================================================================

class TestCh9Structure:
    """Verify TCF output structure: header, table blocks, syntax."""

    def test_starts_with_header(self):
        meta, data_dir, _ = l1_key_value()
        tcf = encode(meta, data_dir)
        assert tcf.startswith("# TCF v0.1")

    def test_header_contains_rle_explanation(self):
        meta, data_dir, _ = l1_key_value()
        tcf = encode(meta, data_dir)
        assert "N:val" in tcf

    def test_table_block_format(self):
        meta, data_dir, _ = l1_key_value()
        tcf = encode(meta, data_dir)
        # Table header: ## name n=count
        assert "## cores n=3" in tcf

    def test_pk_column_has_key_marker(self):
        meta, data_dir, _ = l1_key_value()
        tcf = encode(meta, data_dir)
        assert "id[key]:" in tcf

    def test_column_format_is_name_colon_values(self):
        meta, data_dir, _ = l3_multi_type()
        tcf = encode(meta, data_dir)
        # Each column line: "col_name: val1 val2 val3"
        lines = [l for l in tcf.splitlines() if l.startswith("nome:")]
        assert len(lines) == 1
        assert "Caneta" in lines[0]

    def test_no_empty_tables_in_output(self):
        meta, data_dir, _ = l2_numeric()
        tcf = encode(meta, data_dir)
        # Should have exactly one table block
        table_headers = [l for l in tcf.splitlines() if l.startswith("## ")]
        assert len(table_headers) == 1

    def test_ends_with_newline(self):
        meta, data_dir, _ = l1_key_value()
        tcf = encode(meta, data_dir)
        assert tcf.endswith("\n")


# =========================================================================
# Ch10 — Stats and telemetry
# =========================================================================

class TestCh10Stats:
    """include_stats flag and encode_with_report telemetry."""

    # -- Stats in TCF output --

    def test_stats_disabled_by_default(self):
        meta, data_dir, _ = l2_numeric()
        tcf = encode(meta, data_dir)
        assert "# STATS" not in tcf

    def test_stats_numeric_present_when_enabled(self):
        meta, data_dir, _ = l2_numeric()
        cfg = EncoderConfig(include_stats=True)
        tcf = encode(meta, data_dir, config=cfg)
        stats_lines = [l for l in tcf.splitlines() if l.startswith("# STATS")]
        assert len(stats_lines) >= 1

    def test_stats_numeric_contains_fields(self):
        meta, data_dir, _ = l2_numeric()
        cfg = EncoderConfig(include_stats=True)
        tcf = encode(meta, data_dir, config=cfg)
        # Find the peso stats line
        peso_stats = [l for l in tcf.splitlines() if "# STATS peso" in l]
        assert len(peso_stats) == 1
        line = peso_stats[0]
        assert "n=5" in line
        assert "sum=" in line
        assert "min=" in line
        assert "max=" in line
        assert "avg=" in line

    def test_stats_numeric_correct_values(self):
        meta, data_dir, _ = l2_numeric()
        cfg = EncoderConfig(include_stats=True)
        tcf = encode(meta, data_dir, config=cfg)
        peso_stats = [l for l in tcf.splitlines() if "# STATS peso" in l][0]
        # pesos: 70, 85, 60, 90, 55 -> sum=360, min=55, max=90, avg=72
        assert "sum=360" in peso_stats
        assert "min=55" in peso_stats
        assert "max=90" in peso_stats

    def test_stats_categorical_has_distinct_and_mode(self):
        meta, data_dir, _ = l3_multi_type()
        cfg = EncoderConfig(include_stats=True)
        tcf = encode(meta, data_dir, config=cfg)
        cat_stats = [l for l in tcf.splitlines() if "# STATS nome" in l]
        assert len(cat_stats) == 1
        line = cat_stats[0]
        assert "distinct=" in line
        assert "mode=" in line

    def test_stats_header_hint(self):
        meta, data_dir, _ = l2_numeric()
        cfg = EncoderConfig(include_stats=True)
        tcf = encode(meta, data_dir, config=cfg)
        assert "# STATS" in tcf
        # Header should mention stats
        header = tcf.split("\n\n")[0]
        assert "STATS" in header

    def test_stats_roundtrip_unaffected(self):
        """Stats are comments — decoder should ignore them."""
        meta, data_dir, expected = l2_numeric()
        cfg = EncoderConfig(include_stats=True)
        _, tables = _roundtrip(meta, data_dir, expected, config=cfg)
        pesos = [float(r["peso"]) for r in tables["medidas"]]
        assert pesos == [70, 85, 60, 90, 55]

    # -- Telemetry (EncodeReport) --

    def test_encode_with_report_returns_report(self):
        meta, data_dir, _ = l2_numeric()
        report = encode_with_report(meta, data_dir)
        assert isinstance(report, EncodeReport)

    def test_report_has_tcf_text(self):
        meta, data_dir, _ = l2_numeric()
        report = encode_with_report(meta, data_dir)
        assert isinstance(report.tcf_text, str)
        assert "## medidas" in report.tcf_text

    def test_report_timing(self):
        meta, data_dir, _ = l2_numeric()
        report = encode_with_report(meta, data_dir)
        assert report.elapsed_s >= 0
        assert report.elapsed_s < 5  # should be < 1s

    def test_report_sizes(self):
        meta, data_dir, _ = l2_numeric()
        report = encode_with_report(meta, data_dir)
        assert report.input_bytes > 0
        assert report.output_bytes > 0
        assert report.output_chars > 0

    def test_report_compression_ratio(self):
        meta, data_dir, _ = l2_numeric()
        report = encode_with_report(meta, data_dir)
        assert report.compression_ratio > 0

    def test_report_tables(self):
        meta, data_dir, _ = l4_two_tables_fk()
        report = encode_with_report(meta, data_dir)
        assert "categorias" in report.tables
        assert "itens" in report.tables
        assert report.tables["categorias"] == 2
        assert report.tables["itens"] == 5

    def test_report_config_captured(self):
        meta, data_dir, _ = l2_numeric()
        cfg = EncoderConfig(numeric="int_scaled", int_scale=100, include_stats=True)
        report = encode_with_report(meta, data_dir, config=cfg)
        assert report.config["numeric"] == "int_scaled"
        assert report.config["int_scale"] == 100
        assert report.config["include_stats"] is True

    def test_report_summary_is_string(self):
        meta, data_dir, _ = l2_numeric()
        report = encode_with_report(meta, data_dir)
        summary = report.summary()
        assert isinstance(summary, str)
        assert "elapsed" in summary
        assert "ratio" in summary
