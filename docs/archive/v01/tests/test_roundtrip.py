"""Roundtrip tests: encode → decode → compare with original CSVs."""

import csv
from pathlib import Path

import pytest

# Allow running without install via `python -m pytest` from repo root
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tcf.encoder import encode
from tcf.decoder import decode

DATA_DIR = Path(__file__).parent.parent / "data"
META     = DATA_DIR / "metadata.json"


def read_csv(name: str) -> list[dict]:
    return list(csv.DictReader((DATA_DIR / name).open(encoding="utf-8")))


def test_encode_produces_string():
    result = encode(META, DATA_DIR)
    assert isinstance(result, str)
    assert "# TCF v0.1" in result
    assert "## pessoas" in result
    assert "## vendas" in result


def test_encode_contains_sorted_for_fk():
    result = encode(META, DATA_DIR)
    assert "id_pessoa[sorted]:" in result
    assert "id_produto[sorted]:" in result


def test_roundtrip_pessoas():
    tables = decode(encode(META, DATA_DIR))
    original = read_csv("pessoas.csv")
    restored = tables["pessoas"]

    assert len(original) == len(restored), "row count mismatch"
    for orig, rest in zip(original, restored):
        assert orig["id"] == rest["id"]
        assert orig["nome"] == rest["nome"]


def test_roundtrip_produtos():
    tables = decode(encode(META, DATA_DIR))
    original = read_csv("produtos.csv")
    restored = tables["produtos"]

    assert len(original) == len(restored)
    for orig, rest in zip(original, restored):
        assert orig["id"] == rest["id"]
        assert orig["nome"] == rest["nome"]


def test_roundtrip_vendas_keys():
    tables = decode(encode(META, DATA_DIR))
    original = read_csv("vendas.csv")
    restored = tables["vendas"]

    assert len(original) == len(restored)
    for orig, rest in zip(original, restored):
        assert orig["id_pessoa"]  == rest["id_pessoa"]
        assert orig["id_produto"] == rest["id_produto"]


def test_roundtrip_vendas_values():
    tables = decode(encode(META, DATA_DIR))
    original = read_csv("vendas.csv")
    restored = tables["vendas"]

    for orig, rest in zip(original, restored):
        assert float(orig["vl"]) == pytest.approx(float(rest["vl"]), rel=1e-4)


def test_sorted_rle_frequency_sum():
    """Frequency counts in id_produto[sorted] must sum to total row count."""
    result = encode(META, DATA_DIR)
    for line in result.splitlines():
        if line.startswith("id_produto[sorted]:"):
            _, _, values = line.partition(": ")
            total = 0
            for token in values.split():
                if ":" in token:
                    n, _, _ = token.partition(":")
                    total += int(n)
                else:
                    total += 1
            assert total == 41  # known row count of vendas
            break
