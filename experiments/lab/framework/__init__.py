"""TCF Lab framework — infra reutilizavel para experimentos cientificos.

Componentes:
- datasets:    carregadores (MICRO, Adult, TPC-H, sinteticos)
- encoders:    adapters (CSV, JSON, TCF, TOON quando disponivel)
- compressors: wrappers (gzip, brotli, zstd)
- pipeline:    simulate(rows, encoder, compress, transport)
- metrics:     bytes/timing/roundtrip

Nao faz parte do TCF — e infra de pesquisa.
"""
from .datasets import DATASETS, load_dataset, describe
from .encoders import ENCODERS, get_encoder, list_encoders
from .compressors import COMPRESSORS, get_compressor, list_compressors
from .pipeline import simulate, PipelineResult
from .metrics import compare_rows

__all__ = [
    "DATASETS", "load_dataset", "describe",
    "ENCODERS", "get_encoder", "list_encoders",
    "COMPRESSORS", "get_compressor", "list_compressors",
    "simulate", "PipelineResult",
    "compare_rows",
]
