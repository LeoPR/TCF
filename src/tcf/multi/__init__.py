"""tcf.multi — implementacao interna multi-column (pacote).

P1 modularizacao (2026-06-24): o antigo `multi.py` virou pacote, separando
concerns (clareza pra port C/Rust — separa CORE portavel do HOST so'-Python):
- [`core`](core.py): `_encode_multi`/`_decode_multi` + MAGIC (orquestra candidatos).
- [`dict_v2b`](dict_v2b.py): V2-B dicionario categorico (ADR-0025, `@`).
- [`split`](split.py): split estrutural (ADR-0026, `%`).
- [`parallel`](parallel.py): encode serial/paralelo (HOST — ProcessPoolExecutor).

API publica continua `encode(dict)`/`decode(text)` em tcf.encoder/tcf.decoder.
Este `__init__` re-exporta os internos pra `from tcf.multi import X` seguir
funcionando byte-identico (decoder/encoder/view/tests).
"""
from tcf.multi.core import (
    MAGIC_MULTI,
    MAGIC_MULTI_V2,
    MAGIC_MULTI_V3,
    MAGIC_SINGLE_V3,
    META_PREFIX,
    _decode_multi,
    _decode_multi_impl,
    _encode_multi,
    _fallback_safe,
    _to_str,
)
from tcf.multi.dict_v2b import (
    _V2B_ALPHA,
    _V2B_BASE,
    _V2B_MAX_CARD,
    _decode_v2b,
    _v2b_encode,
    _v2b_idx_chars,
    _v2b_width,
)
from tcf.multi.parallel import (
    _encode_columns_parallel,
    _encode_columns_serial,
    _worker_encode_column,
)
from tcf.multi.split import (
    _DIGITS,
    _decode_struct_split,
    _struct_split_encode,
)
# Re-export pra compat de namespace do antigo modulo (tests usam m.DEFAULT_PIPELINE).
from tcf.pipeline import DEFAULT_PIPELINE, PipelineConfig

__all__ = [
    "DEFAULT_PIPELINE", "PipelineConfig",
    # core
    "MAGIC_MULTI", "MAGIC_MULTI_V2", "MAGIC_MULTI_V3", "MAGIC_SINGLE_V3", "META_PREFIX",
    "_encode_multi", "_decode_multi", "_decode_multi_impl", "_to_str", "_fallback_safe",
    # dict_v2b (V2-B, ADR-0025)
    "_V2B_ALPHA", "_V2B_BASE", "_V2B_MAX_CARD",
    "_v2b_width", "_v2b_idx_chars", "_v2b_encode", "_decode_v2b",
    # split (ADR-0026)
    "_DIGITS", "_struct_split_encode", "_decode_struct_split",
    # parallel (host)
    "_encode_columns_serial", "_encode_columns_parallel", "_worker_encode_column",
]
