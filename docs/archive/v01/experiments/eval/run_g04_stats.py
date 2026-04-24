"""G04 — Stats Deduction: do pre-computed hints help LLMs?

Tests include_stats=True vs False with top configs from Phase 2.
Uses the same _run_phase infrastructure for idempotency.

Usage:
    python experiments/eval/run_g04_stats.py
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_matrix import (
    _run_phase, _load_survivors, DataCache, OllamaClient,
    RESULTS_ROOT, DEFAULT_OPTIONS,
)
from llm_eval.prompts import list_questions_by_layer


def main() -> None:
    endpoint = "http://localhost:11434"
    client = OllamaClient(endpoint)
    if not client.is_available():
        print(f"[ERROR] Ollama not available at {endpoint}", file=sys.stderr)
        sys.exit(1)

    # Use survivors from Phase 1 (exclude gpt-oss for speed)
    survivors = _load_survivors()
    models = [m for m in survivors if "gpt-oss" not in m]
    print(f"[g04] models: {models}")

    # Top configs from Phase 2
    top_configs_path = RESULTS_ROOT / "phase2" / "top_configs.json"
    if top_configs_path.exists():
        top_configs = json.loads(top_configs_path.read_text(encoding="utf-8"))["top_configs"]
    else:
        top_configs = ["raw_float/dict/True"]
    print(f"[g04] top_configs: {top_configs}")

    phase_dir = RESULTS_ROOT / "g04_stats"
    cache = DataCache()
    compute_qs = list(list_questions_by_layer("compute").keys())

    # Build combos: models × top_configs × stats(True/False) × questions
    combos: list[dict[str, Any]] = []
    for model in models:
        for cfg_str in top_configs:
            parts = cfg_str.split("/")
            numeric = parts[0] if len(parts) > 0 else "raw_float"
            fk_mode = parts[1] if len(parts) > 1 else "dict"
            inc_sorted = parts[2] != "False" if len(parts) > 2 else True

            for stats in [False, True]:
                for q in compute_qs:
                    combos.append({
                        "model": model,
                        "format": "tcf",
                        "numeric": numeric,
                        "fk_mode": fk_mode,
                        "include_sorted": inc_sorted,
                        "include_stats": stats,
                        "layer": "compute",
                        "question": q,
                    })

    print(f"[g04] {len(combos)} combinations")
    _run_phase(combos, phase_dir, client, cache, label="g04_stats")

    # Analysis
    manifest_path = phase_dir / "manifest.jsonl"
    entries = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    from collections import defaultdict
    stats_acc: dict[str, list[bool]] = defaultdict(list)
    model_stats_acc: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    q_stats_acc: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))

    for e in entries:
        stats_key = "stats=True" if e.get("include_stats") else "stats=False"
        stats_acc[stats_key].append(e["correct"])
        model_stats_acc[e["model"]][stats_key].append(e["correct"])
        q_stats_acc[e["question"]][stats_key].append(e["correct"])

    print("\n[G04 RESULTS — Stats ablation]")
    print(f"  {'Condition':15s} {'Accuracy':>9s} {'N':>5s}")
    print("  " + "-" * 32)
    for k, v in sorted(stats_acc.items()):
        acc = sum(v) / len(v) if v else 0
        print(f"  {k:15s} {acc:9.1%} {len(v):5d}")

    print("\n[G04 — Per model]")
    for model in sorted(model_stats_acc):
        parts = []
        for k in ["stats=False", "stats=True"]:
            v = model_stats_acc[model].get(k, [])
            acc = sum(v) / len(v) if v else 0
            parts.append(f"{k}={acc:.0%}")
        print(f"  {model:25s} {' | '.join(parts)}")

    print("\n[G04 — Per question (delta)]")
    for q in sorted(q_stats_acc):
        v_off = q_stats_acc[q].get("stats=False", [])
        v_on = q_stats_acc[q].get("stats=True", [])
        acc_off = sum(v_off) / len(v_off) if v_off else 0
        acc_on = sum(v_on) / len(v_on) if v_on else 0
        delta = acc_on - acc_off
        marker = " <<<" if delta > 0.05 else ""
        print(f"  {q:30s} off={acc_off:.0%}  on={acc_on:.0%}  delta={delta:+.0%}{marker}")

    # Save summary
    summary = {
        "overall": {k: sum(v) / len(v) for k, v in stats_acc.items()},
        "per_model": {
            m: {k: sum(v) / len(v) for k, v in accs.items()}
            for m, accs in model_stats_acc.items()
        },
    }
    (phase_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n[g04] results saved to {phase_dir}")


if __name__ == "__main__":
    main()
