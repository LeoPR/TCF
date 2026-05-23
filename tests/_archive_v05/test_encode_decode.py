"""TCF encode/decode roundtrip tests for all compression levels.

Tests:
  - Each level (0-3) encodes and decodes without data loss
  - Compression sizes are as expected (level 2 < level 0)
  - CLI commands work
  - Real data (41 vendas) and synthetic data
"""

import csv as csv_mod
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tcf import encode, decode, EncodeConfig

DATA_DIR = ROOT / "data"
META = DATA_DIR / "metadata.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _original_vendas() -> list[tuple[str, str, float]]:
    """Load original vendas as (pessoa, produto, vl) tuples."""
    pessoas = {r["id"]: r["nome"] for r in csv_mod.DictReader(
        open(DATA_DIR / "pessoas.csv", encoding="utf-8"))}
    produtos = {r["id"]: r["nome"] for r in csv_mod.DictReader(
        open(DATA_DIR / "produtos.csv", encoding="utf-8"))}
    vendas = list(csv_mod.DictReader(
        open(DATA_DIR / "vendas.csv", encoding="utf-8")))
    return sorted(
        (pessoas[v["id_pessoa"]], produtos[v["id_produto"]], float(v["vl"]))
        for v in vendas
    )


def _decoded_vendas(tcf_text: str) -> list[tuple[str, str, float]]:
    """Decode TCF and return vendas as sorted (pessoa, produto, vl) tuples."""
    tables = decode(tcf_text, normalize=False)
    name = list(tables.keys())[0]
    rows = tables[name]
    return sorted(
        (r["pessoa"], r["produto"], float(r["vl"]))
        for r in rows
    )


# ---------------------------------------------------------------------------
# Roundtrip tests per level
# ---------------------------------------------------------------------------

class TestRoundtripLevel0:
    """Level 0: expanded, no compression."""

    def test_roundtrip(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=0, include_stats=False))
        assert _decoded_vendas(text) == _original_vendas()

    def test_has_header(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=0))
        assert "# TCF v0.2 level=0" in text

    def test_no_rle(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=0))
        data_lines = [l for l in text.splitlines() if not l.startswith("#") and l.strip()]
        assert not any("*" in l for l in data_lines if not l.endswith(":")), \
            "Level 0 should have no RLE"


class TestRoundtripLevel1:
    """Level 1: RLE without sorting."""

    def test_roundtrip(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=1, include_stats=False))
        assert _decoded_vendas(text) == _original_vendas()

    def test_has_rle_header(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=1))
        assert "N*val" in text


class TestRoundtripLevel2:
    """Level 2: sorted + RLE (default, recommended)."""

    def test_roundtrip(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=2, include_stats=False))
        assert _decoded_vendas(text) == _original_vendas()

    def test_has_sorted_by(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=2))
        assert "sorted_by=" in text

    def test_has_rle_groups(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=2))
        rle_lines = [l for l in text.splitlines() if "*" in l and not l.startswith("#")]
        assert len(rle_lines) > 0, "Level 2 should have RLE groups"

    def test_smaller_than_level0(self):
        t0 = encode(META, DATA_DIR, EncodeConfig(level=0, include_stats=False))
        t2 = encode(META, DATA_DIR, EncodeConfig(level=2, include_stats=False))
        assert len(t2) < len(t0), f"Level 2 ({len(t2)}) should be smaller than level 0 ({len(t0)})"


class TestRoundtripLevel3:
    """Level 3: dictionary + sorted + RLE."""

    def test_roundtrip(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=3, include_stats=False))
        assert _decoded_vendas(text) == _original_vendas()

    def test_has_dict_lines(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=3))
        dict_lines = [l for l in text.splitlines() if l.startswith("# dict ")]
        assert len(dict_lines) > 0, "Level 3 should have dict lines"


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TestStats:
    """STATS hint lines."""

    def test_stats_present_by_default(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=2))
        assert "# STATS vl:" in text

    def test_stats_can_be_disabled(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=2, include_stats=False))
        assert "# STATS" not in text

    def test_stats_values_correct(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=2))
        for line in text.splitlines():
            if "# STATS vl:" in line:
                assert "n=41" in line
                assert "sum=217.6" in line
                assert "min=1" in line
                assert "max=12.4" in line


# ---------------------------------------------------------------------------
# Normalization (decode to 3 tables)
# ---------------------------------------------------------------------------

class TestNormalize:
    """Decode with normalize=True rebuilds reference tables."""

    def test_normalize_creates_ref_tables(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=2, include_stats=False))
        tables = decode(text, normalize=True)
        assert "pessoa" in tables
        assert "produto" in tables

    def test_normalize_correct_counts(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=2, include_stats=False))
        tables = decode(text, normalize=True)
        assert len(tables["pessoa"]) == 30
        assert len(tables["produto"]) == 12

    def test_flat_mode(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=2, include_stats=False))
        tables = decode(text, normalize=False)
        name = list(tables.keys())[0]
        assert len(tables[name]) == 41
        assert "pessoa" in tables[name][0]


# ---------------------------------------------------------------------------
# Size comparison
# ---------------------------------------------------------------------------

class TestSizes:
    """Verify compression actually compresses."""

    def test_level2_smaller_than_csv(self):
        text = encode(META, DATA_DIR, EncodeConfig(level=2, include_stats=False))
        # CSV baseline
        csv_rows = _original_vendas()
        csv_text = "pessoa,produto,vl\n" + "\n".join(
            f"{p},{pr},{v}" for p, pr, v in csv_rows
        )
        assert len(text) < len(csv_text), \
            f"Level 2 ({len(text)}) should be smaller than CSV ({len(csv_text)})"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCLI:
    """CLI encode/decode commands."""

    def test_encode_stdout(self):
        result = subprocess.run(
            [sys.executable, "-m", "tcf", "encode",
             "--meta", str(META), "--data-dir", str(DATA_DIR), "--level", "2"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "## vendas" in result.stdout

    def test_encode_decode_roundtrip(self, tmp_path):
        # Encode
        tcf_file = tmp_path / "test.tcf"
        result = subprocess.run(
            [sys.executable, "-m", "tcf", "encode",
             "--meta", str(META), "--data-dir", str(DATA_DIR),
             "--level", "2", "--out", str(tcf_file)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

        # Decode
        out_dir = tmp_path / "restored"
        result = subprocess.run(
            [sys.executable, "-m", "tcf", "decode", str(tcf_file),
             "--out-dir", str(out_dir)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

        # Verify vendas.csv exists
        vendas_csv = out_dir / "vendas.csv"
        assert vendas_csv.exists()
        rows = list(csv_mod.DictReader(vendas_csv.open(encoding="utf-8")))
        assert len(rows) == 41

    def test_info(self, tmp_path):
        tcf_file = tmp_path / "test.tcf"
        subprocess.run(
            [sys.executable, "-m", "tcf", "encode",
             "--meta", str(META), "--data-dir", str(DATA_DIR),
             "--level", "2", "--out", str(tcf_file)],
            capture_output=True, text=True,
        )
        result = subprocess.run(
            [sys.executable, "-m", "tcf", "info", str(tcf_file)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "vendas" in result.stdout
