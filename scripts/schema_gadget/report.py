"""Relatório unificado do schema/quality gadget — Fase 4.

Orquestra os detectores das fases anteriores num relatório ALERT-ONLY:
- FK candidates cross-table (fk_detect, Fase 1)
- alertas de qualidade per-coluna zero-custo (sideouts_quality, Fase 3)

Consome um dataset do hub SQLite (via DatasetReader) OU estruturas genéricas
já carregadas. NUNCA modifica dados — emite relatório markdown ou dict/json.

Uso programático:
    from schema_gadget.report import analyze_tables
    rep = analyze_tables({"t": {"col": [...]}}, pks={"t": ["col"]})
    print(rep["markdown"])
"""

from __future__ import annotations

try:  # como pacote (-m schema_gadget) ou import direto (sys.path em scripts/schema_gadget)
    from .fk_detect import detect_fk_candidates
    from .sideouts_quality import analyze_quality
except ImportError:
    from fk_detect import detect_fk_candidates
    from sideouts_quality import analyze_quality


def _build_expected_unique(pk: list[str]) -> set:
    """Converte PK em expected_unique p/ analyze_quality.

    PK single-column -> {nome}; PK composta -> {tupla} (membros excluídos
    do duplicate_key single, conforme Fase 3).
    """
    if not pk:
        return set()
    if len(pk) == 1:
        return {pk[0]}
    return {tuple(pk)}


def analyze_tables(
    tables: dict[str, dict[str, list]],
    *,
    pks: dict[str, list[str]] | None = None,
    fk_min_confidence: str = "media",
) -> dict:
    """Roda quality + FK detect e devolve relatório estruturado.

    Args:
        tables: {tabela: {coluna: [valores]}}.
        pks: {tabela: [colunas-pk]} (opcional; melhora duplicate_key).
        fk_min_confidence: filtro do FK detector (default 'media' — corta
            o ruído de coincidência numérica visto em inteiros densos).

    Returns:
        dict com: quality (lista de alerts por tabela), fks (candidatos),
        counts, e markdown (string pronta pra exibir). ALERT-ONLY.
    """
    from tcf import build_schema  # import tardio (core)

    pks = pks or {}

    # --- Quality per-tabela (zero-custo) ---
    quality: dict[str, list] = {}
    for tname, cols in tables.items():
        schema = build_schema(cols)
        eu = _build_expected_unique(pks.get(tname, []))
        quality[tname] = analyze_quality(schema, expected_unique=eu)

    # --- FK candidates cross-table ---
    fks = detect_fk_candidates(tables, min_confidence=fk_min_confidence)

    n_quality = sum(len(v) for v in quality.values())
    counts = {
        "tables": len(tables),
        "quality_alerts": n_quality,
        "fk_candidates": len(fks),
    }

    return {
        "counts": counts,
        "quality": quality,
        "fks": fks,
        "markdown": _to_markdown(tables, quality, fks, counts, pks),
    }


def _to_markdown(tables, quality, fks, counts, pks) -> str:
    """Renderiza o relatório em markdown (read-only, human-friendly)."""
    lines: list[str] = []
    lines.append("# Schema/Quality Gadget — Relatório (ALERT-ONLY)")
    lines.append("")
    lines.append("> Este relatório **só detecta e alerta — nunca corrige**. "
                 "O dev/arquiteto decide o que fazer.")
    lines.append("")
    lines.append(f"- Tabelas analisadas: **{counts['tables']}**")
    lines.append(f"- Alertas de qualidade: **{counts['quality_alerts']}**")
    lines.append(f"- FK candidates: **{counts['fk_candidates']}**")
    lines.append("")

    # FK candidates
    lines.append("## FK candidates (cross-table)")
    if fks:
        lines.append("")
        lines.append("| confiança | child | parent | overlap | órfãos |")
        lines.append("|---|---|---|---|---|")
        for fk in fks:
            orf = "0 (íntegra)" if fk.is_clean else str(fk.n_orphans)
            lines.append(f"| {fk.confidence} | `{fk.child_table}.{fk.child_col}` "
                         f"| `{fk.parent_table}.{fk.parent_col}` "
                         f"| {fk.overlap:.3f} | {orf} |")
    else:
        lines.append("")
        lines.append("_Nenhum FK candidate acima do limiar de confiança._")
    lines.append("")

    # Quality alerts por tabela
    lines.append("## Alertas de qualidade (zero-custo, per-coluna)")
    any_q = False
    for tname, alerts in quality.items():
        if not alerts:
            continue
        any_q = True
        lines.append("")
        lines.append(f"### `{tname}`")
        for a in alerts:
            lines.append(f"- **[{a.severity}|{a.kind}]** `{a.column}`: {a.detail}")
    if not any_q:
        lines.append("")
        lines.append("_Nenhum alerta de qualidade (zero-custo) disparado._")
    lines.append("")

    # Nota de escopo (honestidade)
    lines.append("---")
    lines.append("_Fora do escopo zero-custo (não verificado): null/empty count, "
                 "drift no tail (além do sample), format-mix, datas impossíveis, "
                 "range. Ver docs/theory/schema-gadget-design.md._")
    return "\n".join(lines)


def analyze_dataset(name: str, *, row_limit: int | None = 20000,
                    fk_min_confidence: str = "media") -> dict:
    """Carrega um dataset do hub SQLite e roda a análise.

    row_limit limita linhas por tabela (FK detect/quality em amostra; tabelas
    grandes como lineitem). None = tudo. Requer Z:/tcf-data/interim/<name>.db.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/
    from dataset_reader import DatasetReader

    r = DatasetReader(name)
    tables: dict[str, dict[str, list]] = {}
    pks: dict[str, list[str]] = {}
    for t in r.tables:
        tables[t] = r.columns(t, limit=row_limit)
        pks[t] = r.pk(t)
    r.close()
    return analyze_tables(tables, pks=pks, fk_min_confidence=fk_min_confidence)
