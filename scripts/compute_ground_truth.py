"""Compute ground truth values by executing SQL from question banks.

Reads `datasets/questions/{name}.json` and, for each question, runs its
SQL statement via `DatasetReader.query()`, then writes the result back
into the `ground_truth` field of the JSON.

Architecture:
    - Questions are authored manually (the SQL is the spec).
    - This script just executes them via the SUPPORT reader.
    - Results are canonical because SQLite types are preserved.

Usage:
    python scripts/compute_ground_truth.py              # all
    python scripts/compute_ground_truth.py tpch-sf001   # single
    python scripts/compute_ground_truth.py --preview    # dry-run, print, don't save
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import PROJECT_ROOT  # noqa: E402
from dataset_reader import DatasetReader  # noqa: E402


QUESTIONS_DIR = PROJECT_ROOT / "datasets" / "questions"


def _normalize_result(rows: list[tuple], answer_type: str):
    """Convert raw SQL result into the shape expected by answer_type.

    - numeric/count/string: single scalar if single row/col
    - pairs: list of [key, value] pairs preserving order
    """
    if answer_type in ("numeric", "count", "string"):
        if len(rows) == 1 and len(rows[0]) == 1:
            val = rows[0][0]
            if answer_type == "count" and val is not None:
                return int(val)
            return val
        # Fall through: not scalar as expected — return as-is
        return rows
    if answer_type == "pairs":
        return [list(r) for r in rows]
    return rows


def compute_for_dataset(dataset_name: str, preview: bool = False) -> None:
    qfile = QUESTIONS_DIR / f"{dataset_name}.json"
    if not qfile.exists():
        print(f"[gt] SKIP: {qfile} not found")
        return

    data = json.loads(qfile.read_text(encoding="utf-8"))
    questions = data.get("questions", [])
    print(f"\n[gt] {dataset_name}: computing {len(questions)} answers")

    with DatasetReader(dataset_name) as reader:
        for q in questions:
            qid = q["id"]
            sql = q["sql"]
            ans_type = q.get("answer_type", "numeric")
            try:
                rows = reader.query(sql)
                gt = _normalize_result(rows, ans_type)
            except Exception as exc:
                gt = f"ERROR: {exc}"
                print(f"  {qid:40s} FAIL: {exc}")
                continue

            # Preview print (truncated)
            display = str(gt)
            if len(display) > 80:
                display = display[:77] + "..."
            print(f"  {qid:40s} [{ans_type:8s}] {display}")

            q["ground_truth"] = gt

    if preview:
        print(f"[gt] --preview: not saving changes")
        return

    # Write back
    qfile.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[gt] saved: {qfile}")


def list_question_banks() -> list[str]:
    return sorted(p.stem for p in QUESTIONS_DIR.glob("*.json"))


def main():
    parser = argparse.ArgumentParser(description="Compute ground truth via SQL")
    parser.add_argument("dataset", nargs="?", help="dataset name (default: all)")
    parser.add_argument("--preview", action="store_true",
                        help="print results without saving back to JSON")
    args = parser.parse_args()

    targets = [args.dataset] if args.dataset else list_question_banks()
    for name in targets:
        compute_for_dataset(name, preview=args.preview)

    print("\n[gt] Done.")


if __name__ == "__main__":
    main()
