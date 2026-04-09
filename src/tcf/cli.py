"""CLI entry point: `tcf` or `python -m tcf`.

Commands:
  encode  CSV + metadata.json -> TCF (with compression levels)
  decode  TCF -> CSV files
  info    Show TCF file statistics

All commands print to console by default.
Use --out / --out-dir to also save to files.
"""

from __future__ import annotations
import argparse
import csv as csv_mod
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_encode(args: argparse.Namespace) -> None:
    from .encoder import encode, EncodeConfig

    config = EncodeConfig(
        level=args.level,
        include_stats=not args.no_stats,
        precision=args.precision,
    )

    text = encode(
        meta_path=Path(args.meta),
        data_dir=Path(args.data_dir),
        config=config,
    )

    size = len(text.encode("utf-8"))
    print(f"TCF level={args.level}: {size:,} bytes ({len(text):,} chars)", file=sys.stderr)

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"  -> {args.out}", file=sys.stderr)
    else:
        print(text)


def cmd_decode(args: argparse.Namespace) -> None:
    from .decoder import decode

    tcf_path = Path(args.file)
    text = tcf_path.read_text(encoding="utf-8")

    tables = decode(text, normalize=not args.flat_only)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, rows in tables.items():
        if not rows:
            continue
        out_path = out_dir / f"{name}.csv"
        with out_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv_mod.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"  {name}: {len(rows)} rows -> {out_path}")

    mode = "flat" if args.flat_only else "normalized"
    print(f"\nDecoded ({mode}) -> {out_dir}/")


def cmd_info(args: argparse.Namespace) -> None:
    from .decoder import decode

    tcf_path = Path(args.file)
    text = tcf_path.read_text(encoding="utf-8")
    tcf_bytes = tcf_path.stat().st_size
    tables = decode(text, normalize=False)

    print(f"File:   {args.file}")
    print(f"Size:   {tcf_bytes:,} bytes ({len(text):,} chars)")

    total_rows = 0
    for name, rows in tables.items():
        cols = list(rows[0].keys()) if rows else []
        total_rows += len(rows)
        print(f"  {name}: {len(rows)} rows x {len(cols)} cols  {cols}")

    # Detect compression
    rle_count = sum(1 for line in text.splitlines() if "*" in line and not line.startswith("#"))
    stats_count = sum(1 for line in text.splitlines() if line.strip().startswith("# STATS"))
    dict_count = sum(1 for line in text.splitlines() if line.strip().startswith("# dict"))

    print(f"\nFormat details:")
    print(f"  Total rows:    {total_rows}")
    print(f"  RLE groups:    {rle_count}")
    print(f"  Stats lines:   {stats_count}")
    print(f"  Dict entries:  {dict_count}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tcf",
        description="TCF -- Textual Columnar Format encoder/decoder",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # encode
    p_enc = sub.add_parser("encode", help="CSV + metadata.json -> TCF")
    p_enc.add_argument("--meta", required=True, help="Path to metadata.json")
    p_enc.add_argument("--data-dir", default=".", help="Directory with CSV files (default: .)")
    p_enc.add_argument("--out", help="Write TCF to file (default: stdout)")
    p_enc.add_argument("--level", type=int, default=2, choices=[0, 1, 2, 3],
                       help="Compression: 0=expanded, 1=rle, 2=sorted+rle, 3=dict+rle (default: 2)")
    p_enc.add_argument("--no-stats", action="store_true", help="Omit # STATS lines")
    p_enc.add_argument("--precision", type=int, default=None, help="Decimal places for floats")

    # decode
    p_dec = sub.add_parser("decode", help="TCF -> CSV files")
    p_dec.add_argument("file", help="Input .tcf file")
    p_dec.add_argument("--out-dir", default="restored", help="Output directory (default: restored/)")
    p_dec.add_argument("--flat-only", action="store_true",
                       help="Output flat table only (no normalization into separate tables)")

    # info
    p_inf = sub.add_parser("info", help="Show TCF file statistics")
    p_inf.add_argument("file", help="Input .tcf file")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    dispatch = {"encode": cmd_encode, "decode": cmd_decode, "info": cmd_info}
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
