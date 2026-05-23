"""Download Online Retail dataset from UCI ML Repository.

Writes CSV to the configured data_root/external/online-retail/ and
metadata.json + sample to datasets/canonical/online-retail/.

UCI dataset 352: ~541,909 transactions from a UK-based online retailer
(2010-2011). Contains UnitPrice with .99/.95/.50 patterns (rounded
prices) — primary target pra testar natureza #8 arredondamento.

Usage:
    pip install -e ".[datasets]"
    python scripts/setup_online_retail.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import external_dir, ensure_dirs, PROJECT_ROOT  # noqa: E402

UCI_URL = (
    "https://archive.ics.uci.edu/static/public/352/online+retail.zip"
)

# Online Retail schema — transactional sales.
RETAIL_SCHEMA = {
    "online_retail": {
        "pk": None,  # InvoiceNo is NOT unique (multiple rows per invoice)
        "fk": {},
        "missing_value_marker": None,  # Description has NaN occasionally
        "columns": {
            "InvoiceNo":   {"type": "string", "nullable": False,
                            "note": "Invoice number; some have 'C' prefix (canceled)"},
            "StockCode":   {"type": "string", "nullable": False,
                            "note": "Product code"},
            "Description": {"type": "string", "nullable": True,
                            "note": "Product description (~0.27% NaN)"},
            "Quantity":    {"type": "int", "nullable": False,
                            "note": "Can be negative (returns)"},
            "InvoiceDate": {"type": "datetime", "nullable": False,
                            "note": "Format: M/D/YYYY HH:MM"},
            "UnitPrice":   {"type": "float", "nullable": False,
                            "note": "GBP; padroes .99/.95/.50 (natureza #8 arredondamento)"},
            "CustomerID":  {"type": "float", "nullable": True,
                            "note": "Customer code (~25% NaN)"},
            "Country":     {"type": "string", "nullable": False,
                            "note": "Country name"},
        },
    }
}


def download_online_retail(verbose: bool = True):
    try:
        import requests
    except ImportError:
        sys.exit("requests not installed. Run: pip install requests")
    try:
        import pandas as pd
    except ImportError:
        sys.exit("pandas not installed. Run: pip install -e \".[datasets]\"")

    ensure_dirs()
    output = external_dir("online-retail")
    output.mkdir(parents=True, exist_ok=True)

    zip_path = output / "raw.zip"
    csv_path = output / "online_retail.csv"

    if verbose:
        print(f"[retail] downloading from UCI -> {zip_path}")
        print(f"[retail] url: {UCI_URL}")

    r = requests.get(UCI_URL, timeout=180)  # 45MB pode demorar
    r.raise_for_status()
    zip_path.write_bytes(r.content)
    if verbose:
        print(f"[retail] downloaded: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")

    # Unzip — UCI 352 ships as Excel .xlsx
    import zipfile
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if verbose:
            print(f"[retail] zip contents: {names}")
        xlsx_in_zip = next(
            (n for n in names if n.endswith(".xlsx")), None
        )
        if xlsx_in_zip is None:
            # Talvez tenha CSV diretamente
            csv_in_zip = next(
                (n for n in names if n.endswith(".csv")), None
            )
            if csv_in_zip is None:
                sys.exit(f"[retail] no .xlsx or .csv found in zip: {names}")
            with zf.open(csv_in_zip) as src, csv_path.open("wb") as dst:
                dst.write(src.read())
            df = pd.read_csv(csv_path, encoding="latin-1")
        else:
            # Extract xlsx + convert para CSV
            xlsx_path = output / "online_retail.xlsx"
            with zf.open(xlsx_in_zip) as src, xlsx_path.open("wb") as dst:
                dst.write(src.read())
            if verbose:
                print(f"[retail] reading xlsx ({xlsx_path.stat().st_size / 1024 / 1024:.1f} MB)...")
            df = pd.read_excel(xlsx_path)
            df.to_csv(csv_path, index=False, encoding="utf-8")
            if verbose:
                print(f"[retail] converted xlsx -> CSV: {csv_path} "
                      f"({csv_path.stat().st_size / 1024 / 1024:.1f} MB)")

    rows, cols = len(df), len(df.columns)
    if verbose:
        print(f"[retail] parsed: {rows} rows x {cols} columns")
        print(f"[retail] columns: {list(df.columns)}")

    return output, rows, cols, df


def write_metadata(row_count: int, col_count: int, df) -> None:
    meta_dir = PROJECT_ROOT / "datasets" / "canonical" / "online-retail"
    meta_dir.mkdir(parents=True, exist_ok=True)

    # Count missing values per column
    missing_counts = {}
    if df is not None:
        for col in df.columns:
            n_null = int(df[col].isna().sum())
            if n_null > 0:
                missing_counts[col] = n_null

    meta = {
        "name": "online-retail",
        "source": "UCI ML Repository (dataset 352)",
        "origin": "https://archive.ics.uci.edu/dataset/352/online+retail",
        "download_url": UCI_URL,
        "license": "CC BY 4.0",
        "citation": "Chen, D. (2015). Online Retail. UCI Machine Learning Repository.",
        "downloaded_via": "requests (UCI direct download) + pandas (xlsx -> csv)",
        "row_counts": {"online_retail": row_count},
        "column_count": col_count,
        "missing_values_per_column": missing_counts,
        "natureza_alvo": "UnitPrice tem padrao .99/.95/.50 — testar #8 arredondamento (T-EXP-NATUREZAS-RARAS-V2 futuro)",
        "tables": RETAIL_SCHEMA,
    }

    meta_path = meta_dir / "metadata.json"
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[retail] metadata: {meta_path}")


def generate_sample(external_path: Path, n_rows: int = 100) -> None:
    samples_dir = PROJECT_ROOT / "datasets" / "samples" / "online-retail"
    samples_dir.mkdir(parents=True, exist_ok=True)

    src = external_path / "online_retail.csv"
    dst = samples_dir / "online-retail-sample.csv"

    with src.open("r", encoding="utf-8") as f:
        lines = []
        for i, line in enumerate(f):
            if i > n_rows:
                break
            lines.append(line)

    dst.write_text("".join(lines), encoding="utf-8")
    size_kb = dst.stat().st_size / 1024
    print(f"[retail]   sample: online-retail-sample.csv "
          f"({size_kb:.1f} KB, {n_rows} rows)")


def main():
    output, rows, cols, df = download_online_retail()
    write_metadata(rows, cols, df)
    generate_sample(output, n_rows=100)

    print(f"\n[retail] Done. {rows:,} rows x {cols} columns.")
    print(f"[retail] Raw data: {output}")
    print(f"[retail] Metadata + sample: datasets/canonical/online-retail/")
    print(f"[retail] Next: python scripts/csv_to_sqlite.py")


if __name__ == "__main__":
    main()
