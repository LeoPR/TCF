"""Compressor wrappers — wrappers neutros sobre gzip/brotli/zstd.

Cada compressor:
- name: str
- compress(data: bytes, level: int) -> bytes
- decompress(data: bytes) -> bytes

Niveis variam:
- gzip: 1-9
- brotli: 0-11
- zstd: 1-22

Default: nivel maximo razoavel (gzip=9, brotli=6, zstd=3).
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable
import gzip


@runtime_checkable
class Compressor(Protocol):
    name: str
    default_level: int
    def compress(self, data: bytes, level: int) -> bytes: ...
    def decompress(self, data: bytes) -> bytes: ...


class NoCompression:
    name = "none"
    default_level = 0
    def compress(self, data: bytes, level: int = 0) -> bytes:
        return data
    def decompress(self, data: bytes) -> bytes:
        return data


class GzipCompressor:
    name = "gzip"
    default_level = 9
    def compress(self, data: bytes, level: int = 9) -> bytes:
        return gzip.compress(data, compresslevel=level)
    def decompress(self, data: bytes) -> bytes:
        return gzip.decompress(data)


class BrotliCompressor:
    name = "brotli"
    default_level = 11
    def __init__(self):
        try:
            import brotli  # noqa
            self._brotli = brotli
        except ImportError:
            self._brotli = None

    def compress(self, data: bytes, level: int = 11) -> bytes:
        if self._brotli is None:
            raise ImportError("brotli not installed. Run: pip install brotli")
        return self._brotli.compress(data, quality=level)

    def decompress(self, data: bytes) -> bytes:
        if self._brotli is None:
            raise ImportError("brotli not installed. Run: pip install brotli")
        return self._brotli.decompress(data)


class ZstdCompressor:
    name = "zstd"
    default_level = 3
    def __init__(self):
        try:
            import zstandard  # noqa
            self._zstd = zstandard
        except ImportError:
            self._zstd = None

    def compress(self, data: bytes, level: int = 3) -> bytes:
        if self._zstd is None:
            raise ImportError("zstandard not installed. Run: pip install zstandard")
        return self._zstd.ZstdCompressor(level=level).compress(data)

    def decompress(self, data: bytes) -> bytes:
        if self._zstd is None:
            raise ImportError("zstandard not installed.")
        return self._zstd.ZstdDecompressor().decompress(data)


COMPRESSORS: dict[str, type] = {
    "none": NoCompression,
    "gzip": GzipCompressor,
    "brotli": BrotliCompressor,
    "zstd": ZstdCompressor,
}


def get_compressor(name: str) -> Compressor:
    if name not in COMPRESSORS:
        raise ValueError(f"Unknown compressor {name!r}. Available: {sorted(COMPRESSORS)}")
    return COMPRESSORS[name]()


def list_compressors() -> list[str]:
    return sorted(COMPRESSORS)
