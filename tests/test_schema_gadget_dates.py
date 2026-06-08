"""Testes do date/format checker (schema_gadget Fase 2).

Casos inline (sem Z:). A validação de falso-positivo em datas REAIS limpas
(tpch o_orderdate, br-identidades data_cadastro -> 0 alertas) + corrupção
controlada foram feitas na sessão; aqui ficam as regressões determinísticas.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "schema_gadget"))

from date_check import check_dates, _valid_ymd, _looks_like_date_column  # noqa: E402


def _kinds(res, table="t"):
    return {a.kind for a in res.get(table, [])}


# --- validação de calendário (núcleo) ---

def test_valid_ymd_leap_year():
    assert _valid_ymd(2024, 2, 29)       # 2024 bissexto
    assert not _valid_ymd(2023, 2, 29)   # 2023 não-bissexto
    assert not _valid_ymd(2026, 2, 30)   # nunca existe
    assert not _valid_ymd(2026, 13, 1)   # mês > 12
    assert not _valid_ymd(2026, 0, 15)   # mês 0
    assert not _valid_ymd(2026, 1, 0)    # dia 0
    assert not _valid_ymd(2026, 4, 31)   # abril tem 30
    assert _valid_ymd(2026, 12, 31)      # válido


# --- impossible_date ---

def test_impossible_date_fires():
    col = ["2024-01-15", "2026-02-30", "2026-13-01", "2024-06-20", "2023-02-29"]
    res = check_dates({"t": {"d": col}})
    assert "impossible_date" in _kinds(res)


def test_clean_iso_no_alert():
    """Datas ISO limpas → nenhum alerta (regressão de falso-positivo)."""
    col = [f"2024-{m:02d}-15" for m in range(1, 13)] + ["2024-02-29"]
    res = check_dates({"t": {"d": col}})
    assert res.get("t", []) == []


def test_clean_datetime_no_alert():
    """Datetime ISO (online-retail style) limpo → 0 alertas."""
    col = [f"2010-12-{d:02d} 08:26:00" for d in range(1, 28)]
    res = check_dates({"t": {"d": col}})
    assert res.get("t", []) == []


# --- format_mix ---

def test_format_mix_fires():
    col = ["2024-01-15", "2024-02-20", "15/03/2024", "2024-04-10", "20/05/2024"]
    res = check_dates({"t": {"d": col}})
    assert "format_mix" in _kinds(res)


# --- suspicious_date ---

def test_suspicious_future():
    col = ["2024-01-01", "2025-06-15", "2999-01-01", "2024-03-03"]
    res = check_dates({"t": {"d": col}})
    assert "suspicious_date" in _kinds(res)


# --- auto-detecção: não-data é ignorada ---

def test_non_date_column_ignored():
    res = check_dates({"t": {"nome": ["ana", "bia", "cris", "duda", "eva"]}})
    assert res.get("t", []) == []


def test_numeric_column_ignored_type_safe():
    """Coluna de inteiros (DatasetReader devolve int) não quebra nem alerta."""
    res = check_dates({"t": {"id": [1, 2, 3, 4, 5, 6]}})  # ints, não strings
    assert res.get("t", []) == []


def test_mixed_int_and_date_safe():
    """Valores int no meio de datas não causam crash (type guard)."""
    col = ["2024-01-15", 20240115, "2024-02-20", None, "2024-03-10", "2024-04-05"]
    res = check_dates({"t": {"d": col}})  # não deve lançar
    assert isinstance(res, dict)


# --- alert-only ---

def test_no_mutation():
    import copy
    tables = {"t": {"d": ["2026-02-30", "2024-01-01", "2024-06-06"]}}
    snap = copy.deepcopy(tables)
    check_dates(tables)
    assert tables == snap


def test_alerts_are_not_zero_cost():
    """DateAlert declara honestamente que NÃO é zero-custo."""
    res = check_dates({"t": {"d": ["2026-02-30", "2024-01-01", "2024-02-02"]}})
    assert all(a.zero_cost is False for a in res.get("t", []))


# --- integração no relatório ---

def test_report_includes_dates():
    sys.path.insert(0, str(ROOT / "src"))
    from report import analyze_tables
    tables = {"pedidos": {
        "o_orderdate": ["2024-01-15", "2026-02-30", "2024-03-20", "2024-04-04"],
    }}
    rep = analyze_tables(tables)
    assert "dates" in rep
    assert rep["counts"]["date_alerts"] >= 1
    assert "data" in rep["markdown"].lower()
