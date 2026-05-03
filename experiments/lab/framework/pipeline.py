"""Pipeline simulator — orquestra encode -> compress -> decompress -> decode.

API principal:
    simulate(rows, encoder=..., compression=..., n_iterations=...) -> PipelineResult

Sem transport de rede no MVP — vive em memoria. Adicionar transport
em sprint posterior se necessario.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any
import time

from .encoders import get_encoder, Encoder
from .compressors import get_compressor, Compressor
from .metrics import compare_rows, utf8_len


@dataclass
class PipelineResult:
    """Resultado de uma execucao end-to-end."""
    encoder: str
    compression: str
    compression_level: int

    # Bytes
    bytes_uncompressed: int            # saida do encoder em UTF-8
    bytes_compressed: int              # apos compressor (ou == uncompressed se none)
    compression_ratio: float           # bytes_compressed / bytes_uncompressed

    # Timing (em ms; mediana de N iteracoes)
    encode_ms: float
    compress_ms: float
    decompress_ms: float
    decode_ms: float
    total_ms: float                    # encode + compress + decompress + decode

    # Roundtrip
    roundtrip_ok: bool
    roundtrip_diff: dict[str, Any] = field(default_factory=dict)

    # Metadata
    n_rows: int = 0
    n_cols: int = 0
    n_iterations: int = 1

    # Encoder/compressor extras (config, etc.)
    encoder_kwargs: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def simulate(
    rows: list[dict],
    *,
    encoder: str = "csv",
    encoder_kwargs: dict | None = None,
    compression: str = "none",
    compression_level: int | None = None,
    n_iterations: int = 5,
    tolerant_types: bool = True,
) -> PipelineResult:
    """Roda o pipeline completo e retorna metricas.

    Args:
        rows: dados de entrada (list[dict] com tipos nativos)
        encoder: 'csv'|'json'|'jsonl'|'tcf'
        encoder_kwargs: passados para o encoder ctor (ex: {'level': 2} para tcf)
        compression: 'none'|'gzip'|'brotli'|'zstd'
        compression_level: nivel especifico (ou None = default do compressor)
        n_iterations: repete encode/decode para timing estavel; mediana
        tolerant_types: roundtrip aceita 30 == '30' (CSV perde tipos)

    Returns:
        PipelineResult com bytes/timing/roundtrip.
    """
    encoder_kwargs = encoder_kwargs or {}
    enc: Encoder = get_encoder(encoder, **encoder_kwargs)
    comp: Compressor = get_compressor(compression)
    level = compression_level if compression_level is not None else comp.default_level

    # Estatisticas dos dados
    n_rows = len(rows)
    n_cols = len(rows[0]) if rows else 0

    # Encode (timing)
    encode_times = []
    encoded_text = ""
    for _ in range(n_iterations):
        t0 = time.perf_counter()
        encoded_text = enc.encode(rows)
        encode_times.append((time.perf_counter() - t0) * 1000)
    encode_ms = _median(encode_times)
    bytes_uncompressed = utf8_len(encoded_text)

    # Compress (timing)
    encoded_bytes = encoded_text.encode("utf-8")
    compress_times = []
    compressed_bytes = encoded_bytes
    for _ in range(n_iterations):
        t0 = time.perf_counter()
        compressed_bytes = comp.compress(encoded_bytes, level=level)
        compress_times.append((time.perf_counter() - t0) * 1000)
    compress_ms = _median(compress_times)
    bytes_compressed = len(compressed_bytes)

    # Decompress (timing)
    decompress_times = []
    decompressed_bytes = compressed_bytes
    for _ in range(n_iterations):
        t0 = time.perf_counter()
        decompressed_bytes = comp.decompress(compressed_bytes)
        decompress_times.append((time.perf_counter() - t0) * 1000)
    decompress_ms = _median(decompress_times)

    # Decode (timing) — captura exception como dado (decoder pode ter bugs)
    decoded_text = decompressed_bytes.decode("utf-8")
    decode_times = []
    decoded_rows = []
    decode_error: str | None = None
    for _ in range(n_iterations):
        t0 = time.perf_counter()
        try:
            decoded_rows = enc.decode(decoded_text)
            decode_times.append((time.perf_counter() - t0) * 1000)
        except Exception as e:
            decode_times.append((time.perf_counter() - t0) * 1000)
            decode_error = f"{type(e).__name__}: {e}"
            decoded_rows = []
            break
    decode_ms = _median(decode_times) if decode_times else 0.0

    # Roundtrip
    if decode_error:
        ok = False
        diff = {"reason": "decode_exception", "error": decode_error}
    else:
        ok, diff = compare_rows(decoded_rows, rows, tolerant_types=tolerant_types)

    return PipelineResult(
        encoder=enc.name,
        compression=comp.name,
        compression_level=level,
        bytes_uncompressed=bytes_uncompressed,
        bytes_compressed=bytes_compressed,
        compression_ratio=(bytes_compressed / bytes_uncompressed
                           if bytes_uncompressed > 0 else 0.0),
        encode_ms=encode_ms,
        compress_ms=compress_ms,
        decompress_ms=decompress_ms,
        decode_ms=decode_ms,
        total_ms=encode_ms + compress_ms + decompress_ms + decode_ms,
        roundtrip_ok=ok,
        roundtrip_diff=diff,
        n_rows=n_rows,
        n_cols=n_cols,
        n_iterations=n_iterations,
        encoder_kwargs=encoder_kwargs,
    )


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2
