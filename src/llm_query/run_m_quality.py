"""M-quality — post-hoc SQL quality analysis sobre todos os manifests.

Aplica `sql_quality.score_sql_quality()` em todos os SQLs gerados em
M3, M5, M6, M6b, M7, M8, M8b, M9, M9-Adult, M-strat. Cruza com accuracy:
- SQLs corretas têm quality score mais alto?
- Modelos diferem em "elegância"?
- Quality discrimina mesmo quando accuracy é igual?

Não roda LLM. Pura análise post-hoc do que já está no disco.

Output:
- experiments/results/m_quality/per_record.jsonl  (1 linha por SQL)
- experiments/results/m_quality/summary.md
- experiments/results/m_quality/report.json (estruturado)
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts"))

from llm_eval.sql_quality import score_sql_quality
from data_sources import load_dataset


RESULTS_DIR = ROOT / "experiments" / "results" / "m_quality"


# Manifests in scope (Linha B SQL-generation experiments)
MANIFESTS = [
    ("m3_crossdomain",     ROOT / "experiments/results/m3_crossdomain/manifest.jsonl"),
    ("m5_intermediate",    ROOT / "experiments/results/m5_intermediate/manifest.jsonl"),
    ("m6_filter",          ROOT / "experiments/results/m6_filter/manifest.jsonl"),
    ("m6b_having_fix",     ROOT / "experiments/results/m6b_having_fix/manifest.jsonl"),
    ("m7_complex",         ROOT / "experiments/results/m7_complex/manifest.jsonl"),
    ("m8_safe_sql",        ROOT / "experiments/results/m8_safe_sql/manifest.jsonl"),
    ("m8b_safe_sql_combos", ROOT / "experiments/results/m8b_safe_sql_combos/manifest.jsonl"),
    ("m9_canonical",       ROOT / "experiments/results/m9_canonical/manifest.jsonl"),
    ("m9_adult",           ROOT / "experiments/results/m9_adult/manifest.jsonl"),
    ("m_strat",            ROOT / "experiments/results/m_strat/manifest.jsonl"),
]


def _load_records(path: Path) -> list[dict]:
    """Load and dedup manifest (last occurrence wins)."""
    if not path.exists():
        return []
    by_key = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            by_key[r["key"]] = r
        except Exception:
            continue
    return list(by_key.values())


def _resolve_tables_for_record(record: dict, cache: dict) -> dict:
    """Reconstruct tables dict for a given record (deterministic from seed+source).

    Cached by (source, seed, n_orders/volume) to avoid reload.
    """
    # Determine source string
    if "dataset" in record and record.get("dataset", "").startswith(("tpch", "adult")):
        source = f"canonical:{record['dataset']}"
    elif "domain" in record:
        # Synthetic with domain (M3-M8 era)
        domain_map = {
            "retail": "synthetic:retail_sales",
            "medical": "synthetic:medical_consultations",
            "financial": "synthetic:financial_transactions",
        }
        source = domain_map.get(record["domain"])
        if source is None:
            return {}
    elif "dataset" in record and "adult" in record.get("dataset", ""):
        source = "canonical:adult-census"
    else:
        return {}

    seed = record.get("seed", 42)
    volume = record.get("volume") or record.get("n_orders") or 100

    cache_key = (source, seed, volume)
    if cache_key not in cache:
        try:
            if source.startswith("synthetic:"):
                tables, _ = load_dataset(source, n_orders=volume, seed=seed)
            else:
                stratify = "class" if "adult" in source else None
                tables, _ = load_dataset(source, volume=volume, seed=seed, stratify_by=stratify)
            cache[cache_key] = tables
        except Exception as e:
            print(f"  WARN: failed to load {source} seed={seed} vol={volume}: {e}", file=sys.stderr)
            cache[cache_key] = {}
    return cache[cache_key]


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def run_analysis(manifests_to_process: list[str] | None = None) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    per_record_path = RESULTS_DIR / "per_record.jsonl"
    report_path = RESULTS_DIR / "report.json"
    summary_path = RESULTS_DIR / "summary.md"

    # Reset output (post-hoc; always regenerate fresh)
    if per_record_path.exists():
        per_record_path.unlink()

    tables_cache: dict = {}
    all_per_record = []

    for phase, mpath in MANIFESTS:
        if manifests_to_process and phase not in manifests_to_process:
            continue
        records = _load_records(mpath)
        if not records:
            print(f"  {phase}: empty / not found")
            continue

        n_processed = 0
        n_skipped_no_sql = 0
        n_no_tables = 0

        for r in records:
            sql = r.get("sql", "").strip()
            if not sql:
                n_skipped_no_sql += 1
                continue

            tables = _resolve_tables_for_record(r, tables_cache)
            if not tables:
                n_no_tables += 1
                # Still score with empty schema (tables_exist will be False)

            quality = score_sql_quality(sql, tables, conn=None)
            qd = quality.to_dict() if hasattr(quality, "to_dict") else {
                "has_explicit_join": quality.has_explicit_join,
                "join_uses_on": quality.join_uses_on,
                "no_select_star": quality.no_select_star,
                "single_result_col": quality.single_result_col,
                "tables_exist": quality.tables_exist,
                "token_count": quality.token_count,
                "has_subquery": quality.has_subquery,
                "has_cte": quality.has_cte,
            }

            entry = {
                "phase": phase,
                "key": r["key"],
                "model": r.get("model", "?"),
                "question": r.get("question", "?"),
                "ok": r.get("ok", False),
                "reason": r.get("reason", "?"),
                "quality_score": quality.score(),
                **qd,
            }
            all_per_record.append(entry)
            n_processed += 1

        print(f"  {phase}: {n_processed} SQLs scored ({n_skipped_no_sql} no SQL, {n_no_tables} no tables)")

    # Persist per-record
    with open(per_record_path, "w", encoding="utf-8") as fh:
        for entry in all_per_record:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\n  Per-record: {len(all_per_record)} records ->{per_record_path}")

    # Aggregate analysis
    report = analyze(all_per_record)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    summary_path.write_text(format_summary_md(report), encoding="utf-8")
    print(f"  Report:     {report_path}")
    print(f"  Summary:    {summary_path}\n")

    print(format_summary_md(report))


def analyze(records: list[dict]) -> dict:
    """Aggregate analysis across all SQLs."""
    n_total = len(records)
    n_ok = sum(1 for r in records if r["ok"])

    # Quality score by ok/fail
    ok_scores = [r["quality_score"] for r in records if r["ok"]]
    fail_scores = [r["quality_score"] for r in records if not r["ok"]]

    # Per-phase
    by_phase: dict[str, dict] = defaultdict(lambda: {"ok": [], "fail": []})
    for r in records:
        if r["ok"]:
            by_phase[r["phase"]]["ok"].append(r["quality_score"])
        else:
            by_phase[r["phase"]]["fail"].append(r["quality_score"])

    # Per-model
    by_model: dict[str, list] = defaultdict(list)
    for r in records:
        by_model[r["model"]].append(r["quality_score"])

    # Quality components prevalence
    comp_keys = ["has_explicit_join", "join_uses_on", "no_select_star",
                 "single_result_col", "tables_exist", "has_subquery", "has_cte"]
    comp_prevalence = {k: sum(1 for r in records if r.get(k)) / max(n_total, 1) for k in comp_keys}

    # Discrepancies: high quality but failed
    high_q_failed = [r for r in records if not r["ok"] and r["quality_score"] >= 0.85]
    # Low quality but succeeded
    low_q_succeeded = [r for r in records if r["ok"] and r["quality_score"] < 0.5]

    return {
        "n_total": n_total,
        "n_ok": n_ok,
        "accuracy": n_ok / max(n_total, 1),
        "quality_mean_ok": statistics.mean(ok_scores) if ok_scores else 0.0,
        "quality_mean_fail": statistics.mean(fail_scores) if fail_scores else 0.0,
        "quality_std_ok": statistics.stdev(ok_scores) if len(ok_scores) > 1 else 0.0,
        "quality_std_fail": statistics.stdev(fail_scores) if len(fail_scores) > 1 else 0.0,
        "by_phase": {
            phase: {
                "n_ok": len(d["ok"]),
                "n_fail": len(d["fail"]),
                "quality_ok_mean": statistics.mean(d["ok"]) if d["ok"] else 0.0,
                "quality_fail_mean": statistics.mean(d["fail"]) if d["fail"] else 0.0,
            }
            for phase, d in by_phase.items()
        },
        "by_model": {
            model: {
                "n": len(scores),
                "quality_mean": statistics.mean(scores) if scores else 0.0,
                "quality_std": statistics.stdev(scores) if len(scores) > 1 else 0.0,
            }
            for model, scores in by_model.items()
        },
        "component_prevalence": comp_prevalence,
        "discrepancies": {
            "high_quality_failed_count": len(high_q_failed),
            "high_quality_failed_samples": [
                {"phase": r["phase"], "model": r["model"], "question": r["question"],
                 "reason": r["reason"], "quality": round(r["quality_score"], 3)}
                for r in high_q_failed[:5]
            ],
            "low_quality_succeeded_count": len(low_q_succeeded),
            "low_quality_succeeded_samples": [
                {"phase": r["phase"], "model": r["model"], "question": r["question"],
                 "quality": round(r["quality_score"], 3)}
                for r in low_q_succeeded[:5]
            ],
        },
    }


def format_summary_md(report: dict) -> str:
    lines = ["# M-quality — SQL quality post-hoc analysis", ""]
    lines.append(f"**Total SQLs avaliadas:** {report['n_total']}")
    lines.append(f"**Accuracy global:** {report['n_ok']}/{report['n_total']} = {report['accuracy']*100:.1f}%")
    lines.append("")
    lines.append("## Quality score (composto, 0-1)")
    lines.append("")
    lines.append(f"- **SQLs corretas (n={report['n_ok']}):** mean={report['quality_mean_ok']:.3f}, std={report['quality_std_ok']:.3f}")
    fails = report['n_total'] - report['n_ok']
    lines.append(f"- **SQLs erradas (n={fails}):** mean={report['quality_mean_fail']:.3f}, std={report['quality_std_fail']:.3f}")
    diff = report['quality_mean_ok'] - report['quality_mean_fail']
    lines.append(f"- **Diff (ok - fail):** {diff:+.3f}")
    if abs(diff) < 0.05:
        lines.append("  ->Quality NÃO discrimina ok vs fail (diferença < 0.05).")
    elif diff > 0:
        lines.append("  ->Quality CORRELACIONA com accuracy (SQLs corretas têm maior score).")
    else:
        lines.append("  ->Quality é INVERTIDO (SQLs erradas têm mais qualidade aparente — investigar).")
    lines.append("")

    lines.append("## Por fase")
    lines.append("")
    lines.append("| Fase | OK | Fail | Quality OK | Quality Fail |")
    lines.append("|------|---:|-----:|-----------:|-------------:|")
    for phase, d in sorted(report["by_phase"].items()):
        lines.append(f"| {phase} | {d['n_ok']} | {d['n_fail']} | {d['quality_ok_mean']:.3f} | {d['quality_fail_mean']:.3f} |")
    lines.append("")

    lines.append("## Por modelo")
    lines.append("")
    lines.append("| Modelo | N | Quality mean | Quality std |")
    lines.append("|--------|--:|-------------:|------------:|")
    for model, d in sorted(report["by_model"].items()):
        lines.append(f"| {model} | {d['n']} | {d['quality_mean']:.3f} | {d['quality_std']:.3f} |")
    lines.append("")

    lines.append("## Prevalência de componentes (% de SQLs com)")
    lines.append("")
    for k, v in report["component_prevalence"].items():
        lines.append(f"- **{k}**: {v*100:.1f}%")
    lines.append("")

    disc = report["discrepancies"]
    lines.append("## Discrepâncias")
    lines.append("")
    lines.append(f"### High quality mas falhou (quality>=0.85, ok=False): {disc['high_quality_failed_count']}")
    lines.append("")
    if disc["high_quality_failed_samples"]:
        for s in disc["high_quality_failed_samples"]:
            lines.append(f"- {s['phase']} / {s['model']} / {s['question']}: quality={s['quality']}, reason={s['reason']}")
    lines.append("")
    lines.append(f"### Low quality mas acertou (quality<0.5, ok=True): {disc['low_quality_succeeded_count']}")
    lines.append("")
    if disc["low_quality_succeeded_samples"]:
        for s in disc["low_quality_succeeded_samples"]:
            lines.append(f"- {s['phase']} / {s['model']} / {s['question']}: quality={s['quality']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="M-quality — post-hoc SQL quality")
    parser.add_argument("--phases", nargs="+", default=None,
                        help="filter to specific phases (e.g. m9_adult m_strat)")
    args = parser.parse_args()

    print("=== M-quality post-hoc analysis ===\n")
    run_analysis(args.phases)


if __name__ == "__main__":
    main()
