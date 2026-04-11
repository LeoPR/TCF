"""Download Adult (Census Income) dataset via OpenML.

Writes CSV to the configured data_root/external/adult-census/ and generates
a small 100-row sample in datasets/samples/adult-census/ for git.

Usage:
    pip install -e ".[datasets]"
    python scripts/setup_adult.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import external_dir, ensure_dirs, PROJECT_ROOT  # noqa: E402


# Adult schema — based on UCI Adult dataset specification.
# OpenML version=2 uses these column names (with hyphens).
ADULT_SCHEMA = {
    "adult": {
        "pk": None,  # no primary key in the original dataset
        "fk": {},
        "missing_value_marker": "?",
        "columns": {
            "age":            {"type": "int", "nullable": False},
            "workclass":      {"type": "string", "nullable": True,
                               "note": "? means missing"},
            "fnlwgt":         {"type": "int", "nullable": False,
                               "note": "Census final weight"},
            "education":      {"type": "string", "nullable": False},
            "education-num":  {"type": "int", "nullable": False,
                               "note": "Years of education"},
            "marital-status": {"type": "string", "nullable": False},
            "occupation":     {"type": "string", "nullable": True,
                               "note": "? means missing"},
            "relationship":   {"type": "string", "nullable": False},
            "race":           {"type": "string", "nullable": False},
            "sex":            {"type": "string", "nullable": False,
                               "note": "Male or Female"},
            "capital-gain":   {"type": "int", "nullable": False},
            "capital-loss":   {"type": "int", "nullable": False},
            "hours-per-week": {"type": "int", "nullable": False},
            "native-country": {"type": "string", "nullable": True,
                               "note": "? means missing"},
            "class":          {"type": "string", "nullable": False,
                               "note": "Target: >50K or <=50K",
                               "target": True},
        },
    }
}


def download_adult(verbose: bool = True) -> tuple[Path, int, int]:
    """Download Adult dataset via sklearn fetch_openml.

    Returns (output_dir, row_count, col_count).
    """
    try:
        from sklearn.datasets import fetch_openml
    except ImportError:
        sys.exit(
            "scikit-learn not installed. Run:\n"
            "    pip install -e \".[datasets]\""
        )

    ensure_dirs()
    output = external_dir("adult-census")
    output.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"[adult] downloading from OpenML (id=1590) -> {output}")

    data = fetch_openml("adult", version=2, as_frame=True, parser="auto")
    df = data.frame

    if verbose:
        print(f"[adult] downloaded: {len(df)} rows x {len(df.columns)} columns")
        print(f"[adult] columns: {list(df.columns)}")

    csv_path = output / "adult.csv"
    df.to_csv(csv_path, index=False)

    size_kb = csv_path.stat().st_size / 1024
    if verbose:
        print(f"[adult] saved: {csv_path} ({size_kb:.1f} KB)")

    return output, len(df), len(df.columns), df


def write_metadata(row_count: int, col_count: int, df) -> None:
    """Write metadata.json for the dataset."""
    meta_dir = PROJECT_ROOT / "datasets" / "canonical" / "adult-census"
    meta_dir.mkdir(parents=True, exist_ok=True)

    # Count missing values per column (marked as NaN after pandas parsing)
    missing_counts = {}
    for col in df.columns:
        n_null = int(df[col].isna().sum())
        if n_null > 0:
            missing_counts[col] = n_null

    meta = {
        "name": "adult-census",
        "source": "UCI ML Repository (via OpenML id=1590)",
        "origin": "https://archive.ics.uci.edu/dataset/2/adult",
        "openml_url": "https://www.openml.org/d/1590",
        "license": "CC BY 4.0",
        "citation": "Becker, B. and Kohavi, R. (1996). Adult. UCI Machine Learning Repository. https://doi.org/10.24432/C5XW20",
        "downloaded_via": "sklearn.datasets.fetch_openml",
        "row_counts": {"adult": row_count},
        "column_count": col_count,
        "missing_values_per_column": missing_counts,
        "tables": ADULT_SCHEMA,
    }

    meta_path = meta_dir / "metadata.json"
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[adult] metadata: {meta_path}")


def generate_sample(external_path: Path, n_rows: int = 100) -> None:
    """Copy first N rows to datasets/samples/adult-census/ for git."""
    samples_dir = PROJECT_ROOT / "datasets" / "samples" / "adult-census"
    samples_dir.mkdir(parents=True, exist_ok=True)

    src = external_path / "adult.csv"
    dst = samples_dir / "adult-sample.csv"

    with src.open("r", encoding="utf-8") as f:
        lines = []
        for i, line in enumerate(f):
            if i > n_rows:  # header + n_rows
                break
            lines.append(line)

    dst.write_text("".join(lines), encoding="utf-8")
    size_kb = dst.stat().st_size / 1024
    print(f"[adult]   sample: adult-sample.csv ({size_kb:.1f} KB, {n_rows} rows)")


def main():
    output, rows, cols, df = download_adult()
    write_metadata(rows, cols, df)
    generate_sample(output, n_rows=100)

    print(f"\n[adult] Done. {rows:,} rows x {cols} columns.")
    print(f"[adult] Raw data: {output}")
    print(f"[adult] Metadata + sample: in git under datasets/canonical/adult-census/")


if __name__ == "__main__":
    main()
