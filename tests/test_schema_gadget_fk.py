"""Testes do FK detector (schema_gadget Fase 1).

Não requer Z:/dataset — usa fixtures determinísticas inline. A validação
contra TPC-H real (recall 9/9, 0 FP em min_confidence='alta') está em
scripts/schema_gadget/ (scratch de validação) e documentada no design.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "schema_gadget"))

from fk_detect import detect_fk_candidates, FKCandidate  # noqa: E402


def _star_schema():
    """Star schema com 1 FK íntegra + 1 FK com órfão + ruído de inteiro denso."""
    return {
        "region": {"r_regionkey": [0, 1, 2, 3, 4]},
        "nation": {
            "n_nationkey": [0, 1, 2, 3, 4, 5, 6, 7],
            "n_regionkey": [0, 1, 1, 2, 3, 4, 0, 2],   # FK -> region (íntegra)
        },
        "customer": {"c_custkey": list(range(1, 21))},
        "orders": {
            "o_orderkey": list(range(100, 110)),
            "o_custkey": [1, 2, 3, 4, 5, 6, 7, 8, 9, 99],  # 99 órfão
        },
    }


def test_finds_clean_fk():
    """FK íntegra (n_regionkey -> region) é detectada com confiança alta."""
    cands = detect_fk_candidates(_star_schema())
    hit = [c for c in cands
           if c.child_table == "nation" and c.child_col == "n_regionkey"
           and c.parent_table == "region"]
    assert hit, "FK n_regionkey -> region.r_regionkey não detectada"
    fk = hit[0]
    assert fk.overlap == 1.0
    assert fk.is_clean
    assert fk.confidence == "alta"  # nome compatível (regionkey) + overlap 1.0


def test_detects_orphans():
    """FK com órfão (o_custkey -> customer, 99 ausente) é flagada com órfão."""
    cands = detect_fk_candidates(_star_schema())
    hit = [c for c in cands
           if c.child_col == "o_custkey" and c.parent_table == "customer"]
    assert hit, "candidato o_custkey -> customer não detectado"
    fk = hit[0]
    assert fk.n_orphans == 1       # o valor 99
    assert not fk.is_clean
    assert fk.overlap < 1.0


def test_confidence_grading_separates_noise():
    """Coincidência numérica (sem nome compatível) fica em confiança baixa."""
    cands = detect_fk_candidates(_star_schema())
    # n_regionkey vs n_nationkey: valores coincidem mas nome não casa exato
    noise = [c for c in cands
             if c.child_col == "n_regionkey" and c.parent_col == "n_nationkey"]
    if noise:  # se emitido, deve ser baixa confiança
        assert noise[0].confidence == "baixa"


def test_min_confidence_filter():
    """min_confidence='alta' remove o ruído, mantém a FK real."""
    high = detect_fk_candidates(_star_schema(), min_confidence="alta")
    assert all(c.confidence == "alta" for c in high)
    # a FK real (nome compatível) sobrevive
    assert any(c.child_col == "n_regionkey" and c.parent_table == "region"
               for c in high)


def test_alert_only_does_not_mutate():
    """O detector é alert-only: não modifica a entrada."""
    tables = _star_schema()
    import copy
    snapshot = copy.deepcopy(tables)
    detect_fk_candidates(tables)
    assert tables == snapshot, "detect_fk_candidates mutou a entrada (proibido)"


def test_ignores_low_cardinality_flags():
    """Colunas com pouquíssimos distintos (flags) não viram FK por ruído."""
    tables = {
        "fact": {"flag": ["A", "B", "A", "B", "A"]},
        "dim": {"code": ["A", "B", "C", "D", "E", "F", "G", "H"]},
    }
    cands = detect_fk_candidates(tables, min_child_distinct=3)
    assert not any(c.child_col == "flag" for c in cands)


def test_high_cardinality_string_fk():
    """FK de string alta-cardinalidade (estilo CPF) detectada sem nome igual."""
    parent_ids = [f"{i:011d}" for i in range(1000)]
    child_refs = [parent_ids[i % 1000] for i in range(300)]  # subconjunto
    tables = {
        "pessoas": {"cpf": parent_ids},
        "empresas": {"socio_cpf": child_refs},
    }
    cands = detect_fk_candidates(tables)
    hit = [c for c in cands if c.child_col == "socio_cpf"]
    assert hit, "FK socio_cpf -> cpf (alta cardinalidade) não detectada"
    assert hit[0].overlap == 1.0
    # nome compatível (sufixo cpf) -> alta
    assert hit[0].confidence == "alta"
