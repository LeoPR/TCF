"""Baseline format writers for derived representations.

Each writer takes generic Python structures (list[dict] of rows, plus
optional column type metadata) and writes a file in its format.

**These are support scripts, not part of TCF core.**
Anyone using TCF can write their own writers for their own formats.
"""

from .csv_writer import write_csv
from .jsonl_writer import write_jsonl
from .markdown_writer import write_markdown

__all__ = ["write_csv", "write_jsonl", "write_markdown"]
