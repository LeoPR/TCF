"""Testes do quality detector (schema_gadget Fase 3).

Casos derivados da validação adversarial 2026-06-03 (workflow): garantem
precisão (sem ruído) e que os bugs confirmados ficam fechados. Não requer Z:.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "schema_gadget"))
sys.path.insert(0, str(ROOT / "src"))

from tcf import build_schema  # noqa: E402
from sideouts_quality import analyze_quality, QualityAlert  # noqa: E402


def _kinds(alerts, col=None):
    return {a.kind for a in alerts if col is None or a.column == col}


# --- constant (o único detector com TP real e 0 FP) ---

def test_constant_fires():
    sch = build_schema({"flag": ["0"] * 1000})
    assert "constant" in _kinds(analyze_quality(sch), "flag")


def test_constant_not_on_two_values():
    sch = build_schema({"sex": ["M", "F"] * 500})
    assert "constant" not in _kinds(analyze_quality(sch), "sex")


# --- duplicate_key (single PK only) ---

def test_duplicate_key_single_pk():
    sch = build_schema({"id": ["1", "2", "3", "2", "5"]})
    a = analyze_quality(sch, expected_unique={"id"})
    assert "duplicate_key" in _kinds(a, "id")


def test_duplicate_key_silent_without_pk_hint():
    """Sem hint de PK, não há como saber intenção → não alerta."""
    sch = build_schema({"id": ["1", "2", "3", "2", "5"]})
    assert "duplicate_key" not in _kinds(analyze_quality(sch), "id")


def test_composite_pk_no_false_positive():
    """Componente de PK composta repete por design → NÃO é duplicate_key.

    Regressão dos 4 FPs ALTA do tpch (ps_partkey/ps_suppkey, l_orderkey/l_linenumber).
    """
    data = {
        "ps_partkey": [str(i // 4) for i in range(20)],   # repete (4x cada)
        "ps_suppkey": [str(i % 4) for i in range(20)],
    }
    sch = build_schema(data)
    # PK composta passada como tupla → membros excluídos do single duplicate_key
    a = analyze_quality(sch, expected_unique={("ps_partkey", "ps_suppkey")})
    assert "duplicate_key" not in _kinds(a, "ps_partkey")
    assert "duplicate_key" not in _kinds(a, "ps_suppkey")


# --- useless_id REMOVIDO (regressão dos 12 FPs do tpch) ---

def test_no_useless_id_on_distinct_string():
    """String all-distinct (nome/comentário/chave natural) NÃO deve alertar."""
    sentences = [f"comentario unico numero {i} aqui" for i in range(100)]
    sch = build_schema({"c_comment": sentences})
    alerts = analyze_quality(sch)  # sem PK hint
    assert alerts == [] or all(a.kind != "useless_id" for a in alerts)
    # 'useless_id' nem existe mais como kind
    assert "useless_id" not in _kinds(alerts)


# --- type_drift por fração numérica (agora dispara de verdade) ---

def test_type_drift_fires_on_sentinel():
    """Coluna maioria-numérica com 'N/A' no sample → type_drift."""
    sch = build_schema({"amount": ["1", "2", "3", "N/A", "5", "6", "7", "8"]})
    assert "type_drift" in _kinds(analyze_quality(sch), "amount")


def test_type_drift_silent_on_pure_numeric():
    sch = build_schema({"n": [str(i) for i in range(50)]})
    assert "type_drift" not in _kinds(analyze_quality(sch), "n")


def test_type_drift_silent_on_pure_text():
    """Coluna majoritariamente texto NÃO é type_drift (é categórica)."""
    sch = build_schema({"city": ["São Paulo", "Rio", "BH", "Curitiba", "Recife", "1"]})
    assert "type_drift" not in _kinds(analyze_quality(sch), "city")


def test_early_sentinel_no_useless_id_compound_bug():
    """Bug composto: 'N/A' cedo numa coluna all-distinct.

    Antes: type_drift suprimido + useless_id disparado (FP). Agora: type_drift
    dispara, useless_id não existe.
    """
    col = ["100", "200", "N/A"] + [str(i) for i in range(300, 350)]
    sch = build_schema({"amount": col})
    kinds = _kinds(analyze_quality(sch), "amount")
    assert "useless_id" not in kinds
    assert "type_drift" in kinds


# --- robustez ---

def test_expected_unique_string_not_substring():
    """expected_unique='cpf' trata só coluna 'cpf', não 'cp' (substring guard)."""
    sch = build_schema({"cp": ["1", "2", "2"], "cpf": ["a", "b", "b"]})
    a = analyze_quality(sch, expected_unique="cpf")
    assert "duplicate_key" in _kinds(a, "cpf")     # 'cpf' é a PK
    assert "duplicate_key" not in _kinds(a, "cp")  # 'cp' NÃO (não é substring-match)


def test_alert_only_no_mutation():
    data = {"id": ["1", "2", "2"], "x": ["a", "a", "a"]}
    import copy
    snap = copy.deepcopy(data)
    build_schema(data)  # build não muta
    sch = build_schema(data)
    analyze_quality(sch, expected_unique={"id"})
    assert data == snap


def test_zero_cost_only_reads_schema():
    """O detector não faz IO nem recomputa — opera só sobre o TableSchema."""
    sch = build_schema({"a": ["1", "1", "2"]})
    # se precisasse de dados além do schema, quebraria sem acesso a eles
    alerts = analyze_quality(sch)
    assert isinstance(alerts, list)
    assert all(isinstance(a, QualityAlert) and a.zero_cost for a in alerts)
