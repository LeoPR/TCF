"""Suite de regressao byte-canonical pra v1.0 baseline.

Snapshot byte-count + RT pra datasets-chave. Qualquer mudanca em
src/tcf/ que mude um byte aqui = regressao. Bytes documentados em:

    experiments/lab/dirty/2026-05-27-baseline-consolidado/METRICS.md

Estrategia (Beizer 1995 — characteristic outputs):
- D1-D9: 9 datasets sinteticos single-col (M10 baseline = 1523B total)
- D17a: 1 dataset sintetico multi-col (322B INVARIANT)

Regressao byte-canonical REAL-WORLD (colunas free-text, regime
n_tam_est>=3) vive em test_real_world_snapshots.py — fixtures committadas
em datasets/samples/ (frozen, portaveis, NAO dependem de Z:). Gate
obrigatorio pra mudancas em HCC/prune (T-REGRESSION-REAL-WORLD, 2026-05-31).
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

import tcf
from tcf import encode, decode


ROOT = Path(__file__).resolve().parent.parent
DATASETS = ROOT / "datasets" / "synthetic"


# Superficie de API publica. Sob ADR-0024/0028 (pre-1.0) a adicao e' ADITIVA —
# atualizar esta lista ao exportar algo novo. Bump de versao (0.7.1 -> 0.7.2,
# release dentro do formato #TCF.7; ADR-0028) acontece no release, nao a cada export.
EXPECTED_PUBLIC_API = {
    "encode",
    "decode",
    "SideOutputs",
    "build_schema",
    "TableSchema",
    "ColumnSchema",
    "TemplatedCheckedSpec",
    "TemplatedPaddedSpec",
    "SPEC_CPF",
    "SPEC_CNPJ",
    "SPEC_IP",
    "PipelineConfig",
    "view",       # camada read-only lazy/consultavel (A4, plano 0.8)
    "LazyTCF",    # A4
    "Filtered",   # A4
    # encode_table/decode_table APOSENTADOS 2026-06-24 (T-CODE-LEGACY-PRUNE-PRE-07)
}


class TestPublicAPISurface:
    """ADR-0017: API publica congelada. Contrato enforced por test."""

    def test_all_matches_expected(self):
        assert set(tcf.__all__) == EXPECTED_PUBLIC_API, (
            "tcf.__all__ divergiu da API publica congelada (ADR-0017). "
            "Adicionar/remover export requer atualizar EXPECTED_PUBLIC_API + "
            "bump de versao + nota no ADR.\n"
            f"  faltando: {EXPECTED_PUBLIC_API - set(tcf.__all__)}\n"
            f"  extra:    {set(tcf.__all__) - EXPECTED_PUBLIC_API}"
        )

    def test_all_symbols_importable(self):
        """Cada nome em __all__ deve existir como atributo do modulo."""
        for name in tcf.__all__:
            assert hasattr(tcf, name), f"tcf.__all__ lista '{name}' mas nao existe"

    def test_version_pre_1_0(self):
        # Pré-1.0 (ADR-0024): pacote em 0.x, minor acompanha o formato (#TCF.7).
        assert tcf.__version__ == "0.7.1"


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

D17A_INVARIANT = 303  # 0.7 default (V2-B: era 307; re-pinavel — ADR-0024/0025)
D17A_LEGACY_V6 = 322   # #TCF.6 legado, ainda produzivel internamente


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
    """D17a multi-col baseline: 0.7 default = 303B (V2-B na coluna `categoria`;
    era 307 sem V2-B, 322 em #TCF.6). Baseline = guarda de regressao re-pinavel
    em mudanca INTENCIONAL (ADR-0024/0025), nao contrato eterno."""

    def test_d17a_exact_baseline(self):
        cols = _load_multi_col("D17a-multi-column-mixed")
        text = encode(cols)
        actual = len(text.encode("utf-8"))
        assert actual == D17A_INVARIANT, (
            f"D17a baseline (303B, 0.7) mudou: obteve {actual}B. Re-pina so' se a "
            f"mudanca de formato for INTENCIONAL (ADR-0024/0025)."
        )

    def test_d17a_round_trip(self):
        cols = _load_multi_col("D17a-multi-column-mixed")
        text = encode(cols)
        assert decode(text) == cols
