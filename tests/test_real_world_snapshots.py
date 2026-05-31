"""Suite de regressao byte-canonical REAL-WORLD (gate de prune algoritmico).

Complementa test_regression_v1_baseline.py (D1-D9 + D17a sinteticos). Motivo
(T-REGRESSION-REAL-WORLD, 2026-05-31): o mini-suite sintetico NAO cobre o
regime `n_tam_est >= 3` que aparece em colunas free-text reais com atom_count
alto. Candidato H-PERF-06-v2 #03 (prune-k-03) passou D1-D9 + D17a mas
regrediu bytes em online-retail real (+0.59%) — exatamente este blind spot.

Fixtures (committadas em datasets/samples/, frozen, portaveis — NAO dependem
de Z:): primeiros 2000 valores de colunas free-text que PROVARAM poder
discriminante (catch #03) no probe da Fase A:

    retail Description, retail StockCode, lineitem l_comment

Gerador reproduzivel + evidencia de discriminacao:
    experiments/lab/dirty/2026-05-31-regression-real-world/

Qualquer mudanca em src/tcf/ (especialmente em _detect_compositions / HCC)
que mude um byte aqui = regressao no regime real-world. Atualizar snapshot
SO' apos investigar + ADR.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tcf import encode, decode


ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "datasets" / "samples"


# Bytes baseline congelados (src/tcf canonical, medido 2026-05-31).
# Cada fixture provou DIVERGIR no candidato #03 (regime n_tam_est>=3) e
# MANTER no #15 — ver lab 2026-05-31-regression-real-world/REPORT.md.
REAL_WORLD_BYTES_FROZEN = {
    "retail-description-2k": (27581, "online-retail/description-2k.csv"),
    "retail-stockcode-2k":   (11437, "online-retail/stockcode-2k.csv"),
    "lineitem-comment-2k":   (50598, "tpch-sf001/lcomment-2k.csv"),
}

REAL_WORLD_TOTAL = 89616  # 27581 + 11437 + 50598


def _load_single_col(rel: str) -> list[str]:
    path = SAMPLES / rel
    assert path.exists(), (
        f"fixture ausente: {path}\n"
        f"Regenerar via experiments/lab/dirty/2026-05-31-regression-real-world/"
        f"make_fixtures.py (requer Z:)"
    )
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        next(r)  # header
        return [row[0] for row in r if row]


class TestRealWorldByteCanonical:
    """Snapshot byte-count + RT pra colunas free-text reais (gate n_tam_est>=3)."""

    @pytest.mark.parametrize(
        "name,expected_bytes,rel",
        [(k, v[0], v[1]) for k, v in REAL_WORLD_BYTES_FROZEN.items()],
    )
    def test_byte_count_matches_snapshot(self, name, expected_bytes, rel):
        values = _load_single_col(rel)
        text = encode(values)
        actual = len(text.encode("utf-8"))
        assert actual == expected_bytes, (
            f"{name}: esperado {expected_bytes}B, obteve {actual}B "
            f"(regressao byte-canonical REAL-WORLD — regime n_tam_est>=3; "
            f"investigar src/tcf OU atualizar snapshot com ADR)"
        )

    @pytest.mark.parametrize(
        "name,rel",
        [(k, v[1]) for k, v in REAL_WORLD_BYTES_FROZEN.items()],
    )
    def test_round_trip(self, name, rel):
        values = _load_single_col(rel)
        text = encode(values)
        assert decode(text) == values, f"RT broken em {name}"

    def test_total_invariant(self):
        total = 0
        for _name, (_b, rel) in REAL_WORLD_BYTES_FROZEN.items():
            values = _load_single_col(rel)
            total += len(encode(values).encode("utf-8"))
        assert total == REAL_WORLD_TOTAL, (
            f"Total real-world mudou: esperado {REAL_WORLD_TOTAL}B, obteve {total}B"
        )
