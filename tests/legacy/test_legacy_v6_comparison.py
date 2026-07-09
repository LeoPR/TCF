"""Legado #TCF.6 — comparacao V2-vs-legado, FORA do gate principal.

O #TCF.6 e' produzivel internamente (`fallback=False, min_header=False`) e LIDO
pelo decoder (caminho legado). Aqui fica so' a comparacao HISTORICA do ganho V2
(#TCF.7) sobre o #TCF.6: D17a 322B (#TCF.6) vs 302B (#TCF.7, gate principal).
Pré-1.0 (ADR-0024, git-as-compat). T-CODE-LEGACY-PRUNE-PRE-07 S2 (2026-06-24).

Separado de tests/test_multi_col_rt.py de proposito: 302B/#TCF.7 e' o invariante
VIVO; o #TCF.6/322B e' legado-comparacao, nao contrato vivo. Some no 1.0.
"""
from __future__ import annotations

import csv
from pathlib import Path

from tcf import decode, encode
from tcf.multi import _encode_multi

ROOT = Path(__file__).resolve().parents[2]
DATASETS_DIR = ROOT / "datasets" / "synthetic"


def _legacy_v6(table):
    """Formato legado #TCF.6 (sem fallback nem header minimo)."""
    return _encode_multi(table, fallback=False, min_header=False)


def _ler_csv_multi(name: str) -> dict[str, list[str]]:
    with (DATASETS_DIR / f"{name}.csv").open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        cols: dict[str, list[str]] = {h: [] for h in header}
        for row in r:
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


_KNOBS_TABLE = {
    "hour": [str(i % 24) for i in range(120)],
    "code": [f"{(i * 2654435761) & 0xFFFFFF:06x}" for i in range(120)],
    "nome": [f"item_{i:03d}_descricao_unica" for i in range(120)],
}


class TestLegacyV6Comparison:
    """Comparacao do ganho V2 vs o legado #TCF.6. Re-pinavel (ADR-0024)."""

    def test_d17a_legacy_322B(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        legacy = _legacy_v6(table)
        assert len(legacy.encode("utf-8")) == 322
        assert legacy.startswith("#TCF.6 M")
        assert decode(legacy) == table

    def test_legacy_is_v6_with_prefix(self):
        legacy = _legacy_v6({"a": ["abc", "abcd"], "b": ["x", "y"]})
        assert legacy.startswith("#TCF.6 M\n# ")
        meta = legacy.split("\n", 2)[1]
        assert all("=" in p for p in meta[2:].split(","))  # todos com size

    def test_decoder_reads_legacy(self):
        t = {"a": ["abc", "abcd"], "b": ["x", "y"]}
        assert decode(_legacy_v6(t)) == t

    def test_force_legacy_via_public_knobs(self):
        t = _KNOBS_TABLE
        text = encode(t, fallback=False, min_header=False)
        assert text.startswith("#TCF.6 M\n# ")
        assert decode(text) == t
        assert text == _legacy_v6(t)

    def test_v7_not_larger_than_legacy_v6(self):
        t = _KNOBS_TABLE
        assert len(encode(t).encode("utf-8")) <= len(_legacy_v6(t).encode("utf-8"))
