"""Resolve storage paths based on config/storage.json (gitignored).

This module is imported by all dataset-related scripts to know where to
download data, write SQLite, and generate derivations. Keeps the code
portable across different machines (user configures their own storage).

Usage:
    from _paths import data_root, external_dir, interim_db, processed_dir

    # Get the configured root
    root = data_root()

    # Dataset-specific helpers
    tpch_raw = external_dir("tpch-sf001")
    tpch_db = interim_db("tpch-sf001")
    tpch_csv_dir = processed_dir("tpch-sf001", "csv")

Run directly to see current config:
    python scripts/_paths.py
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG = PROJECT_ROOT / "config" / "storage.json"
_FALLBACK = PROJECT_ROOT / "data-local"


def data_root() -> Path:
    """Return the configured data root, or fall back to ./data-local/."""
    if _CONFIG.exists():
        cfg = json.loads(_CONFIG.read_text(encoding="utf-8"))
        return Path(cfg["data_root"])
    return _FALLBACK


def external_dir(name: str) -> Path:
    """Path to raw downloaded data for a dataset."""
    return data_root() / "external" / name


def interim_db(name: str) -> Path:
    """Path to the SQLite file for a dataset."""
    return data_root() / "interim" / f"{name}.db"


def processed_dir(name: str, fmt: str) -> Path:
    """Path to processed output for a dataset in a given format.

    Args:
        name: dataset name (e.g. "tpch-sf001")
        fmt: output format (e.g. "csv", "jsonl", "markdown", "tcf")
    """
    return data_root() / "processed" / name / fmt


def archive_path(name: str) -> Path:
    """Path to the LZMA archive for a dataset."""
    return data_root() / "archives" / f"{name}.tar.xz"


def ensure_dirs() -> None:
    """Create the standard top-level directories if they don't exist.

    Creates:
        data_root/external/
        data_root/interim/
        data_root/processed/
        data_root/archives/

    Does NOT create per-dataset subdirectories — those are created by
    individual dataset scripts.
    """
    root = data_root()
    for sub in ("external", "interim", "processed", "archives"):
        (root / sub).mkdir(parents=True, exist_ok=True)


def _describe() -> str:
    """Return a human-readable summary of current config."""
    lines = [
        f"Project root: {PROJECT_ROOT}",
        f"Config file:  {_CONFIG}",
    ]
    if _CONFIG.exists():
        lines.append("  status:     FOUND")
        cfg = json.loads(_CONFIG.read_text(encoding="utf-8"))
        lines.append(f"  data_root:  {cfg['data_root']}")
    else:
        lines.append("  status:     NOT FOUND (using fallback)")
        lines.append(f"  fallback:   {_FALLBACK}")

    root = data_root()
    lines.append("")
    lines.append(f"Effective data root: {root}")
    lines.append(f"  exists:     {root.exists()}")
    lines.append("")
    lines.append("Path helpers (example for 'tpch-sf001'):")
    lines.append(f"  external_dir:  {external_dir('tpch-sf001')}")
    lines.append(f"  interim_db:    {interim_db('tpch-sf001')}")
    lines.append(f"  processed_csv: {processed_dir('tpch-sf001', 'csv')}")
    lines.append(f"  archive_path:  {archive_path('tpch-sf001')}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(_describe())
