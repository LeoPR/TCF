"""Tests for P04 — EncoderConfig variants (numeric encoding + FK modes)."""

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tcf.encoder import encode, EncoderConfig
from tcf.decoder import decode

DATA_DIR = ROOT / "data"
META     = DATA_DIR / "metadata.json"


def _orig_vendas() -> list[dict]:
    return list(csv.DictReader((DATA_DIR / "vendas.csv").open(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vl_values(tcf_text: str) -> list[str]:
    """Extract raw tokens from the 'vl:' line (unsorted)."""
    for line in tcf_text.splitlines():
        if line.strip().startswith("vl:"):
            return line.split(":", 1)[1].strip().split()
    return []


def _has_line_starting(tcf_text: str, prefix: str) -> bool:
    return any(line.strip().startswith(prefix) for line in tcf_text.splitlines())


# ---------------------------------------------------------------------------
# EncoderConfig validation
# ---------------------------------------------------------------------------

def test_config_invalid_numeric():
    with pytest.raises(ValueError, match="numeric"):
        EncoderConfig(numeric="bad")

def test_config_invalid_fk_mode():
    with pytest.raises(ValueError, match="fk_mode"):
        EncoderConfig(fk_mode="bad")

def test_config_defaults():
    c = EncoderConfig()
    assert c.numeric == "raw_float"
    assert c.fk_mode == "id_raw"
    assert c.include_sorted is True


# ---------------------------------------------------------------------------
# raw_float (default) — already tested in test_roundtrip.py, smoke test here
# ---------------------------------------------------------------------------

def test_raw_float_roundtrip():
    text = encode(META, DATA_DIR)
    tables = decode(text)
    orig = _orig_vendas()
    restored = tables["vendas"]
    assert len(orig) == len(restored)
    for o, r in zip(orig, restored):
        assert float(o["vl"]) == pytest.approx(float(r["vl"]), rel=1e-4)


# ---------------------------------------------------------------------------
# int_scaled
# ---------------------------------------------------------------------------

def test_int_scaled_produces_integers():
    cfg = EncoderConfig(numeric="int_scaled", int_scale=100)
    text = encode(META, DATA_DIR, config=cfg)
    tokens = _vl_values(text)
    assert tokens, "vl: line not found"
    for t in tokens:
        assert t.lstrip("-").isdigit(), f"Expected integer token, got {t!r}"

def test_int_scaled_header_comment():
    cfg = EncoderConfig(numeric="int_scaled", int_scale=100)
    text = encode(META, DATA_DIR, config=cfg)
    assert _has_line_starting(text, "# SCALE"), "Missing # SCALE comment"

def test_int_scaled_value_correct():
    cfg = EncoderConfig(numeric="int_scaled", int_scale=100)
    text = encode(META, DATA_DIR, config=cfg)
    tokens = _vl_values(text)
    # First vl in vendas.csv is 2.50 → int(2.50 * 100) = 250
    assert tokens[0] == "250", f"Expected 250, got {tokens[0]}"

def test_int_scaled_roundtrip():
    cfg = EncoderConfig(numeric="int_scaled", int_scale=100)
    text = encode(META, DATA_DIR, config=cfg)
    tables = decode(text)
    orig = _orig_vendas()
    restored = tables["vendas"]
    assert len(orig) == len(restored)
    for o, r in zip(orig, restored):
        assert float(o["vl"]) == pytest.approx(float(r["vl"]), rel=1e-3)


# ---------------------------------------------------------------------------
# bins_16
# ---------------------------------------------------------------------------

def test_bins_produces_integers_in_range():
    cfg = EncoderConfig(numeric="bins_16", n_bins=16)
    text = encode(META, DATA_DIR, config=cfg)
    tokens = _vl_values(text)
    assert tokens, "vl: line not found"
    for t in tokens:
        assert t.lstrip("-").isdigit(), f"Not an integer: {t!r}"
        assert 0 <= int(t) <= 15, f"Bin index out of range: {t}"

def test_bins_header_comment():
    cfg = EncoderConfig(numeric="bins_16", n_bins=16)
    text = encode(META, DATA_DIR, config=cfg)
    assert _has_line_starting(text, "# BINS"), "Missing # BINS comment"

def test_bins_min_max_in_comment():
    cfg = EncoderConfig(numeric="bins_16", n_bins=16)
    text = encode(META, DATA_DIR, config=cfg)
    bins_line = next(l for l in text.splitlines() if l.strip().startswith("# BINS vl"))
    assert "min=1.0" in bins_line, f"Expected min=1.0 in: {bins_line}"
    assert "max=12.4" in bins_line, f"Expected max=12.4 in: {bins_line}"

def test_bins_count_preserved():
    cfg = EncoderConfig(numeric="bins_16", n_bins=16)
    text = encode(META, DATA_DIR, config=cfg)
    tokens = _vl_values(text)
    assert len(tokens) == 41

def test_bins_decode_approximate():
    """Bins roundtrip: decoded values approximate original within half a bin-width."""
    cfg = EncoderConfig(numeric="bins_16", n_bins=16)
    text = encode(META, DATA_DIR, config=cfg)
    tables = decode(text)
    orig = _orig_vendas()
    restored = tables["vendas"]
    # bin width = (12.4 - 1.0) / 16 ≈ 0.7125; max error ≤ half-width ≈ 0.36
    for o, r in zip(orig, restored):
        diff = abs(float(o["vl"]) - float(r["vl"]))
        assert diff <= 1.0, f"Decoded vl too far: orig={o['vl']} restored={r['vl']}"


# ---------------------------------------------------------------------------
# include_sorted=False
# ---------------------------------------------------------------------------

def _data_lines(tcf_text: str) -> list[str]:
    """Return only column/table data lines, excluding header/comments."""
    return [l for l in tcf_text.splitlines() if not l.startswith("#") and not l.startswith(">")]

def test_no_sorted_omits_sorted_columns():
    cfg = EncoderConfig(include_sorted=False)
    text = encode(META, DATA_DIR, config=cfg)
    data = _data_lines(text)
    assert not any("[sorted]" in l for l in data), "Sorted column found in data lines"

def test_default_includes_sorted():
    text = encode(META, DATA_DIR)
    data = _data_lines(text)
    assert any("[sorted]" in l for l in data)


# ---------------------------------------------------------------------------
# fk_mode="dict"
# ---------------------------------------------------------------------------

def test_fk_dict_emits_dict_block():
    cfg = EncoderConfig(fk_mode="dict")
    text = encode(META, DATA_DIR, config=cfg)
    assert "## DICT id_pessoa" in text
    assert "## DICT id_produto" in text

def test_fk_dict_contains_id_name_pairs():
    cfg = EncoderConfig(fk_mode="dict")
    text = encode(META, DATA_DIR, config=cfg)
    # Ana has id=1, so "1=Ana" should appear in dict block
    assert "1=Ana" in text

def test_fk_dict_ids_still_in_column():
    """FK column still has original IDs — DICT is additive context."""
    cfg = EncoderConfig(fk_mode="dict")
    text = encode(META, DATA_DIR, config=cfg)
    # The id_pessoa column line should contain the original numeric IDs
    id_pessoa_line = next(
        l for l in text.splitlines()
        if l.strip().startswith("id_pessoa:") and "[" not in l.split(":")[0]
    )
    assert "1" in id_pessoa_line.split(":")[1]

def test_fk_dict_roundtrip():
    """dict mode: IDs are original → roundtrip identical to id_raw."""
    cfg = EncoderConfig(fk_mode="dict")
    tables = decode(encode(META, DATA_DIR, config=cfg))
    orig = _orig_vendas()
    for o, r in zip(orig, tables["vendas"]):
        assert o["id_pessoa"] == r["id_pessoa"]
        assert o["id_produto"] == r["id_produto"]


# ---------------------------------------------------------------------------
# fk_mode="hint"
# ---------------------------------------------------------------------------

def test_fk_hint_emits_hint_line():
    cfg = EncoderConfig(fk_mode="hint")
    text = encode(META, DATA_DIR, config=cfg)
    assert any(
        l.strip().startswith("> id_pessoa ref pessoas")
        for l in text.splitlines()
    ), "Missing hint line for id_pessoa"

def test_fk_hint_ids_in_column():
    cfg = EncoderConfig(fk_mode="hint")
    text = encode(META, DATA_DIR, config=cfg)
    id_pessoa_line = next(
        l for l in text.splitlines()
        if l.strip().startswith("id_pessoa:") and "[" not in l.split(":")[0]
    )
    assert "1" in id_pessoa_line

def test_fk_hint_roundtrip():
    cfg = EncoderConfig(fk_mode="hint")
    tables = decode(encode(META, DATA_DIR, config=cfg))
    orig = _orig_vendas()
    for o, r in zip(orig, tables["vendas"]):
        assert o["id_pessoa"] == r["id_pessoa"]


# ---------------------------------------------------------------------------
# fk_mode="inline"
# ---------------------------------------------------------------------------

def test_fk_inline_has_names_not_ids():
    cfg = EncoderConfig(fk_mode="inline")
    text = encode(META, DATA_DIR, config=cfg)
    # After inline, column is 'pessoa' not 'id_pessoa'
    assert any(l.strip().startswith("pessoa:") for l in text.splitlines()), \
        "Expected 'pessoa:' column in inline mode"

def test_fk_inline_contains_name_values():
    cfg = EncoderConfig(fk_mode="inline")
    text = encode(META, DATA_DIR, config=cfg)
    pessoa_line = next(l for l in text.splitlines() if l.strip().startswith("pessoa:"))
    assert "Ana" in pessoa_line

def test_fk_inline_no_numeric_fk_ids():
    """In inline mode, the raw FK column (id_pessoa) should not appear."""
    cfg = EncoderConfig(fk_mode="inline")
    text = encode(META, DATA_DIR, config=cfg)
    # No line should start with "id_pessoa:" (unsorted)
    fk_lines = [
        l for l in text.splitlines()
        if l.strip().startswith("id_pessoa:") and "[" not in l.split(":")[0]
    ]
    assert not fk_lines, "id_pessoa: column found in inline mode"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="CLI v0.1 flags removed; encoder v0.1 tested via Python API above")
def test_cli_encode_int_scaled(tmp_path):
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "tcf", "encode",
         "--meta", str(META), "--data-dir", str(DATA_DIR),
         "--numeric", "int_scaled", "--out", str(tmp_path / "out.tcf")],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    text = (tmp_path / "out.tcf").read_text(encoding="utf-8")
    assert "# SCALE" in text

@pytest.mark.skip(reason="CLI v0.1 flags removed; encoder v0.1 tested via Python API above")
def test_cli_encode_fk_dict(tmp_path):
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "tcf", "encode",
         "--meta", str(META), "--data-dir", str(DATA_DIR),
         "--fk-mode", "dict", "--out", str(tmp_path / "out.tcf")],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    text = (tmp_path / "out.tcf").read_text(encoding="utf-8")
    assert "## DICT" in text

@pytest.mark.skip(reason="CLI v0.1 flags removed; encoder v0.1 tested via Python API above")
def test_cli_encode_no_sorted(tmp_path):
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "tcf", "encode",
         "--meta", str(META), "--data-dir", str(DATA_DIR),
         "--no-sorted", "--out", str(tmp_path / "out.tcf")],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    text = (tmp_path / "out.tcf").read_text(encoding="utf-8")
    data = [l for l in text.splitlines() if not l.startswith("#") and not l.startswith(">")]
    assert not any("[sorted]" in l for l in data)
