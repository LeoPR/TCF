"""Testes do relatório unificado / CLI (schema_gadget Fase 4).

Usa a API analyze_tables (não requer Z:; estruturas inline). Cobre a
orquestração FK + quality e a renderização markdown/estrutura.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "schema_gadget"))
sys.path.insert(0, str(ROOT / "src"))

from report import analyze_tables  # noqa: E402


def _star():
    """Star schema: FK íntegra + FK com órfão + coluna constante + PK dup."""
    return {
        "region": {"r_regionkey": ["0", "1", "2", "3", "4"]},
        "nation": {
            "n_nationkey": ["0", "1", "2", "3", "4", "5"],
            "n_regionkey": ["0", "1", "1", "2", "3", "4"],  # FK -> region
        },
        "customer": {
            "c_custkey": ["1", "2", "3", "4", "5"],
            "c_status": ["A", "A", "A", "A", "A"],           # constante
        },
        "orders": {
            "o_orderkey": ["10", "11", "12", "13"],
            "o_custkey": ["1", "2", "3", "99"],              # 99 órfão
        },
    }


PKS = {"region": ["r_regionkey"], "nation": ["n_nationkey"],
       "customer": ["c_custkey"], "orders": ["o_orderkey"]}


def test_report_structure():
    rep = analyze_tables(_star(), pks=PKS)
    assert set(rep.keys()) >= {"counts", "quality", "fks", "markdown"}
    assert rep["counts"]["tables"] == 4
    assert isinstance(rep["markdown"], str)


def test_report_finds_fk():
    rep = analyze_tables(_star(), pks=PKS, fk_min_confidence="alta")
    pairs = {(fk.child_table, fk.child_col, fk.parent_table) for fk in rep["fks"]}
    assert ("nation", "n_regionkey", "region") in pairs


def test_report_finds_constant():
    rep = analyze_tables(_star(), pks=PKS)
    constants = [a for al in rep["quality"].values() for a in al if a.kind == "constant"]
    assert any(a.column == "c_status" for a in constants)


def test_report_fk_orphan_flagged():
    """FK com 1 órfão entre muitos valores (overlap alto) é flagada c/ n_orphans>0."""
    # 20 custkeys; orders referencia 19 válidos + 1 órfão (overlap 19/20=0.95)
    tables = {
        "customer": {"c_custkey": [str(i) for i in range(1, 21)]},
        "orders": {
            "o_orderkey": [str(i) for i in range(100, 120)],
            "o_custkey": [str(i) for i in range(1, 20)] + ["999"],  # 999 órfão
        },
    }
    rep = analyze_tables(tables,
                         pks={"customer": ["c_custkey"], "orders": ["o_orderkey"]},
                         fk_min_confidence="baixa")
    oc = [fk for fk in rep["fks"]
          if fk.child_col == "o_custkey" and fk.parent_table == "customer"]
    assert oc, "FK candidate o_custkey -> customer não detectada"
    assert oc[0].n_orphans >= 1
    assert not oc[0].is_clean


def test_markdown_is_alert_only_and_has_scope_note():
    rep = analyze_tables(_star(), pks=PKS)
    md = rep["markdown"]
    assert "ALERT-ONLY" in md or "alerta" in md.lower()
    assert "nunca corrige" in md.lower()
    assert "schema-gadget-design.md" in md  # nota de escopo


def test_composite_pk_no_duplicate_key_in_report():
    """PK composta não deve gerar duplicate_key (regressão Fase 3 via report)."""
    tables = {
        "partsupp": {
            "ps_partkey": [str(i // 3) for i in range(12)],
            "ps_suppkey": [str(i % 3) for i in range(12)],
        },
    }
    rep = analyze_tables(tables, pks={"partsupp": ["ps_partkey", "ps_suppkey"]})
    dups = [a for al in rep["quality"].values() for a in al if a.kind == "duplicate_key"]
    assert not dups


def test_no_mutation():
    import copy
    tables = _star()
    snap = copy.deepcopy(tables)
    analyze_tables(tables, pks=PKS)
    assert tables == snap


def test_cli_main_list(capsys):
    """O entrypoint CLI roda `list` sem erro (carregado por caminho explícito)."""
    import importlib.util
    cli_path = ROOT / "scripts" / "schema_gadget" / "__main__.py"
    spec = importlib.util.spec_from_file_location("schema_gadget_cli", cli_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rc = mod.main(["list"])
    assert rc == 0
