"""Phase 1 results analysis — accuracy by format, layer, model, and question.

Usage:
    python experiments/eval/analyze_phase1.py
    python experiments/eval/analyze_phase1.py --format tsv   # machine-readable
"""

from __future__ import annotations
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PHASE1_DIR = ROOT / "experiments" / "results" / "phase1"


def load_manifest(path: Path) -> list[dict]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def accuracy(vals: list[bool]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def print_table(headers: list[str], rows: list[list], fmt: str = "pretty") -> None:
    if fmt == "tsv":
        print("\t".join(headers))
        for row in rows:
            print("\t".join(str(c) for c in row))
        return
    widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0))
              for i, h in enumerate(headers)]
    sep = "  "
    print(sep.join(f"{h:{widths[i]}}" for i, h in enumerate(headers)))
    print(sep.join("-" * w for w in widths))
    for row in rows:
        print(sep.join(f"{str(c):{widths[i]}}" for i, c in enumerate(row)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["pretty", "tsv"], default="pretty")
    parser.add_argument("--phase-dir", default=str(PHASE1_DIR))
    args = parser.parse_args()
    fmt = args.format

    manifest_path = Path(args.phase_dir) / "manifest.jsonl"
    if not manifest_path.exists():
        print(f"[ERROR] No manifest at {manifest_path}", file=sys.stderr)
        sys.exit(1)

    entries = load_manifest(manifest_path)
    total = len(entries)

    # Enrich with error_type from per-model result files
    key_to_error: dict[str, str] = {}
    results_dir = Path(args.phase_dir) / "results"
    if results_dir.exists():
        for f in results_dir.glob("*.jsonl"):
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        r = json.loads(line)
                        # Reconstruct the key from run_matrix._run_key logic
                        k = "|".join([
                            r.get("model", ""), r.get("format", ""),
                            r.get("numeric") or "N", r.get("fk_mode") or "N",
                            str(r.get("include_sorted", "N")),
                            r.get("layer", ""), r.get("question", ""),
                        ])
                        if "error_type" in r:
                            key_to_error[k] = r["error_type"]
                    except json.JSONDecodeError:
                        pass

    for e in entries:
        if e.get("key") in key_to_error:
            e["error_type"] = key_to_error[e["key"]]

    print(f"\n=== PHASE 1 ANALYSIS ({total} entries) ===\n")

    # ── 1. Accuracy by (model, layer) ───────────────────────────────────────
    model_layer: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for e in entries:
        model_layer[e["model"]][e["layer"]].append(e["correct"])

    print("[1] Accuracy by Model × Layer")
    headers = ["Model", "math_ctrl", "decode", "compute", "N"]
    rows = []
    for model in sorted(model_layer):
        mc = accuracy(model_layer[model].get("math_control", []))
        dec = accuracy(model_layer[model].get("decode_only", []))
        comp = accuracy(model_layer[model].get("compute", []))
        n = sum(len(v) for v in model_layer[model].values())
        rows.append([model, f"{mc:.0%}", f"{dec:.0%}", f"{comp:.0%}", n])
    rows.sort(key=lambda r: r[3], reverse=True)
    print_table(headers, rows, fmt)

    # ── 2. Accuracy by (format, layer) ──────────────────────────────────────
    print("\n[2] Accuracy by Format × Layer (compute only)")
    fmt_qs: dict[str, list[bool]] = defaultdict(list)
    for e in entries:
        if e["layer"] == "compute":
            f = e.get("format", "none")
            fmt_qs[f].append(e["correct"])

    headers2 = ["Format", "Accuracy", "N"]
    rows2 = [(f, f"{accuracy(v):.0%}", len(v)) for f, v in sorted(fmt_qs.items())]
    rows2.sort(key=lambda r: r[1], reverse=True)
    print_table(headers2, rows2, fmt)

    # ── 3. Accuracy by question (across all models and formats) ─────────────
    print("\n[3] Accuracy by Question (compute layer, all models, all formats)")
    q_acc: dict[str, list[bool]] = defaultdict(list)
    for e in entries:
        if e["layer"] == "compute":
            q_acc[e["question"]].append(e["correct"])

    headers3 = ["Question", "Accuracy", "N"]
    rows3 = [(q, f"{accuracy(v):.0%}", len(v)) for q, v in sorted(q_acc.items())]
    rows3.sort(key=lambda r: r[1], reverse=True)
    print_table(headers3, rows3, fmt)

    # ── 4. Per-model accuracy by format (compute) ───────────────────────────
    print("\n[4] Per-model Accuracy by Format (compute)")
    mf_acc: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for e in entries:
        if e["layer"] == "compute":
            mf_acc[e["model"]][e.get("format", "none")].append(e["correct"])

    all_fmts = sorted({e.get("format", "none") for e in entries if e["layer"] == "compute"})
    headers4 = ["Model"] + all_fmts
    rows4 = []
    for model in sorted(mf_acc):
        row = [model] + [f"{accuracy(mf_acc[model].get(f, [])):.0%}" for f in all_fmts]
        rows4.append(row)
    print_table(headers4, rows4, fmt)

    # ── 5. Error type distribution ───────────────────────────────────────────
    print("\n[5] Error type distribution (compute, incorrect only)")
    err_counts: dict[str, int] = defaultdict(int)
    total_incorrect = 0
    for e in entries:
        if e["layer"] == "compute" and not e["correct"]:
            err_counts[e.get("error_type", "unknown")] += 1
            total_incorrect += 1

    if total_incorrect:
        headers5 = ["Error Type", "Count", "%"]
        rows5 = [(et, c, f"{c/total_incorrect:.0%}") for et, c in
                 sorted(err_counts.items(), key=lambda x: -x[1])]
        print_table(headers5, rows5, fmt)

    # ── 6. Summary for TICKETS.md ────────────────────────────────────────────
    print("\n[6] Survivors (compute accuracy >= 30%)")
    survivors = [
        model for model in sorted(model_layer)
        if accuracy(model_layer[model].get("compute", [])) >= 0.30
    ]
    if not survivors:
        # Fallback: top 3
        ranked = sorted(model_layer, key=lambda m: -accuracy(model_layer[m].get("compute", [])))
        survivors = ranked[:3]
        print(f"  (No model >= 30% — using top 3 fallback)")
    for m in survivors:
        comp = accuracy(model_layer[m].get("compute", []))
        print(f"  -> {m}: compute={comp:.0%}")

    # Check completeness
    expected = 210
    print(f"\n[Status] {total}/{expected} entries complete ({total/expected:.0%})")
    if total < expected:
        done_models = set(e["model"] for e in entries)
        print(f"  Done models: {sorted(done_models)}")


if __name__ == "__main__":
    main()
