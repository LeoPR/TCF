"""TCF -- Textual Columnar Format

Compact columnar data encoding with RLE compression for LLM reasoning.

Quick start (core, no IO):
    from tcf import encode_columns, EncodeConfig

    columns = {"name": ["Ana", "Bruno"], "age": ["25", "30"]}
    tcf_text = encode_columns("people", columns)

From row-oriented data:
    from tcf import encode_rows

    rows = [{"name": "Ana", "age": 25}, {"name": "Bruno", "age": 30}]
    tcf_text = encode_rows("people", rows)

Legacy (reads CSV files from disk):
    from tcf import encode

    tcf_text = encode("data/metadata.json", "data/")

Decode:
    from tcf import decode

    tables = decode(tcf_text)

Compression levels (--level):
    0  Expanded (no compression, one value per line)
    1  RLE (compress consecutive repeats)
    2  Sorted + RLE (sort by best column, then RLE) — default
    3  Dictionary + sorted + RLE (strings become indices)
"""

from .encoder import encode, encode_columns, encode_rows, EncodeConfig
from .decoder import decode

__version__ = "0.2.0"
__all__ = ["encode", "encode_columns", "encode_rows", "decode", "EncodeConfig"]
