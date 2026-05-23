"""Download Beijing PM2.5 dataset from UCI ML Repository.

Writes CSV to the configured data_root/external/beijing-pm25/ and
metadata.json + sample to datasets/canonical/beijing-pm25/.

UCI dataset 381: ~43,824 hourly air quality observations from Beijing
(2010-2014). Sensor decimals (DEWP, TEMP, PRES) + PM2.5 measurements.

Usage:
    pip install -e ".[datasets]"
    python scripts/setup_beijing_pm25.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import external_dir, ensure_dirs, PROJECT_ROOT  # noqa: E402

UCI_URL = (
    "https://archive.ics.uci.edu/static/public/381/"
    "beijing+pm2+5+data.zip"
)

# Beijing PM2.5 schema — sensor decimals + counters.
BEIJING_SCHEMA = {
    "beijing_pm25": {
        "pk": "No",
        "fk": {},
        "missing_value_marker": "NA",
        "columns": {
            "No":     {"type": "int", "nullable": False, "note": "row number"},
            "year":   {"type": "int", "nullable": False},
            "month":  {"type": "int", "nullable": False},
            "day":    {"type": "int", "nullable": False},
            "hour":   {"type": "int", "nullable": False},
            "pm2.5":  {"type": "float", "nullable": True,
                       "note": "PM2.5 concentration (ug/m^3); NA when missing"},
            "DEWP":   {"type": "float", "nullable": False,
                       "note": "Dew Point (Celsius)"},
            "TEMP":   {"type": "float", "nullable": False,
                       "note": "Temperature (Celsius)"},
            "PRES":   {"type": "float", "nullable": False,
                       "note": "Pressure (hPa)"},
            "cbwd":   {"type": "string", "nullable": False,
                       "note": "Combined wind direction (NW/NE/SE/cv)"},
            "Iws":    {"type": "float", "nullable": False,
                       "note": "Cumulated wind speed (m/s)"},
            "Is":     {"type": "int", "nullable": False,
                       "note": "Cumulated hours of snow"},
            "Ir":     {"type": "int", "nullable": False,
                       "note": "Cumulated hours of rain"},
        },
    }
}


def download_beijing_pm25(verbose: bool = True):
    try:
        import requests
    except ImportError:
        sys.exit(
            "requests not installed. Run:\n"
            "    pip install requests"
        )

    ensure_dirs()
    output = external_dir("beijing-pm25")
    output.mkdir(parents=True, exist_ok=True)

    zip_path = output / "raw.zip"
    csv_path = output / "beijing_pm25.csv"

    if verbose:
        print(f"[beijing] downloading from UCI -> {zip_path}")
        print(f"[beijing] url: {UCI_URL}")

    r = requests.get(UCI_URL, timeout=60)
    r.raise_for_status()
    zip_path.write_bytes(r.content)
    if verbose:
        print(f"[beijing] downloaded: {zip_path.stat().st_size / 1024:.1f} KB")

    # Unzip
    import zipfile
    with zipfile.ZipFile(zip_path) as zf:
        # Find the CSV inside
        names = zf.namelist()
        if verbose:
            print(f"[beijing] zip contents: {names}")
        csv_in_zip = next(n for n in names if n.endswith(".csv"))
        with zf.open(csv_in_zip) as src, csv_path.open("wb") as dst:
            dst.write(src.read())

    if verbose:
        print(f"[beijing] extracted: {csv_path} "
              f"({csv_path.stat().st_size / 1024:.1f} KB)")

    # Count rows + cols
    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
        rows, cols = len(df), len(df.columns)
        if verbose:
            print(f"[beijing] parsed: {rows} rows x {cols} columns")
            print(f"[beijing] columns: {list(df.columns)}")
    except ImportError:
        # Fallback sem pandas
        with csv_path.open(encoding="utf-8") as f:
            header = next(f).strip().split(",")
            cols = len(header)
            rows = sum(1 for _ in f)
        df = None
        if verbose:
            print(f"[beijing] parsed (no pandas): {rows} rows x {cols} columns")

    return output, rows, cols, df


def write_metadata(row_count: int, col_count: int) -> None:
    meta_dir = PROJECT_ROOT / "datasets" / "canonical" / "beijing-pm25"
    meta_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "name": "beijing-pm25",
        "source": "UCI ML Repository (dataset 381)",
        "origin": "https://archive.ics.uci.edu/dataset/381/beijing+pm2+5+data",
        "download_url": UCI_URL,
        "license": "CC BY 4.0",
        "citation": "Liang, X., et al. (2015). Assessing Beijing's PM2.5 pollution: severity, weather impact, APEC and winter heating. Proceedings of the Royal Society A, 471(2182), 20150257.",
        "downloaded_via": "requests (UCI direct download)",
        "row_counts": {"beijing_pm25": row_count},
        "column_count": col_count,
        "missing_values_note": "pm2.5 has NA values (~5% of rows)",
        "tables": BEIJING_SCHEMA,
    }

    meta_path = meta_dir / "metadata.json"
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[beijing] metadata: {meta_path}")


def generate_sample(external_path: Path, n_rows: int = 100) -> None:
    samples_dir = PROJECT_ROOT / "datasets" / "samples" / "beijing-pm25"
    samples_dir.mkdir(parents=True, exist_ok=True)

    src = external_path / "beijing_pm25.csv"
    dst = samples_dir / "beijing-pm25-sample.csv"

    with src.open("r", encoding="utf-8") as f:
        lines = []
        for i, line in enumerate(f):
            if i > n_rows:
                break
            lines.append(line)

    dst.write_text("".join(lines), encoding="utf-8")
    size_kb = dst.stat().st_size / 1024
    print(f"[beijing]   sample: beijing-pm25-sample.csv "
          f"({size_kb:.1f} KB, {n_rows} rows)")


def main():
    output, rows, cols, df = download_beijing_pm25()
    write_metadata(rows, cols)
    generate_sample(output, n_rows=100)

    print(f"\n[beijing] Done. {rows:,} rows x {cols} columns.")
    print(f"[beijing] Raw data: {output}")
    print(f"[beijing] Metadata + sample: datasets/canonical/beijing-pm25/")
    print(f"[beijing] Next: python scripts/csv_to_sqlite.py")


if __name__ == "__main__":
    main()
