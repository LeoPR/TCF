"""Generate quality reports (Markdown) for each canonical dataset.

Reads from the SQLite hub via `dataset_reader.DatasetReader` and writes
`datasets/quality-reports/{name}.md` with:
- Schema summary (PK, FK, types)
- Row counts per table
- Per-column statistics (numeric or categorical)
- Missing value counts
- Sample rows (head, mid, tail)

**Architecture note:** this script is a CLIENT of `dataset_reader.py`.
Both live in `scripts/` and are purely for our project tooling — they are
not part of the TCF core (`src/tcf/`).

Usage:
    python scripts/quality_report.py              # all datasets
    python scripts/quality_report.py tpch-sf001   # single dataset
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import PROJECT_ROOT  # noqa: E402
from dataset_reader import DatasetReader, is_numeric  # noqa: E402


REPORTS_DIR = PROJECT_ROOT / "datasets" / "quality-reports"


# ---------------------------------------------------------------------------
# Markdown formatting helpers
# ---------------------------------------------------------------------------

def _fmt_num(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        if abs(v) < 0.01 or abs(v) >= 1e6:
            return f"{v:.4e}"
        return f"{v:,.4f}"
    return str(v)


def _fmt_text_short(v, max_len: int = 40) -> str:
    if v is None:
        return "—"
    s = str(v)
    if len(s) > max_len:
        return s[:max_len - 1] + "…"
    return s


def _section(title: str, level: int = 2) -> str:
    return "\n" + ("#" * level) + " " + title + "\n"


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_report(reader: DatasetReader) -> str:
    meta = reader.metadata
    lines: list[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Header
    lines.append(f"# Quality Report — {reader.name}\n")
    lines.append(f"_Generated: {now}_\n")
    if "source" in meta:
        lines.append(f"- **Source:** {meta['source']}")
    if "origin" in meta:
        lines.append(f"- **Origin:** {meta['origin']}")
    if "license" in meta:
        lines.append(f"- **License:** {meta['license']}")
    if "citation" in meta:
        lines.append(f"- **Citation:** {meta['citation']}")

    # Schema summary
    lines.append(_section("Schema Summary"))
    lines.append("| Table | Rows | Cols | PK | FKs |")
    lines.append("|-------|------|------|-----|-----|")
    total_rows = 0
    total_cols = 0
    for table in reader.tables:
        n_rows = reader.row_count(table)
        n_cols = len(reader.column_names(table))
        pk = ", ".join(reader.pk(table)) or "—"
        fk_list = list(reader.fk(table).keys())
        fk_str = ", ".join(fk_list) if fk_list else "—"
        lines.append(f"| `{table}` | {n_rows:,} | {n_cols} | `{pk}` | `{fk_str}` |")
        total_rows += n_rows
        total_cols += n_cols
    lines.append(f"\n**Total:** {total_rows:,} rows across {len(reader.tables)} tables "
                 f"({total_cols} columns combined)")

    # Per-table details
    for table in reader.tables:
        lines.append(_section(f"Table: `{table}`"))
        n_rows = reader.row_count(table)
        schema = reader.schema(table)
        lines.append(f"- **Rows:** {n_rows:,}")
        lines.append(f"- **Columns:** {len(schema)}")
        if reader.pk(table):
            lines.append(f"- **PK:** `{', '.join(reader.pk(table))}`")
        if reader.fk(table):
            fk_lines = [f"`{k}` → `{v}`" for k, v in reader.fk(table).items()]
            lines.append(f"- **FK:** {', '.join(fk_lines)}")

        # Column stats
        lines.append(_section("Column Statistics", level=3))
        lines.append("| Column | Type | Nulls | Distinct/Min | Max | Mean | StdDev |")
        lines.append("|--------|------|-------|--------------|-----|------|--------|")
        for col_name, col_meta in schema.items():
            stats = reader.column_stats(table, col_name)
            typ = col_meta["type"]
            nulls = stats.get("null_count", 0)
            nulls_str = f"{nulls:,}" if nulls > 0 else "0"
            if is_numeric(col_meta):
                mn = _fmt_num(stats.get("min"))
                mx = _fmt_num(stats.get("max"))
                mean = _fmt_num(stats.get("mean"))
                stdev = _fmt_num(stats.get("stdev"))
                lines.append(
                    f"| `{col_name}` | {typ} | {nulls_str} | {mn} | {mx} | {mean} | {stdev} |"
                )
            else:
                distinct = stats.get("distinct", "—")
                lines.append(
                    f"| `{col_name}` | {typ} | {nulls_str} | {distinct:,} | — | — | — |"
                )

        # Top values for text columns (up to 3 columns max, to keep reports short)
        text_cols = [c for c, m in schema.items() if not is_numeric(m)]
        if text_cols:
            lines.append(_section("Top values (categorical columns)", level=3))
            for col in text_cols[:3]:
                stats = reader.column_stats(table, col)
                distinct = stats.get("distinct", 0)
                entropy = stats.get("entropy_bits", 0)
                lines.append(f"\n**`{col}`** — distinct: {distinct:,}, entropy: {entropy} bits")
                tops = stats.get("top_values", [])
                if tops:
                    for val, count in tops:
                        pct = 100.0 * count / max(1, n_rows)
                        lines.append(f"- `{_fmt_text_short(val)}`: {count:,} ({pct:.1f}%)")
            if len(text_cols) > 3:
                lines.append(
                    f"\n_(showing 3 of {len(text_cols)} categorical columns — see metadata.json for full list)_"
                )

        # Sample rows
        lines.append(_section("Sample rows (first 3)", level=3))
        sample = reader.rows(table, limit=3)
        if sample:
            cols = list(sample[0].keys())
            # Truncate columns if too many
            display_cols = cols[:6]
            truncated_note = f" (showing 6 of {len(cols)} columns)" if len(cols) > 6 else ""
            lines.append(f"_{truncated_note}_" if truncated_note else "")
            lines.append("| " + " | ".join(f"`{c}`" for c in display_cols) + " |")
            lines.append("|" + "|".join("---" for _ in display_cols) + "|")
            for row in sample:
                vals = [_fmt_text_short(row.get(c)) for c in display_cols]
                lines.append("| " + " | ".join(vals) + " |")

    return "\n".join(lines) + "\n"


def write_report(dataset_name: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / f"{dataset_name}.md"
    with DatasetReader(dataset_name) as r:
        content = build_report(r)
    out_path.write_text(content, encoding="utf-8")
    return out_path


def list_datasets() -> list[str]:
    root = PROJECT_ROOT / "datasets" / "canonical"
    return sorted([p.name for p in root.iterdir()
                   if p.is_dir() and (p / "metadata.json").exists()])


def main():
    parser = argparse.ArgumentParser(description="Generate quality reports")
    parser.add_argument("dataset", nargs="?", help="dataset name (default: all)")
    args = parser.parse_args()

    targets = [args.dataset] if args.dataset else list_datasets()
    for name in targets:
        path = write_report(name)
        size_kb = path.stat().st_size / 1024
        print(f"[quality] {name}: {path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
