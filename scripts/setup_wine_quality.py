"""Download Wine Quality dataset via OpenML.

Writes CSV to the configured data_root/external/wine-quality/ and
metadata.json + sample to datasets/canonical/wine-quality/.

Wine Quality has 2 variants (red, white) — both downloaded and merged
with a 'variant' column. 1599 red + 4898 white = 6497 total rows.

Usage:
    pip install -e ".[datasets]"
    python scripts/setup_wine_quality.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import external_dir, ensure_dirs, PROJECT_ROOT  # noqa: E402


# Wine Quality schema — features quimicas decimais + quality target.
WINE_SCHEMA = {
    "wine": {
        "pk": None,
        "fk": {},
        "missing_value_marker": None,
        "columns": {
            "fixed_acidity":        {"type": "float", "nullable": False},
            "volatile_acidity":     {"type": "float", "nullable": False},
            "citric_acid":          {"type": "float", "nullable": False},
            "residual_sugar":       {"type": "float", "nullable": False},
            "chlorides":            {"type": "float", "nullable": False},
            "free_sulfur_dioxide":  {"type": "float", "nullable": False},
            "total_sulfur_dioxide": {"type": "float", "nullable": False},
            "density":              {"type": "float", "nullable": False},
            "pH":                   {"type": "float", "nullable": False},
            "sulphates":            {"type": "float", "nullable": False},
            "alcohol":              {"type": "float", "nullable": False},
            "quality":              {"type": "int", "nullable": False,
                                     "note": "Target: 0-10", "target": True},
            "variant":              {"type": "string", "nullable": False,
                                     "note": "red or white"},
        },
    }
}


def download_wine_quality(verbose: bool = True):
    try:
        from sklearn.datasets import fetch_openml
    except ImportError:
        sys.exit(
            "scikit-learn not installed. Run:\n"
            "    pip install -e \".[datasets]\""
        )
    try:
        import pandas as pd
    except ImportError:
        sys.exit("pandas not installed. Run: pip install -e \".[datasets]\"")

    ensure_dirs()
    output = external_dir("wine-quality")
    output.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"[wine] downloading from OpenML (red id=40691, white id=40692) -> {output}")

    # Red wine: OpenML id=40691
    red_data = fetch_openml(data_id=40691, as_frame=True, parser="auto")
    df_red = red_data.frame.copy()
    df_red["variant"] = "red"

    # White wine: OpenML id=40692
    white_data = fetch_openml(data_id=40692, as_frame=True, parser="auto")
    df_white = white_data.frame.copy()
    df_white["variant"] = "white"

    # Merge
    df = pd.concat([df_red, df_white], ignore_index=True)

    if verbose:
        print(f"[wine] red:   {len(df_red)} rows")
        print(f"[wine] white: {len(df_white)} rows")
        print(f"[wine] total: {len(df)} rows x {len(df.columns)} columns")
        print(f"[wine] columns: {list(df.columns)}")

    csv_path = output / "wine.csv"
    df.to_csv(csv_path, index=False)

    size_kb = csv_path.stat().st_size / 1024
    if verbose:
        print(f"[wine] saved: {csv_path} ({size_kb:.1f} KB)")

    return output, len(df), len(df.columns), df


def write_metadata(row_count: int, col_count: int, df) -> None:
    meta_dir = PROJECT_ROOT / "datasets" / "canonical" / "wine-quality"
    meta_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "name": "wine-quality",
        "source": "UCI ML Repository (via OpenML id=40691 red, id=40692 white)",
        "origin": "https://archive.ics.uci.edu/dataset/186/wine+quality",
        "openml_url_red": "https://www.openml.org/d/40691",
        "openml_url_white": "https://www.openml.org/d/40692",
        "license": "CC BY 4.0",
        "citation": "Cortez, P., Cerdeira, A., Almeida, F., Matos, T., & Reis, J. (2009). Modeling wine preferences by data mining from physicochemical properties. Decision Support Systems, 47(4), 547-553.",
        "downloaded_via": "sklearn.datasets.fetch_openml",
        "row_counts": {"wine": row_count},
        "column_count": col_count,
        "tables": WINE_SCHEMA,
    }

    meta_path = meta_dir / "metadata.json"
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[wine] metadata: {meta_path}")


def generate_sample(external_path: Path, n_rows: int = 100) -> None:
    samples_dir = PROJECT_ROOT / "datasets" / "samples" / "wine-quality"
    samples_dir.mkdir(parents=True, exist_ok=True)

    src = external_path / "wine.csv"
    dst = samples_dir / "wine-sample.csv"

    with src.open("r", encoding="utf-8") as f:
        lines = []
        for i, line in enumerate(f):
            if i > n_rows:
                break
            lines.append(line)

    dst.write_text("".join(lines), encoding="utf-8")
    size_kb = dst.stat().st_size / 1024
    print(f"[wine]   sample: wine-sample.csv ({size_kb:.1f} KB, {n_rows} rows)")


def main():
    output, rows, cols, df = download_wine_quality()
    write_metadata(rows, cols, df)
    generate_sample(output, n_rows=100)

    print(f"\n[wine] Done. {rows:,} rows x {cols} columns.")
    print(f"[wine] Raw data: {output}")
    print(f"[wine] Metadata + sample: in git under datasets/canonical/wine-quality/")
    print(f"[wine] Next: python scripts/csv_to_sqlite.py")


if __name__ == "__main__":
    main()
