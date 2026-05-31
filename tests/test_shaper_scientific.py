"""Gate cientifico-estatistico do shaper (T-SHAPER-SCIENTIFIC-GATING).

Valida os CLAIMS estatisticos do shaper — nao so' cardinalidade/presenca
(que test_shaper.py ja' cobre). Pre-requisito pra usar o shaper em
experimentos TCF que produzem evidencia empirica (principio do owner
2026-05-31: tool cientifico precisa de aprovacao estatistica formal).

Tooling de suporte (scripts/shaper/), NAO TCF-core. Requer hubs SQLite em
Z:/tcf-data/interim/ (skip se ausente).

  P1  fk_preserving: integridade referencial (no orphans + no amplification)
  P2  stratify:      preserva distribuicao (chi2 + TVD sobre amostra REAL)
  P3  join flat:     preserva contagem do fact (LEFT JOIN, sem perda/multipl.)
  P4  volume random: preserva marginais (TVD por coluna categorica)
  P5  SCHEMA_LEVELS:  coerentes com topologia FK (nao arbitrarios)

Princpio de rigor: P2/P4 recomputam metricas a partir das LINHAS retornadas
(nao confiam no METRICS_JSON do trace, que reporta os targets de alocacao).
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from shaper import ShapeRequest, Shaper  # noqa: E402
from shaper._stratify_metrics import compute_stratification_metrics  # noqa: E402
from dataset_reader import DatasetReader  # noqa: E402

# IMPORTANTE: carregar o registry COMPLETO de strategies ANTES de importar
# qualquer modulo de strategy individual. `_load_builtin_strategies` faz
# early-return se o registry ja' estiver nao-vazio; importar so' schema.py
# aqui registraria APENAS schema e silenciaria join/stratify/volume/etc.
# (fragilidade do lazy-load — anotada em T-SHAPER-CODE-HARDENING A5).
from shaper.pipeline import _load_builtin_strategies as _load_strats  # noqa: E402
_load_strats()
from shaper.strategies.schema import SCHEMA_LEVELS  # noqa: E402


def _needs_db(name: str):
    from _paths import interim_db
    if not interim_db(name).exists():
        pytest.skip(f"SQLite DB not found: {name}. Run csv_to_sqlite.py first.")


@pytest.fixture(scope="module")
def shaper():
    return Shaper()


def _pop_column(dataset: str, table: str, col: str) -> list:
    with DatasetReader(dataset) as rd:
        return rd.columns(table, limit=None)[col]


# ---------------------------------------------------------------------------
# P1 — fk_preserving: integridade referencial
# ---------------------------------------------------------------------------

class TestP1_FKPreservingIntegrity:
    @pytest.fixture(autouse=True)
    def _db(self):
        _needs_db("tpch-sf001")

    @staticmethod
    def _fk_edges_in_scope(result):
        """(child, fk_col, parent, pk_col) p/ arestas FK totalmente no result."""
        meta = result.metadata["tables"]
        for child in result.tables:
            for fk_col, ref in meta.get(child, {}).get("fk", {}).items():
                parent, pk_col = ref.split(".")
                if parent in result.tables:
                    yield child, fk_col, parent, pk_col

    def test_no_orphans(self, shaper):
        r = shaper.apply(ShapeRequest(
            dataset="tpch-sf001", schema="chain",
            volume=100, fk_preserving=True, seed=42))
        edges = list(self._fk_edges_in_scope(r))
        assert edges, "esperava >=1 aresta FK in-scope em schema=chain"
        for child, fk_col, parent, pk_col in edges:
            child_fks = {row[fk_col] for row in r.tables[child]
                         if row[fk_col] is not None}
            parent_pks = {row[pk_col] for row in r.tables[parent]}
            orphans = child_fks - parent_pks
            assert not orphans, (
                f"FK orfa {child}.{fk_col} -> {parent}.{pk_col}: "
                f"{len(orphans)} valores sem PK correspondente no parent filtrado"
            )

    def test_no_amplification(self, shaper):
        full = shaper.apply(ShapeRequest(dataset="tpch-sf001", schema="chain"))
        samp = shaper.apply(ShapeRequest(
            dataset="tpch-sf001", schema="chain",
            volume=100, fk_preserving=True, seed=42))
        for t in samp.tables:
            assert len(samp.tables[t]) <= len(full.tables[t]), (
                f"{t} amplificou: {len(samp.tables[t])} > {len(full.tables[t])}"
            )

    def test_fact_respects_volume(self, shaper):
        # fact em chain = lineitem (mais FKs); amostra <= volume
        r = shaper.apply(ShapeRequest(
            dataset="tpch-sf001", schema="chain",
            volume=100, fk_preserving=True, seed=42))
        assert len(r.tables["lineitem"]) <= 100

    def test_determinism(self, shaper):
        req = ShapeRequest(dataset="tpch-sf001", schema="chain",
                           volume=100, fk_preserving=True, seed=42)
        r1 = shaper.apply(req)
        r2 = shaper.apply(req)
        assert r1.table_row_counts() == r2.table_row_counts()


# ---------------------------------------------------------------------------
# P2 — stratify: preserva distribuicao
# ---------------------------------------------------------------------------

class TestP2_StratifyPreservesDistribution:
    @pytest.fixture(autouse=True)
    def _db(self):
        _needs_db("adult-census")

    def test_chi2_and_tvd_on_real_sample(self, shaper):
        vol = 2000
        r = shaper.apply(ShapeRequest(
            dataset="adult-census", volume=vol, stratify_by="sex"))
        sample = r.tables["adult"]
        assert len(sample) == vol

        pop_counts = dict(Counter(_pop_column("adult-census", "adult", "sex")))
        sample_counts = dict(Counter(row["sex"] for row in sample))
        m = compute_stratification_metrics(pop_counts, sample_counts)

        assert not m["chi2_warn_low_n"], "expected-cell < 5: aumentar volume"
        assert m["chi2_pvalue"] > 0.05, (
            f"H0 (proporcionalidade) rejeitada: chi2_p={m['chi2_pvalue']}")
        assert m["tvd"] < 0.02, f"TVD alto demais: {m['tvd']}"

    def test_all_groups_covered_min1(self, shaper):
        # min-1 por grupo: mesmo grupo raro deve aparecer (cobertura categorica)
        r = shaper.apply(ShapeRequest(
            dataset="adult-census", volume=50, stratify_by="race"))
        pop_groups = set(_pop_column("adult-census", "adult", "race"))
        sample_groups = set(row["race"] for row in r.tables["adult"])
        assert sample_groups == pop_groups, (
            f"stratify deve cobrir todos os grupos (min-1); "
            f"faltando: {pop_groups - sample_groups}")


# ---------------------------------------------------------------------------
# P3 — join flat: preserva contagem do fact
# ---------------------------------------------------------------------------

class TestP3_JoinRowCountInvariant:
    @pytest.fixture(autouse=True)
    def _db(self):
        _needs_db("tpch-sf001")

    def test_flat_preserves_fact_count(self, shaper):
        norm = shaper.apply(ShapeRequest(
            dataset="tpch-sf001", schema="core", join_level="normalized"))
        flat = shaper.apply(ShapeRequest(
            dataset="tpch-sf001", schema="core", join_level="flat"))
        # fact em core = tabela maior (orders); LEFT JOIN many-to-one
        # preserva exatamente a contagem do fact (sem perda nem multiplicacao).
        fact_count = max(len(v) for v in norm.tables.values())
        assert len(flat.table_names) == 1, "flat deve produzir 1 supertabela"
        assert flat.total_rows == fact_count, (
            f"flat {flat.total_rows} != fact {fact_count} "
            f"(LEFT JOIN deve preservar contagem do fact)")


# ---------------------------------------------------------------------------
# P4 — volume random: preserva marginais
# ---------------------------------------------------------------------------

class TestP4_VolumeMarginalUnbiased:
    @pytest.fixture(autouse=True)
    def _db(self):
        _needs_db("adult-census")

    def test_random_sample_preserves_marginals(self, shaper):
        vol = 5000
        r = shaper.apply(ShapeRequest(
            dataset="adult-census", volume=vol, order="random", seed=42))
        sample = r.tables["adult"]
        assert len(sample) == vol

        with DatasetReader("adult-census") as rd:
            cols = rd.columns("adult", limit=None)
        for col in ("sex", "race", "education"):
            pop_counts = dict(Counter(cols[col]))
            sample_counts = dict(Counter(row[col] for row in sample))
            m = compute_stratification_metrics(pop_counts, sample_counts)
            assert m["tvd"] < 0.05, (
                f"coluna '{col}': amostra random viesada, TVD={m['tvd']} "
                f"(esperado < 0.05 p/ amostra de {vol})")


# ---------------------------------------------------------------------------
# P5 — SCHEMA_LEVELS coerentes com topologia FK
# ---------------------------------------------------------------------------

class TestP5_SchemaLevelsFKTopology:
    @pytest.fixture(autouse=True)
    def _db(self):
        _needs_db("tpch-sf001")

    @staticmethod
    def _internal_fk_edges(reader, level_tables) -> int:
        scope = set(level_tables)
        return sum(
            1
            for t in level_tables
            for ref in reader.fk(t).values()
            if ref.split(".")[0] in scope
        )

    def test_core_has_fk_relationship(self):
        with DatasetReader("tpch-sf001") as rd:
            core = SCHEMA_LEVELS["tpch-sf001"]["core"]
            assert self._internal_fk_edges(rd, core) >= 1, (
                "level 'core' deveria ter >=1 FK interna (nao arbitrario)")

    def test_chain_extends_core(self):
        with DatasetReader("tpch-sf001") as rd:
            core = SCHEMA_LEVELS["tpch-sf001"]["core"]
            chain = SCHEMA_LEVELS["tpch-sf001"]["chain"]
            ce = self._internal_fk_edges(rd, core)
            che = self._internal_fk_edges(rd, chain)
            assert len(chain) > len(core), "chain deve ter mais tabelas que core"
            assert che > ce, (
                f"chain ({che} FKs internas) deveria estender core ({ce}) "
                f"com mais relacionamentos")
