"""TCF -- Textual Columnar Format

Compact columnar data encoding with RLE compression for LLM reasoning.

Quick start:
    from tcf import encode, decode

    tcf_text = encode("data/metadata.json", "data/")
    tables   = decode(tcf_text)

Compression levels (--level):
    0  Expanded (no compression, one value per line)
    1  RLE (compress consecutive repeats)
    2  Sorted + RLE (sort by best column, then RLE) — default
    3  Dictionary + sorted + RLE (strings become indices)
"""

from .encoder_v02 import encode_v02 as encode, V02Config as EncodeConfig
from .decoder_v02 import decode_v02 as decode

__version__ = "0.2.0"
__all__ = ["encode", "decode", "EncodeConfig"]
